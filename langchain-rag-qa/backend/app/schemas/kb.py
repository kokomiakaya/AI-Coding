"""知识库模块 Schema。"""
from pydantic import BaseModel, ConfigDict, Field


class KBCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    rewrite_enabled: bool = True


class KBUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    chunk_size: int | None = Field(default=None, ge=100, le=2000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=500)
    top_k: int | None = Field(default=None, ge=1, le=20)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    rewrite_enabled: bool | None = None
    is_active: bool | None = None


class KBOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    score_threshold: float
    rewrite_enabled: bool
    is_active: bool
    created_at: str
    document_count: int = 0
    chunk_count: int = 0


class SearchTestIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
