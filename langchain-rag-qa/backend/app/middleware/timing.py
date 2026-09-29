"""请求计时中间件：统一记录接口耗时（可观测性）。"""
import time
import uuid

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = uuid.uuid4().hex[:8]
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} -> "
            f"{response.status_code} ({duration_ms:.0f}ms)"
        )
        return response
