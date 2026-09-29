"""公共依赖：当前用户、管理员校验。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db=Depends(get_db),
) -> User:
    """解析 JWT 并加载用户；每次请求校验 is_active（禁用即时生效）。"""
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或登录已过期")
    payload = decode_access_token(cred.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或登录已过期")
    user = await db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号已被禁用，请联系管理员")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """仅管理员可访问（RBAC）。"""
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权限：仅管理员可访问")
    return user
