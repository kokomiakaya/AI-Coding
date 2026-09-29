"""嵌入服务：三种实现，按配置切换（embedding_provider）：
- BgeEmbedder：本地 BGE 中文模型（fastembed/ONNX，免费、离线、无 API 依赖）
- DashScopeEmbedder：text-embedding-v4 批量嵌入（httpx 直调兼容模式 /embeddings）
- HashEmbedder：离线演示模式（MOCK_MODE）的确定性伪向量

统一封装批量调用与维度校验；供应商可插拔（论文论述点）。
"""
import asyncio
import hashlib
import math

import httpx
import jieba
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings


class BaseEmbedder:
    async def embed_query(self, text: str) -> list[float]: ...
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class DashScopeEmbedder(BaseEmbedder):
    """百炼兼容模式文本嵌入客户端（OpenAI 协议）。"""

    def __init__(self) -> None:
        s = get_settings()
        self._client = httpx.AsyncClient(timeout=60.0)
        self._url = s.dashscope_base_url.rstrip("/") + "/embeddings"
        self._key = s.dashscope_api_key
        self._model = s.embedding_model
        self.dim = s.embedding_dim
        self._batch = 16  # 单次请求最多 16 条（批量调用降低 API 次数）

    async def close(self) -> None:
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10), reraise=True)
    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.post(
            self._url,
            headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
            json={"model": self._model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if len(data) != len(texts):
            raise RuntimeError(f"嵌入返回数量不一致：期望 {len(texts)}，实际 {len(data)}")
        data.sort(key=lambda d: d.get("index", 0))
        vectors = [d["embedding"] for d in data]
        # 维度校验：换 embedding 模型后维度不匹配会在此处快速暴露
        if any(len(v) != self.dim for v in vectors):
            raise RuntimeError(f"嵌入维度与配置不符（期望 {self.dim}），请检查 embedding_model 配置")
        return vectors

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), self._batch):
            results.extend(await self._embed_batch(texts[i : i + self._batch]))
        return results

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed_batch([text]))[0]


class BgeEmbedder(BaseEmbedder):
    """本地 BGE 中文嵌入（fastembed + ONNX Runtime，CPU 推理）。

    免费、离线、无需 API Key；首次使用自动下载模型到 storage/models（约 100MB，
    国内网络可设 HF_ENDPOINT=https://hf-mirror.com），之后启动秒级加载。
    推理走线程池包装，不阻塞事件循环。
    """

    def __init__(self) -> None:
        s = get_settings()
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=s.embedding_model, cache_dir=str(s.models_dir))
        self.dim = s.embedding_dim
        self._batch = 32

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors = await asyncio.to_thread(lambda: list(self._model.embed(texts)))
        if any(len(v) != self.dim for v in vectors):
            raise RuntimeError(
                f"嵌入维度与配置不符（期望 {self.dim}，实际 {len(vectors[0])}），"
                "请检查 embedding_model / embedding_dim 配置"
            )
        return [v.tolist() for v in vectors]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), self._batch):
            results.extend(await self._embed_batch(texts[i : i + self._batch]))
        return results

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed_batch([text]))[0]


class HashEmbedder(BaseEmbedder):
    """离线演示模式：基于 jieba 分词的哈希投影伪向量。

    确定性输出、同词相似（词袋哈希投影 + 归一化），
    与真实嵌入的检索逻辑同构，便于无网络环境演示与测试。
    """

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in jieba.cut_for_search(text):
            token = token.strip()
            if not token:
                continue
            digest = hashlib.md5(token.encode("utf-8")).digest()
            for k in range(4):  # 每个词打 4 个哈希槽
                idx = int.from_bytes(digest[k * 4 : k * 4 + 4], "little") % self.dim
                sign = 1.0 if digest[k * 4 + 3] & 1 else -1.0
                vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]


def build_embedder() -> BaseEmbedder:
    s = get_settings()
    if s.mock_mode:
        return HashEmbedder(s.embedding_dim)
    if s.embedding_provider == "local":
        return BgeEmbedder()
    return DashScopeEmbedder()
