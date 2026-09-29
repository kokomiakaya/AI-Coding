"""认证接口：注册 / 登录 / 当前用户 / 修改密码（登录注册走 IP 限流防撞库）。"""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.models import User
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])

LOGIN_RATE = (5, 60)  # 5 次 / 分钟 / IP


def _check_rate(request: Request) -> None:
    if get_settings().rate_limit_disabled:
        return
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(f"auth:{client_ip}", *LOGIN_RATE):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "尝试过于频繁，请稍后再试")


@router.post("/register", summary="用户注册")
async def register(body: RegisterIn, request: Request, db=Depends(get_db)):
    _check_rate(request)
    try:
        user = await auth_service.register(db, body.username, body.password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return UserOut.model_validate(user)


@router.post("/login", summary="用户登录")
async def login(body: LoginIn, request: Request, db=Depends(get_db)):
    _check_rate(request)
    try:
        token, user = await auth_service.login(db, body.username, body.password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", summary="当前用户信息")
async def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.post("/change-password", summary="修改密码（需校验旧密码）")
async def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        await auth_service.change_password(db, user, body.old_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"message": "密码修改成功"}
