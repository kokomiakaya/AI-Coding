"""消息表：会话内问答记录。sources 存引用片段，meta 存分阶段耗时等可观测数据。"""
from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow_iso


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user / assistant
    content: Mapped[str] = mapped_column(Text, default="")
    # 引用片段数组（结构见 services/rag/pipeline.py 的 build_sources）
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    # 分阶段耗时 / fallback / no_citation 等可观测数据（论文图表素材）
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    feedback: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 赞 / -1 踩
    feedback_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow_iso, index=True)
