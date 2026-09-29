"""FAISS 向量存储实现（可选回退方案，需手动 pip install faiss-cpu）。

仅在 chromadb 不可用时启用。按 KB 落盘索引文件 + id→metadata 映射。
"""
import asyncio
import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.vectorstore.base import BaseVectorStore, VectorHit, VectorRecord


class FAISSVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        import faiss  # 延迟导入：未安装时在工厂层拦截

        self._faiss = faiss
        settings = get_settings()
        self._dir: Path = settings.chroma_dir / "faiss"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._dim = settings.embedding_dim
        self._cache: dict[int, tuple[Any, dict[str, dict]]] = {}

    def _kb_dir(self, kb_id: int) -> Path:
        p = self._dir / f"kb_{kb_id}"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _load(self, kb_id: int):
        """加载（或缓存）KB 的索引与 id→metadata 映射。"""
        if kb_id in self._cache:
            return self._cache[kb_id]
        idx_path = self._kb_dir(kb_id) / "index.faiss"
        meta_path = self._kb_dir(kb_id) / "meta.json"
        index = None
        meta: dict[str, dict] = {}
        if idx_path.exists() and meta_path.exists():
            index = self._faiss.read_index(str(idx_path))
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        self._cache[kb_id] = (index, meta)
        return index, meta

    def _persist(self, kb_id: int, index, meta: dict[str, dict]) -> None:
        self._faiss.write_index(index, str(self._kb_dir(kb_id) / "index.faiss"))
        with open(self._kb_dir(kb_id) / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        self._cache[kb_id] = (index, meta)

    async def upsert(self, kb_id: int, records: list[VectorRecord]) -> None:
        def _do() -> None:
            import numpy as np

            index, meta = self._load(kb_id)
            if index is None:
                index = self._faiss.IndexFlatIP(self._dim)  # 内积（配合 L2 归一化=余弦）
            vecs = np.array([r.embedding for r in records], dtype="float32")
            self._faiss.normalize_L2(vecs)
            ids = np.array([[r.chunk_id] for r in records], dtype="int64")
            index.add_with_ids(vecs, ids)
            for r in records:
                meta[str(r.chunk_id)] = {"text": r.text, **r.metadata}
            self._persist(kb_id, index, meta)

        await asyncio.to_thread(_do)

    async def delete_document(self, kb_id: int, document_id: int) -> None:
        def _do() -> None:
            import numpy as np

            index, meta = self._load(kb_id)
            if index is None:
                return
            keep_ids = {
                int(cid) for cid, m in meta.items() if m.get("document_id") != document_id
            }
            removed = [cid for cid, m in meta.items() if m.get("document_id") == document_id]
            for cid in removed:
                meta.pop(cid, None)
            if keep_ids:
                # 用保留向量重建索引（回退方案不做增量删除，重建开销可接受）
                ids = np.array([[cid] for cid in sorted(keep_ids)], dtype="int64")
                vecs = np.array(
                    [
                        index.reconstruct(int(idx))
                        for idx in range(index.ntotal)
                        if int(index.id_at(idx)) in keep_ids
                    ],
                    dtype="float32",
                )
                new_index = self._faiss.IndexFlatIP(self._dim)
                new_index.add_with_ids(vecs, ids)
                self._persist(kb_id, new_index, meta)
            else:
                self._persist(kb_id, self._faiss.IndexFlatIP(self._dim), meta)

        await asyncio.to_thread(_do)

    async def delete_kb(self, kb_id: int) -> None:
        def _do() -> None:
            import shutil

            shutil.rmtree(self._kb_dir(kb_id), ignore_errors=True)
            self._cache.pop(kb_id, None)

        await asyncio.to_thread(_do)

    async def search(
        self, kb_ids: list[int], query_embedding: list[float], top_k: int
    ) -> list[VectorHit]:
        def _do() -> list[VectorHit]:
            import numpy as np

            q = np.array([query_embedding], dtype="float32")
            self._faiss.normalize_L2(q)
            hits: list[VectorHit] = []
            for kb_id in kb_ids:
                index, meta = self._load(kb_id)
                if index is None or index.ntotal == 0:
                    continue
                scores, ids = index.search(q, min(top_k, index.ntotal))
                for score, cid in zip(scores[0], ids[0]):
                    if cid < 0:
                        continue
                    info = meta.get(str(int(cid)), {})
                    hits.append(VectorHit(chunk_id=int(cid), similarity=float(score), metadata=info))
            return hits

        return await asyncio.to_thread(_do)

    def health(self) -> dict:
        try:
            return {"backend": "faiss", "ok": True, "collections": len(list(self._dir.glob("kb_*")))}
        except Exception as exc:
            return {"backend": "faiss", "ok": False, "error": str(exc)[:200]}
