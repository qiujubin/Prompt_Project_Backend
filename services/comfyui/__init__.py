"""
ComfyUI Integration Services
"""

from .client import ComfyUIClient
from .manager import ComfyUIManager
from .websocket import ComfyUIWebSocketHandler
from .connection_pool import (
    WebSocketConnectionPool,
    HTTPClientPool,
    ConnectionPoolManager,
    PooledConnection,
    ConnectionState
)
from .task_queue import (
    TaskQueue,
    TaskInfo,
    TaskStatus,
    TaskPriority,
    get_task_queue,
    shutdown_task_queue
)
from .retry import (
    RetryHandler,
    RetryConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    with_retry,
    get_circuit_breaker,
    classify_error,
    get_error_suggestion,
    RetryableError,
    NonRetryableError
)

__all__ = [
    # Core
    'ComfyUIClient',
    'ComfyUIManager',
    'ComfyUIWebSocketHandler',
    # Connection Pool
    'WebSocketConnectionPool',
    'HTTPClientPool',
    'ConnectionPoolManager',
    'PooledConnection',
    'ConnectionState',
    # Task Queue
    'TaskQueue',
    'TaskInfo',
    'TaskStatus',
    'TaskPriority',
    'get_task_queue',
    'shutdown_task_queue',
    # Retry
    'RetryHandler',
    'RetryConfig',
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'with_retry',
    'get_circuit_breaker',
    'classify_error',
    'get_error_suggestion',
    'RetryableError',
    'NonRetryableError'
]
