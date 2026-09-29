"""混合检索：向量检索（语义）+ FTS5 BM25（关键词），RRF 融合。

两路检索互补：向量擅长同义表达，BM25 擅长精确关键词（商品型号/规格等）。
RRF 融合无需调参、对分数尺度不敏感（论文核心优化点之一）。
"""
import asyncio
from dataclasses import dataclass

import jieba
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document
from app.services.ingestion.embedder import BaseEmbedder
from app.vectorstore.base import BaseVectorStore, VectorHit

RRF_K = 60  # RRF 常数：平滑排名差异

# 疑问词/语气词停用表：不是内容词，命中只会把无关分块顶进候选（实测"你是什么模型"
# 因命中含"什么"的分块而误入 RAG 路径）；单字 token 在 bm25_search 内已按长度过滤
QUESTION_WORDS = {
    "什么", "怎么", "怎样", "怎么样", "多少", "哪些", "哪个", "哪款", "哪家",
    "如何", "为何", "为什么", "是否", "是不是", "有没有", "吗", "呢", "吧",
    "请问", "一下", "多少",
}


@dataclass
class RetrievedChunk:
    """检索候选片段（两路融合后的统一结构）。"""

    chunk_id: int
    document_id: int
    document_name: str
    content: str
    page: int | None = None
    sheet: str | None = None
    row: int | None = None
    score: float = 0.0  # 重排后的最终分数
    rrf_score: float = 0.0
    vector_similarity: float = 0.0  # 向量路余弦相似度（0~1，本地重排主信号）
    bm25_rank: int | None = None  # BM25 路排名（1 起），未命中为 None
    bm25_total: int = 0  # BM25 命中总数（排名加成归一化用）


def tokenize(text: str) -> list[str]:
    """jieba 搜索模式分词（提升召回），过滤空白 token。"""
    return [t.strip().lower() for t in jieba.cut_for_search(text) if t.strip()]


def rrf_fuse(vector_hits: list[VectorHit], bm25_rows: list[dict]) -> dict[int, float]:
    """RRF 融合：score = Σ 1/(K + rank)，rank 从 1 开始，去重累加。"""
    scores: dict[int, float] = {}
    for rank, hit in enumerate(vector_hits, start=1):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    for rank, row in enumerate(bm25_rows, start=1):
        cid = row["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank)
    return scores


async def bm25_search(
    db: AsyncSession, kb_ids: list[int], query: str, top_k: int
) -> list[dict]:
    """FTS5 中文 BM25 检索：查询侧 jieba 分词，OR 连接，bm25() 排序（值越小越相关）。

    过滤单字 token（中文单字词频极高、精度极差，会以词频优势霸占 BM25 榜首）
    与疑问词（"什么/怎么样"等非内容词，命中纯属巧合，会把闲聊类问题误拉进 RAG 路径）。
    """
    tokens = [
        t.replace('"', "")
        for t in tokenize(query)
        if t and len(t) >= 2 and t.lower() not in QUESTION_WORDS
    ]
    if not tokens or not kb_ids:
        return []
    match_expr = " OR ".join(f'"{t}"' for t in tokens)
    kb_in = ",".join(str(k) for k in kb_ids)  # kb_ids 为整数，无注入风险
    sql = text(
        f"""
        SELECT c.id, c.kb_id, c.document_id, c.content, c.meta,
               bm25(chunks_fts) AS bm25_score
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        WHERE chunks_fts MATCH :q AND c.kb_id IN ({kb_in})
        ORDER BY bm25_score
        LIMIT :limit
        """
    )
    rows = await db.execute(sql, {"q": match_expr, "limit": top_k})
    return [dict(r._mapping) for r in rows]


async def hybrid_search(
    db: AsyncSession,
    vector_store: BaseVectorStore,
    embedder: BaseEmbedder,
    query: str,
    kb_ids: list[int],
    candidates: int = 20,
    top_k_vector: int = 50,
    top_k_bm25: int = 30,
) -> list[RetrievedChunk]:
    """双路检索 + RRF 融合，返回候选片段（按 RRF 分降序，共 candidates 个）。"""
    if not kb_ids:
        return []
    # 两路并行：向量嵌入 + BM25
    emb_task = embedder.embed_query(query)
    bm25_task = bm25_search(db, kb_ids, query, top_k_bm25)
    query_vec, bm25_rows = await asyncio.gather(emb_task, bm25_task)
    vector_hits = await vector_store.search(kb_ids, query_vec, top_k_vector)

    fused = rrf_fuse(vector_hits, bm25_rows)
    ranked_ids = sorted(fused, key=fused.get, reverse=True)[:candidates]
    if not ranked_ids:
        return []

    # 单路信号（供本地混合分数重排使用）
    sim_map = {h.chunk_id: h.similarity for h in vector_hits}
    bm25_rank_map: dict[int, int] = {}
    for rank, row in enumerate(bm25_rows, start=1):
        bm25_rank_map.setdefault(row["id"], rank)

    # 批量取分块与文档名
    chunks = (await db.execute(select(Chunk).where(Chunk.id.in_(ranked_ids)))).scalars().all()
    chunk_map = {c.id: c for c in chunks}
    doc_map: dict[int, Document] = {}
    if chunks:
        doc_ids = {c.document_id for c in chunks}
        docs = (await db.execute(select(Document).where(Document.id.in_(doc_ids)))).scalars().all()
        doc_map = {d.id: d for d in docs}

    results: list[RetrievedChunk] = []
    for cid in ranked_ids:
        chunk = chunk_map.get(cid)
        if chunk is None:
            continue
        doc = doc_map.get(chunk.document_id)
        meta = chunk.meta or {}
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=doc.filename if doc else "未知文档",
                content=chunk.content,
                page=meta.get("page"),
                sheet=meta.get("sheet"),
                row=meta.get("row"),
                rrf_score=round(fused[cid], 5),
                vector_similarity=round(sim_map.get(cid, 0.0), 4),
                bm25_rank=bm25_rank_map.get(cid),
                bm25_total=len(bm25_rows),
            )
        )
    return results
