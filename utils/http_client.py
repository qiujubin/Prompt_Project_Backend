#!/usr/bin/env python3
"""
通用 HTTP 客户端工具
绕过 httpx 特定异常，提供统一的错误处理
"""

from utils.httpx_compat import httpx_compat as httpx
import asyncio
from typing import Dict, Any, Optional, Union
from core.logger import get_logger

logger = get_logger(__name__)


class HTTPClientError(Exception):
    """HTTP 客户端基础异常"""
    def __init__(self, message: str, error_code: str = "HTTP_ERROR", status_code: Optional[int] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class ConnectionError(HTTPClientError):
    """连接错误"""
    def __init__(self, message: str = "连接失败"):
        super().__init__(message, "CONNECTION_ERROR")


class TimeoutError(HTTPClientError):
    """超时错误"""
    def __init__(self, message: str = "请求超时"):
        super().__init__(message, "TIMEOUT_ERROR")


class HTTPError(HTTPClientError):
    """HTTP 状态码错误"""
    def __init__(self, message: str, status_code: int):
        super().__init__(message, "HTTP_ERROR", status_code)


class SafeHTTPClient:
    """安全的 HTTP 客户端，统一异常处理"""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def _handle_exception(self, e: Exception, url: str) -> HTTPClientError:
        """统一异常处理，避免依赖 httpx 特定异常"""
        error_str = str(e).lower()
        error_type = type(e).__name__.lower()

        logger.error(f"HTTP request failed for {url}: {type(e).__name__}: {e}")

        # 连接相关错误
        if (
            "connecterror" in error_str or "connection" in error_str or
            "connecterror" in error_type or "connectionerror" in error_type or
            "refused" in error_str or "unreachable" in error_str or
            "network" in error_str or "resolve" in error_str
        ):
            return ConnectionError(f"无法连接到服务器 {url}")

        # 超时相关错误
        elif "timeout" in error_str or "timeout" in error_type:
            return TimeoutError(f"请求超时 {url}")

        # HTTP 状态码错误
        elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            status_code = e.response.status_code
            return HTTPError(f"HTTP {status_code} 错误", status_code)

        # 其他错误
        else:
            return HTTPClientError(f"请求失败: {str(e)}", "UNKNOWN_ERROR")

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """安全的 GET 请求"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, **kwargs)
                response.raise_for_status()
                return response
        except Exception as e:
            raise self._handle_exception(e, url)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """安全的 POST 请求"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, **kwargs)
                response.raise_for_status()
                return response
        except Exception as e:
            raise self._handle_exception(e, url)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        """安全的 PUT 请求"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(url, **kwargs)
                response.raise_for_status()
                return response
        except Exception as e:
            raise self._handle_exception(e, url)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """安全的 DELETE 请求"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(url, **kwargs)
                response.raise_for_status()
                return response
        except Exception as e:
            raise self._handle_exception(e, url)

    def get_sync(self, url: str, **kwargs) -> httpx.Response:
        """同步 GET 请求"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, **kwargs)
                response.raise_for_status()
                return response
        except Exception as e:
            raise self._handle_exception(e, url)

    def post_sync(self, url: str, **kwargs) -> httpx.Response:
        """同步 POST 请求"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, **kwargs)
                response.raise_for_status()
                return response
        except Exception as e:
            raise self._handle_exception(e, url)


# 全局客户端实例
default_client = SafeHTTPClient()

# 便捷函数
async def safe_get(url: str, **kwargs) -> httpx.Response:
    """安全的异步 GET 请求"""
    return await default_client.get(url, **kwargs)

async def safe_post(url: str, **kwargs) -> httpx.Response:
    """安全的异步 POST 请求"""
    return await default_client.post(url, **kwargs)

def safe_get_sync(url: str, **kwargs) -> httpx.Response:
    """安全的同步 GET 请求"""
    return default_client.get_sync(url, **kwargs)

def safe_post_sync(url: str, **kwargs) -> httpx.Response:
    """安全的同步 POST 请求"""
    return default_client.post_sync(url, **kwargs)
