"""基础设施单元测试：滑动窗口限流 + TTL 缓存。"""
from app.core.cache import TTLCacheBackend
from app.core.rate_limit import SlidingWindowRateLimiter


def test_sliding_window_limit():
    rl = SlidingWindowRateLimiter()
    assert rl.check("k", 2, 60) is True
    assert rl.check("k", 2, 60) is True
    assert rl.check("k", 2, 60) is False  # 第 3 次超限


def test_sliding_window_keys_isolated():
    rl = SlidingWindowRateLimiter()
    assert rl.check("a", 1, 60) is True
    assert rl.check("a", 1, 60) is False
    assert rl.check("b", 1, 60) is True  # 不同 key 互不影响


def test_ttl_cache_get_set():
    c = TTLCacheBackend(ttl=60)
    assert c.get("missing") is None
    c.set("k1", {"a": 1})
    assert c.get("k1") == {"a": 1}


def test_ttl_cache_invalidate_prefix():
    c = TTLCacheBackend(ttl=60)
    c.set("cfg:a", 1)
    c.set("cfg:b", 2)
    c.set("other", 3)
    c.invalidate_prefix("cfg:")
    assert c.get("cfg:a") is None
    assert c.get("cfg:b") is None
    assert c.get("other") == 3
