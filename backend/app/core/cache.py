"""缓存抽象层：当前实现为进程内 TTLCache，生产环境可替换为 Redis 实现（论文论述点）。"""
import threading
from typing import Any, Protocol

from cachetools import TTLCache


class CacheBackend(Protocol):
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def invalidate_prefix(self, prefix: str) -> None: ...
    def clear(self) -> None: ...


class TTLCacheBackend:
    """线程安全的进程内 TTL 缓存。"""

    def __init__(self, maxsize: int = 2048, ttl: float = 300.0) -> None:
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [k for k in self._cache if k.startswith(prefix)]:
                self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


cache: CacheBackend = TTLCacheBackend()
