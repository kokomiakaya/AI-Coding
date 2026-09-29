"""重排序：实现"粗排→精排"两阶段检索架构，按配置切换实现（rerank_provider）。

- dashscope：qwen3-rerank 专用重排模型（需百炼额度），失败自动降级为本地混合分数重排
- local：本地混合分数重排（向量相似度 + BM25 排名加成），免费、确定性、无 API 依赖

粗排（RRF 融合 top-20）负责高召回，精排负责高精度。
"""
import httpx
import jieba
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.services.rag.hybrid import RetrievedChunk


def _local_scores(query: str, chunks: list[RetrievedChunk], top_n: int) -> list[tuple[int, float]]:
    """本地混合分数重排：0.65 × 向量相似度 + 0.35 × BM25 排名加成。

    分数与阈值同尺度（0~1）：
    - 向量相似度（BGE 余弦）是主信号：实测相关片段 0.6~0.9、噪声 0.2~0.4；
    - BM25 命中给加成（排名越靠前越高），保住精确关键词（型号/规格）命中的片段。
    """
    scored = []
    for i, c in enumerate(chunks):
        bonus = 0.0
        if c.bm25_rank is not None and c.bm25_total:
            bonus = 1.0 - (c.bm25_rank - 1) / c.bm25_total
        score = min(1.0, 0.65 * c.vector_similarity + 0.35 * bonus)
        scored.append((i, round(score, 4)))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_n]


class Reranker:
    def __init__(self) -> None:
        s = get_settings()
        self.mock = s.mock_mode
        self._provider = s.rerank_provider
        self._client = httpx.AsyncClient(timeout=30.0)
        self._url = s.dashscope_rerank_url
        self._model = s.rerank_model
        self._key = s.dashscope_api_key

    async def close(self) -> None:
        await self._client.aclose()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.5, max=4), reraise=True)
    async def _call(
        self, query: str, documents: list[str], top_n: int
    ) -> list[tuple[int, float]]:
        resp = await self._client.post(
            self._url,
            headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
            json={
                "model": self._model,
                "input": {"query": query, "documents": documents},
                "parameters": {"top_n": top_n, "return_documents": False},
            },
        )
        resp.raise_for_status()
        results = resp.json().get("output", {}).get("results", [])
        return [(int(r["index"]), float(r.get("relevance_score", 0.0))) for r in results]

    async def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_n: int
    ) -> list[tuple[int, float]] | None:
        """返回 [(候选下标, 相关性分)]；异常时降级为本地混合分数（永不返回 None）。"""
        if not chunks:
            return []
        if self.mock:
            return self._mock_scores(query, chunks, top_n)
        if self._provider == "local":
            return _local_scores(query, chunks, top_n)
        try:
            return await self._call(query, [c.content for c in chunks], top_n)
        except Exception as exc:
            logger.warning(f"重排模型调用失败，降级为本地混合分数重排：{exc}")
            return _local_scores(query, chunks, top_n)

    def _mock_scores(self, query: str, chunks: list[RetrievedChunk], top_n: int) -> list[tuple[int, float]]:
        """离线演示模式：jieba 词重叠的朴素相关性打分，确定性与真实逻辑同构。"""
        q_tokens = set(jieba.cut_for_search(query))
        scored = []
        for i, c in enumerate(chunks):
            overlap = len(q_tokens & set(jieba.cut_for_search(c.content)))
            scored.append((i, min(1.0, 0.15 + overlap * 0.12)))
        scored.sort(key=lambda x: -x[1])
        return scored[:top_n]
