"""问答模块 Schema。"""
from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: int | None = None  # 为空则自动新建会话
    kb_id: int | None = None  # 为空则使用会话绑定/全部知识库


class FeedbackIn(BaseModel):
    rate: int = Field(ge=-1, le=1)  # 1 赞 / -1 踩
    comment: str | None = Field(default=None, max_length=500)
