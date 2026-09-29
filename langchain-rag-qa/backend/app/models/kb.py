"""知识库表：检索参数按库可配（修改仅影响新文档的切分，旧文档可 re-embed 重建）。"""
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class KnowledgeBase(TimestampMixin, Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    # 切分参数（影响新上传文档）
    chunk_size: Mapped[int] = mapped_column(Integer, default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50)
    # 检索参数
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    # 重排相关性阈值：实测 qwen3-rerank 相关片段 ~0.9、噪声 0.3~0.4，0.5 分界干净
    score_threshold: Mapped[float] = mapped_column(Float, default=0.5)
    rewrite_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
