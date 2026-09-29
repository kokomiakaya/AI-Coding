"""文档管理接口（仅管理员）：上传 / 列表 / 状态轮询 / re-embed / 删除 / 分块预览。

上传即返回（pending），后台 worker 异步摄取，前端 2s 轮询状态。
"""
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select

from app.api.deps import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Chunk, Document, KnowledgeBase, User
from app.schemas.document import ChunkOut, DocumentOut, TextDocIn

router = APIRouter(prefix="/api", tags=["文档管理"])


def _validate_file(filename: str, size: int) -> tuple[str, str]:
    """校验扩展名与大小，返回 (文件名, 类型)。"""
    settings = get_settings()
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"不支持的文件类型 {suffix}，仅支持：{'/'.join(settings.allowed_extensions)}",
        )
    max_bytes = settings.upload_max_size_mb * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"文件超过大小限制（{settings.upload_max_size_mb}MB）"
        )
    return filename, suffix.lstrip(".")


@router.post("/kb/{kb_id}/documents", summary="上传文档（多文件，秒回 pending）")
async def upload_documents(
    kb_id: int,
    request: Request,
    files: list[UploadFile] = File(...),
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
    settings = get_settings()
    kb_dir = settings.uploads_dir / str(kb_id)
    kb_dir.mkdir(parents=True, exist_ok=True)

    created: list[DocumentOut] = []
    for upload in files:
        content = await upload.read()
        _validate_file(upload.filename or "", len(content))
        # 唯一文件名，避免覆盖与路径冲突
        stored_name = f"{uuid.uuid4().hex[:12]}{Path(upload.filename).suffix.lower()}"
        dest = kb_dir / stored_name
        async with aiofiles.open(dest, "wb") as f:
            await f.write(content)

        doc = Document(
            kb_id=kb_id,
            filename=upload.filename,
            file_type=Path(upload.filename).suffix.lower().lstrip("."),
            file_size=len(content),
            file_path=str(dest),
            status="pending",
            created_by=admin.id,
        )
        db.add(doc)
        await db.commit()
        request.app.state.services.ingestion_worker.enqueue(doc.id)
        created.append(DocumentOut.model_validate(doc))
    return {"items": created, "message": f"已接收 {len(created)} 个文件，正在后台处理"}


@router.post("/kb/{kb_id}/documents/text", summary="直接录入文本（粘贴内容入库解析）")
async def create_text_document(
    kb_id: int,
    body: TextDocIn,
    request: Request,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """把粘贴的文本作为文档写入知识库：落盘为 .txt 后走与上传完全相同的异步摄取管道。"""
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
    content = body.content.strip()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文本内容不能为空")

    filename = body.filename.strip()[:100] or "手动录入文本"
    if not filename.lower().endswith(".txt"):
        filename += ".txt"

    settings = get_settings()
    kb_dir = settings.uploads_dir / str(kb_id)
    kb_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:12]}.txt"
    dest = kb_dir / stored_name
    async with aiofiles.open(dest, "w", encoding="utf-8") as f:
        await f.write(content)

    doc = Document(
        kb_id=kb_id,
        filename=filename,
        file_type="txt",
        file_size=len(content.encode("utf-8")),
        file_path=str(dest),
        status="pending",
        created_by=admin.id,
    )
    db.add(doc)
    await db.commit()
    request.app.state.services.ingestion_worker.enqueue(doc.id)
    return DocumentOut.model_validate(doc)


@router.get("/kb/{kb_id}/documents", summary="知识库文档列表（分页+状态筛选）")
async def list_documents(
    kb_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "知识库不存在")
    filters = [Document.kb_id == kb_id]
    if status_filter:
        filters.append(Document.status == status_filter)
    total = (await db.execute(select(func.count(Document.id)).where(*filters))).scalar_one()
    rows = (
        await db.execute(
            select(Document)
            .where(*filters)
            .order_by(Document.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars().all()
    return {
        "items": [DocumentOut.model_validate(d) for d in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/documents/{doc_id}", summary="文档详情（状态轮询用）")
async def get_document(
    doc_id: int,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    return DocumentOut.model_validate(doc)


@router.post("/documents/{doc_id}/re-embed", summary="重新嵌入（失败重试/参数更新后重建，幂等）")
async def re_embed(
    doc_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    if doc.status not in ("failed", "ready"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文档正在处理中，请稍后再试")
    doc.status = "pending"
    doc.error_message = None
    doc.chunk_count = 0
    await db.commit()
    request.app.state.services.ingestion_worker.enqueue(doc.id)
    return DocumentOut.model_validate(doc)


@router.delete("/documents/{doc_id}", summary="删除文档（级联删分块与向量）")
async def delete_document(
    doc_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    kb_id, file_path = doc.kb_id, doc.file_path
    await db.delete(doc)  # FK 级联删分块
    await db.commit()
    await request.app.state.services.vector_store.delete_document(kb_id, doc_id)
    Path(file_path).unlink(missing_ok=True)
    return {"message": "文档已删除"}


@router.get("/documents/{doc_id}/chunks", summary="分块预览（检查切分质量）")
async def list_chunks(
    doc_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    total = (
        await db.execute(select(func.count(Chunk.id)).where(Chunk.document_id == doc_id))
    ).scalar_one()
    rows = (
        await db.execute(
            select(Chunk)
            .where(Chunk.document_id == doc_id)
            .order_by(Chunk.chunk_index)
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars().all()
    return {
        "items": [ChunkOut.model_validate(c) for c in rows],
        "total": total,
        "page": page,
        "size": size,
    }
