"""认证服务：注册 / 登录 / 修改密码。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import utcnow_iso
from app.models import User


async def register(db: AsyncSession, username: str, password: str) -> User:
    existing = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if existing:
        raise ValueError("用户名已存在")
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    await db.commit()
    return user


async def login(db: AsyncSession, username: str, password: str) -> tuple[str, User]:
    """登录成功返回 (token, user)。失败统一抛出 ValueError（防用户名枚举）。"""
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")
    if not user.is_active:
        raise ValueError("账号已被禁用，请联系管理员")
    user.last_login_at = utcnow_iso()
    await db.commit()
    return create_access_token(user.id, user.role), user


async def change_password(
    db: AsyncSession, user: User, old_password: str, new_password: str
) -> None:
    if not verify_password(old_password, user.password_hash):
        raise ValueError("原密码错误")
    user.password_hash = hash_password(new_password)
    await db.commit()
