"""单文档摄取流程：解析 → 切分 → 批量嵌入 → 写 SQLite（真源）→ 写向量库。

状态机：pending → parsing → embedding → ready / failed（失败可 re-embed 重试）。
一致性策略：SQLite 为唯一真源，向量库崩溃后可幂等重建；
re-embed 幂等：先清旧分块与向量，再全量重建。
"""
import asyncio

from loguru import logger
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models import Chunk, Document, KnowledgeBase
from app.services.ingestion import loaders, splitter
from app.vectorstore.base import VectorRecord


async def process_document(document_id: int, vector_store, embedder, semaphore) -> None:
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, document_id)
        if doc is None or doc.status != "pending":
            return
        kb = await db.get(KnowledgeBase, doc.kb_id)
        if kb is None:
            doc.status = "failed"
            doc.error_message = "知识库不存在，请删除该文档"
            await db.commit()
            return
        try:
            # ---------- ① 解析 ----------
            doc.status = "parsing"
            await db.commit()
            pages = await asyncio.to_thread(loaders.load_document, doc.file_path, doc.file_type)
            if not pages:
                raise ValueError("文档解析结果为空，请检查文件内容")

            # ---------- ② 切分（参数取 KB 配置） ----------
            chunks = splitter.split_pages(pages, kb.chunk_size, kb.chunk_overlap)
            if not chunks:
                raise ValueError("文档切分结果为空")

            # ---------- ③ 清旧分块（re-embed 幂等） ----------
            await db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
            doc.chunk_count = 0
            doc.status = "embedding"
            await db.commit()

            # ---------- ④ 批量嵌入（信号量限并发上游请求） ----------
            texts = [c["content"] for c in chunks]
            async with semaphore:
                vectors = await embedder.embed_documents(texts)

            # ---------- ⑤ 写 SQLite 分块（FTS5 触发器自动同步索引） ----------
            for i, (c, vec) in enumerate(zip(chunks, vectors)):
                db.add(
                    Chunk(
                        kb_id=doc.kb_id,
                        document_id=doc.id,
                        chunk_index=i,
                        content=c["content"],
                        content_tokens=splitter.tokenize_for_fts(c["content"]),
                        meta=c["meta"],
                    )
                )
            await db.flush()
            chunk_rows = (
                await db.execute(
                    select(Chunk)
                    .where(Chunk.document_id == doc.id)
                    .order_by(Chunk.chunk_index)
                )
            ).scalars().all()

            # ---------- ⑥ 写向量库（按 chunk_id 关联） ----------
            await vector_store.upsert(
                doc.kb_id,
                [
                    VectorRecord(
                        chunk_id=row.id,
                        embedding=vec,
                        text=row.content,
                        metadata={
                            "kb_id": doc.kb_id,
                            "document_id": doc.id,
                            "chunk_index": row.chunk_index,
                        },
                    )
                    for row, vec in zip(chunk_rows, vectors)
                ],
            )

            doc.chunk_count = len(chunks)
            doc.status = "ready"
            doc.error_message = None
            await db.commit()
            logger.info(f"文档《{doc.filename}》摄取完成：{len(chunks)} 个分块")
        except Exception as exc:
            await db.rollback()
            doc = await db.get(Document, document_id)
            if doc is not None:
                doc.status = "failed"
                doc.error_message = str(exc)[:500]
                await db.commit()
            logger.error(f"文档《{doc.filename}》摄取失败：{exc}")
