"""健康检查：SQLite/FTS5/向量库/模型配置状态。"""
from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter(tags=["健康检查"])


@router.get("/api/health", summary="服务健康状态")
async def health(request: Request):
    settings = get_settings()
    services = request.app.state.services

    # 数据库连通性
    db_ok, db_error = True, None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_ok, db_error = False, str(exc)[:200]

    # FTS5 全文检索可用性
    fts_ok, fts_error = True, None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT count(*) FROM chunks_fts"))
    except Exception as exc:
        fts_ok, fts_error = False, str(exc)[:200]

    vector = services.vector_store.health()
    overall = "ok" if db_ok and fts_ok and vector.get("ok") else "degraded"
    return {
        "status": overall,
        "database": {"ok": db_ok, "error": db_error, "fts5": fts_ok, "fts5_error": fts_error},
        "vector_store": vector,
        "models": {
            "chat": settings.chat_model,
            "embedding_provider": settings.embedding_provider,
            "embedding": settings.embedding_model,
            "embedding_dim": settings.embedding_dim,
            "rerank_provider": settings.rerank_provider,
            "rerank": settings.rerank_model,
        },
        "mock_mode": settings.mock_mode,
    }
