"""服务容器：lifespan 中构建全部单例服务（LLM/嵌入/重排/向量库/摄取 worker）。"""
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.services.ingestion.embedder import BaseEmbedder, build_embedder
from app.services.ingestion.worker import IngestionWorker
from app.services.rag.generator import Generator
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import Reranker
from app.vectorstore.base import BaseVectorStore, get_vector_store


@dataclass
class Services:
    settings: Settings
    vector_store: BaseVectorStore
    embedder: BaseEmbedder
    rewriter: QueryRewriter
    reranker: Reranker
    generator: Generator
    ingestion_worker: IngestionWorker

    async def start(self) -> None:
        await self.ingestion_worker.start()

    async def stop(self) -> None:
        await self.ingestion_worker.stop()
        await self.reranker.close()


def build_services() -> Services:
    settings = get_settings()
    vector_store = get_vector_store()
    embedder = build_embedder()
    worker = IngestionWorker(vector_store=vector_store, embedder=embedder)
    return Services(
        settings=settings,
        vector_store=vector_store,
        embedder=embedder,
        rewriter=QueryRewriter(),
        reranker=Reranker(),
        generator=Generator(),
        ingestion_worker=worker,
    )
