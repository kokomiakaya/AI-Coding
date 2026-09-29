"""摄取任务 worker：asyncio 队列 + 协程池 + 并发信号量。

无消息队列的轻量异步方案（论文论述点：上传与处理解耦，预留 Redis 队列扩展）。
崩溃恢复：启动时把中间状态文档重置为 pending 重新入队（任务幂等）。
"""
import asyncio

from loguru import logger
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Document
from app.services.ingestion import pipeline as ingestion_pipeline


class IngestionWorker:
    def __init__(
        self,
        vector_store,
        embedder,
        n_workers: int = 2,
        embed_concurrency: int = 4,
    ) -> None:
        self._vector_store = vector_store
        self._embedder = embedder
        self._n_workers = n_workers
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(embed_concurrency)
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def enqueue(self, document_id: int) -> None:
        self._queue.put_nowait(document_id)

    async def start(self) -> None:
        self._running = True
        self._tasks = [
            asyncio.create_task(self._worker_loop(i)) for i in range(self._n_workers)
        ]
        await self._recover_interrupted()
        logger.info(f"摄取 worker 已启动（{self._n_workers} 个协程）")

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("摄取 worker 已停止")

    async def _worker_loop(self, idx: int) -> None:
        while self._running:
            document_id = await self._queue.get()
            try:
                await ingestion_pipeline.process_document(
                    document_id, self._vector_store, self._embedder, self._semaphore
                )
            except Exception:
                logger.exception(f"文档 {document_id} 处理异常（已被标记 failed）")
            finally:
                self._queue.task_done()

    async def _recover_interrupted(self) -> None:
        """崩溃恢复：pending/parsing/embedding 文档重置为 pending 并重新入队（幂等重建）。"""
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(Document).where(
                        Document.status.in_(["pending", "parsing", "embedding"])
                    )
                )
            ).scalars().all()
            for doc in rows:
                doc.status = "pending"
                doc.error_message = None
            await session.commit()
            for doc in rows:
                self.enqueue(doc.id)
            if rows:
                logger.info(f"恢复 {len(rows)} 个未完成的文档摄取任务")
