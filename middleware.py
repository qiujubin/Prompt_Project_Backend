"""中间件：性能监控。

记录每次请求的耗时与状态码，便于后续日志分析与性能优化。
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time
from core.logger import get_logger

logger = get_logger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """简单的请求耗时统计中间件。"""

    async def dispatch(self, request: Request, call_next):
        """在处理请求前后记录时间，并输出日志。"""
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration_ms:.2f}ms")
        return response

