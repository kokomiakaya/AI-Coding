"""知识库服务：计数统计与级联删除（含向量集合与上传文件清理）。"""
import shutil
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, KnowledgeBase


async def kb_counts(db: AsyncSession, kb_ids: list[int]) -> dict[int, dict]:
    """批量统计每个 KB 的文档数与分块数。"""
    if not kb_ids:
        return {}
    doc_rows = (
        await db.execute(
            select(Document.kb_id, func.count(Document.id))
            .where(Document.kb_id.in_(kb_ids))
            .group_by(Document.kb_id)
        )
    ).all()
    chunk_rows = (
        await db.execute(
            select(Chunk.kb_id, func.count(Chunk.id))
            .where(Chunk.kb_id.in_(kb_ids))
            .group_by(Chunk.kb_id)
        )
    ).all()
    docs = {kb_id: n for kb_id, n in doc_rows}
    chunks = {kb_id: n for kb_id, n in chunk_rows}
    return {
        kb_id: {"document_count": docs.get(kb_id, 0), "chunk_count": chunks.get(kb_id, 0)}
        for kb_id in kb_ids
    }


async def delete_kb(db: AsyncSession, vector_store, kb: KnowledgeBase) -> None:
    """删除知识库：级联删文档/分块（FK），清理向量集合与上传文件。"""
    files = (
        await db.execute(select(Document.file_path).where(Document.kb_id == kb.id))
    ).scalars().all()
    kb_id = kb.id
    await db.delete(kb)
    await db.commit()
    await vector_store.delete_kb(kb_id)
    for path in files:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
    # 清理 KB 上传目录
    from app.core.config import get_settings

    kb_dir = get_settings().uploads_dir / str(kb_id)
    shutil.rmtree(kb_dir, ignore_errors=True)
