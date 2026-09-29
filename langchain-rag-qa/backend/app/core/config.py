"""全局配置模块：读取 backend/.env，集中管理所有可配置项。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend 目录（app/core/config.py 的上三级）
BASE_DIR = Path(__file__).resolve().parents[2]


def _resolve(path: str) -> Path:
    """相对路径统一解析到 backend 目录下，避免受进程工作目录影响。"""
    p = Path(path)
    return p if p.is_absolute() else BASE_DIR / p


class Settings(BaseSettings):
    """应用配置。字段与 .env 中的大写环境变量对应（大小写不敏感）。"""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 对话模型（OpenAI 兼容协议，供应商可切换：deepseek-* / dashscope）----
    # 按模型名前缀自动选择供应商密钥与地址（见 chat_api_key/chat_base_url 属性）
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    chat_model: str = "deepseek-chat"

    # ---- 嵌入模型 ----
    # local = BGE 本地模型（fastembed/ONNX，免费离线）；dashscope = text-embedding-v4（需百炼额度）
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    # ---- 重排模型 ----
    # local = 本地混合分数重排（向量相似度+BM25 加成）；dashscope = qwen3-rerank（需百炼额度）
    rerank_provider: str = "local"
    rerank_model: str = "qwen3-rerank"
    # 重排接口走 DashScope 原生端点（兼容模式无 rerank 路由）
    dashscope_rerank_url: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
    )

    # ---- 服务 ----
    secret_key: str = "dev-secret-key"
    jwt_expire_hours: int = 24
    database_url: str = "sqlite+aiosqlite:///./storage/ragkb.db"
    chroma_persist_dir: str = "./storage/chroma"
    upload_dir: str = "./storage/uploads"
    log_dir: str = "./storage/logs"

    # ---- 离线演示模式（无网络/无 Key 时兜底，LLM/嵌入/重排返回确定性假数据）----
    mock_mode: bool = False

    # ---- 限流开关（测试环境置 1 关闭） ----
    rate_limit_disabled: bool = False

    # ---- 上传限制 ----
    upload_max_size_mb: int = 50
    allowed_extensions: tuple[str, ...] = (".pdf", ".docx", ".txt", ".md", ".xlsx", ".csv")

    @property
    def chat_api_key(self) -> str:
        """对话密钥：模型名以 deepseek 开头 → DeepSeek，否则 DashScope。"""
        return self.deepseek_api_key if self.chat_model.startswith("deepseek") else self.dashscope_api_key

    @property
    def chat_base_url(self) -> str:
        return self.deepseek_base_url if self.chat_model.startswith("deepseek") else self.dashscope_base_url

    @property
    def sqlite_path(self) -> Path:
        raw = self.database_url.split(":///", 1)[-1]
        return _resolve(raw)

    @property
    def chroma_dir(self) -> Path:
        return _resolve(self.chroma_persist_dir)

    @property
    def uploads_dir(self) -> Path:
        return _resolve(self.upload_dir)

    @property
    def logs_dir(self) -> Path:
        return _resolve(self.log_dir)

    @property
    def models_dir(self) -> Path:
        """本地嵌入模型缓存目录（fastembed 下载的 ONNX 模型）。"""
        return _resolve("./storage/models")


@lru_cache
def get_settings() -> Settings:
    return Settings()
