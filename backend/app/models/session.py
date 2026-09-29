"""会话表：每个用户独立的多会话，历史持久化可找回。"""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChatSession(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # 会话绑定的知识库；NULL 表示全部知识库检索
    kb_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_bases.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="新会话")
