"""向量存储抽象层：统一接口 + 工厂。

当前实现 Chroma（HNSW 索引），生产可扩展 PG+pgvector / Milvus（论文论述点：
向量引擎可插拔，分块内容的唯一真源始终在 SQLite chunks 表，向量可随时重建）。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    """待写入向量库的一条分块记录。"""

    chunk_id: int
    embedding: list[float]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorHit:
    """向量检索命中结果。"""

    chunk_id: int
    similarity: float  # 1 - 距离，越大越相关
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseVectorStore(ABC):
    """向量库统一接口，屏蔽底层实现差异。"""

    @abstractmethod
    async def upsert(self, kb_id: int, records: list[VectorRecord]) -> None:
        """写入/更新一批向量。"""

    @abstractmethod
    async def delete_document(self, kb_id: int, document_id: int) -> None:
        """删除某文档的全部向量。"""

    @abstractmethod
    async def delete_kb(self, kb_id: int) -> None:
        """删除整个知识库的向量空间。"""

    @abstractmethod
    async def search(
        self, kb_ids: list[int], query_embedding: list[float], top_k: int
    ) -> list[VectorHit]:
        """跨知识库检索，返回相似度降序的命中。"""

    @abstractmethod
    def health(self) -> dict:
        """健康状态（供 /api/health 与排查）。"""


def get_vector_store() -> BaseVectorStore:
    """工厂：优先 Chroma，失败回退 FAISS（可选安装 faiss-cpu）。"""
    try:
        from app.vectorstore.chroma_store import ChromaVectorStore

        return ChromaVectorStore()
    except ImportError as exc:
        from loguru import logger

        logger.warning(f"Chroma 不可用（{exc}），尝试回退 FAISS")
        try:
            from app.vectorstore.faiss_store import FAISSVectorStore

            return FAISSVectorStore()
        except ImportError:
            raise RuntimeError("向量库初始化失败：请安装 chromadb（或 faiss-cpu）") from exc
