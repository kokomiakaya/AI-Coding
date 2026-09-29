"""Chroma 向量存储实现：纯 pip 安装、本地持久化、内建 HNSW 索引（cosine 距离）。"""
import asyncio
from typing import Any

import chromadb
from loguru import logger

from app.core.config import get_settings
from app.vectorstore.base import BaseVectorStore, VectorHit, VectorRecord


def _collection_name(kb_id: int) -> str:
    """集合名带嵌入维度后缀：切换嵌入模型（维度变化）时自动使用新集合。

    旧维度集合保留在磁盘不删除（可随时切回嵌入模型），无需手工清库。
    """
    return f"kb_{kb_id}_d{get_settings().embedding_dim}"


class ChromaVectorStore(BaseVectorStore):
    """基于 chromadb PersistentClient 的向量存储。

    每个知识库（每维度）一个 collection（隔离性好，删库即删集合）；
    向量只与 chunk_id 关联，分块内容真源在 SQLite chunks 表，崩溃后可幂等重建。
    """

    def __init__(self) -> None:
        settings = get_settings()
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client: Any = chromadb.PersistentClient(path=str(settings.chroma_dir))

    def _get_collection(self, kb_id: int) -> Any:
        return self._client.get_or_create_collection(
            name=_collection_name(kb_id),
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(self, kb_id: int, records: list[VectorRecord]) -> None:
        def _do() -> None:
            col = self._get_collection(kb_id)
            col.upsert(
                ids=[str(r.chunk_id) for r in records],
                embeddings=[r.embedding for r in records],
                documents=[r.text for r in records],
                metadatas=[r.metadata for r in records],
            )

        await asyncio.to_thread(_do)

    async def delete_document(self, kb_id: int, document_id: int) -> None:
        def _do() -> None:
            col = self._get_collection(kb_id)
            try:
                col.delete(where={"document_id": document_id})
            except Exception as exc:
                logger.warning(f"删除文档向量失败（kb={kb_id}, doc={document_id}）: {exc}")

        await asyncio.to_thread(_do)

    async def delete_kb(self, kb_id: int) -> None:
        def _do() -> None:
            try:
                self._client.delete_collection(_collection_name(kb_id))
            except Exception as exc:
                logger.warning(f"删除知识库向量集合失败（kb={kb_id}）: {exc}")

        await asyncio.to_thread(_do)

    async def search(
        self, kb_ids: list[int], query_embedding: list[float], top_k: int
    ) -> list[VectorHit]:
        def _do() -> list[VectorHit]:
            hits: list[VectorHit] = []
            for kb_id in kb_ids:
                col = self._get_collection(kb_id)
                res = col.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    include=["metadatas", "distances"],
                )
                ids = (res.get("ids") or [[]])[0]
                dists = (res.get("distances") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0] or []
                for i, chunk_id in enumerate(ids):
                    if chunk_id is None:
                        continue
                    hits.append(
                        VectorHit(
                            chunk_id=int(chunk_id),
                            similarity=1.0 - float(dists[i]),
                            metadata=metas[i] if i < len(metas) and metas[i] else {},
                        )
                    )
            return hits

        return await asyncio.to_thread(_do)

    def health(self) -> dict:
        try:
            collections = self._client.list_collections()
            return {"backend": "chroma", "ok": True, "collections": len(collections)}
        except Exception as exc:
            return {"backend": "chroma", "ok": False, "error": str(exc)[:200]}
