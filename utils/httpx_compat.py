#!/usr/bin/env python3
"""
httpx 兼容层 - 解决 ConnectError 不存在的问题
"""

import httpx as _httpx
from typing import Any

# 创建一个兼容的 httpx 模块
class HTTPXCompat:
    """httpx 兼容层，提供所有 httpx 功能并处理缺失的异常"""

    def __init__(self):
        # 复制所有 httpx 的属性
        for attr in dir(_httpx):
            if not attr.startswith('_'):
                setattr(self, attr, getattr(_httpx, attr))

        # 如果 ConnectError 不存在，创建一个兼容的版本
        if not hasattr(_httpx, 'ConnectError'):
            # 创建一个基于现有异常的 ConnectError
            class ConnectError(Exception):
                """兼容的 ConnectError 异常"""
                pass
            self.ConnectError = ConnectError

        # 如果 TimeoutException 不存在，创建一个兼容的版本
        if not hasattr(_httpx, 'TimeoutException'):
            class TimeoutException(Exception):
                """兼容的 TimeoutException 异常"""
                pass
            self.TimeoutException = TimeoutException

        # 如果 HTTPStatusError 不存在，创建一个兼容的版本
        if not hasattr(_httpx, 'HTTPStatusError'):
            class HTTPStatusError(Exception):
                """兼容的 HTTPStatusError 异常"""
                def __init__(self, message, *, request=None, response=None):
                    super().__init__(message)
                    self.request = request
                    self.response = response
            self.HTTPStatusError = HTTPStatusError

# 创建兼容的 httpx 实例
httpx_compat = HTTPXCompat()

# 导出所有需要的内容
__all__ = ['httpx_compat']
