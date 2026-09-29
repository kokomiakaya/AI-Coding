"""限流抽象层：当前实现为内存滑动窗口，生产环境可替换为 Redis 分布式限流（论文论述点）。"""
import threading
import time
from collections import defaultdict, deque
from typing import Protocol


class RateLimiter(Protocol):
    def check(self, key: str, limit: int, window_seconds: float) -> bool: ...


class SlidingWindowRateLimiter:
    """按 key 记录请求时间戳的滑动窗口限流器。"""

    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: float) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


rate_limiter = SlidingWindowRateLimiter()
