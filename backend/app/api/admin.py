"""管理接口（仅管理员）：统计看板 / 系统配置热更新。"""
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.api.deps import require_admin
from app.db.session import get_db
from app.models import User
from app.services import config_service, stats_service

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/stats/overview", summary="KPI 总览")
async def stats_overview(_admin: User = Depends(require_admin), db=Depends(get_db)):
    return await stats_service.overview(db)


@router.get("/stats/trend", summary="按天趋势（消息量与 token 消耗）")
async def stats_trend(
    days: int = Query(30, ge=1, le=90),
    _admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    return {"days": days, "items": await stats_service.trend(db, days)}


@router.get("/stats/kb", summary="知识库分布统计")
async def stats_kb(_admin: User = Depends(require_admin), db=Depends(get_db)):
    return await stats_service.kb_stats(db)


@router.get("/stats/feedback", summary="反馈统计（赞踩/满意度/趋势）")
async def stats_feedback(_admin: User = Depends(require_admin), db=Depends(get_db)):
    return await stats_service.feedback_stats(db)


@router.get("/config", summary="全部系统配置")
async def get_configs(_admin: User = Depends(require_admin), db=Depends(get_db)):
    return await config_service.get_all_configs(db)


@router.put("/config", summary="批量更新系统配置（热更新，缓存失效即时生效）")
async def update_configs(
    updates: dict = Body(..., description="配置键值对，如 {\"retrieval.top_k\": 6}"),
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    if not isinstance(updates, dict) or not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请求体应为非空 JSON 对象")
    try:
        await config_service.set_configs(db, updates, admin.id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"message": "配置已更新", "updated": list(updates.keys())}
