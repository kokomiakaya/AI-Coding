"""用户管理接口（仅管理员）：列表 / 禁用启用 / 角色调整。"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import require_admin
from app.db.session import get_db
from app.models import User
from app.schemas.auth import UserOut, UserUpdateIn

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("", summary="用户列表（分页/搜索/角色筛选）")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    role: str | None = Query(default=None, pattern="^(admin|user)$"),
    _admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    filters = []
    if q:
        filters.append(User.username.like(f"%{q}%"))
    if role:
        filters.append(User.role == role)
    total = (
        await db.execute(select(func.count(User.id)).where(*filters))
    ).scalar_one()
    rows = (
        await db.execute(
            select(User).where(*filters).order_by(User.id).offset((page - 1) * size).limit(size)
        )
    ).scalars().all()
    return {
        "items": [UserOut.model_validate(u) for u in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@router.patch("/{user_id}", summary="更新用户（禁用/启用、角色调整）")
async def update_user(
    user_id: int,
    body: UserUpdateIn,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    # 保护管理员自身：不允许禁用自己或降级自己的角色
    if user.id == admin.id:
        if body.is_active is False or (body.role is not None and body.role != "admin"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能禁用自己或修改自己的管理员权限")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role
    await db.commit()
    return UserOut.model_validate(user)
