"""会话模块 Schema。"""
from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    kb_id: int | None = None


class SessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    kb_id: int | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    kb_id: int | None = None
    created_at: str
    updated_at: str
    last_message: str | None = None
    message_count: int = 0


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    sources: list | None = None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    meta: dict
    feedback: int | None = None
    created_at: str
