"""文档模块 Schema。"""
from pydantic import BaseModel, ConfigDict, Field


class TextDocIn(BaseModel):
    """直接录入文本（无需上传文件，粘贴内容即可入库解析）。"""

    filename: str = Field(default="手动录入文本", max_length=100)
    content: str = Field(min_length=1, max_length=200000)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kb_id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: str


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    content: str
    meta: dict
