"""
ComfyUI Error Retry Mechanism

Provides robust retry logic with exponential backoff, circuit breaker pattern,
and intelligent error classification.

Performance Optimizations:
- Exponential backoff with jitter to prevent thundering herd
- Circuit breaker pattern to fail fast when service is down
- Intelligent error classification for better retry decisions
- Metrics collection for monitoring retry behavior
"""
import asyncio
import time
import functools
from typing import Callable, TypeVar, Any, Optional, List, Type, Dict
from dataclasses import dataclass, field
from enum import Enum
import random

from core.comfyui_config import get_comfyui_settings
from core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class RetryableError(Exception):
    """可重试的错误基类"""
    pass


class ConnectionError(RetryableError):
    """连接错误"""
    pass


class TimeoutError(RetryableError):
    """超时错误"""
    pass


class ServerBusyError(RetryableError):
    """服务器繁忙错误"""
    pass


class NonRetryableError(Exception):
    """不可重试的错误基类"""
    pass


class ValidationError(NonRetryableError):
    """验证错误"""
    pass


class AuthenticationError(NonRetryableError):
    """认证错误"""
    pass


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retryable_exceptions: List[Type[Exception]] = field(
        default_factory=lambda: [RetryableError, ConnectionError, TimeoutError, ServerBusyError]
    )


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5  # 触发熔断的失败次数
    success_threshold: int = 3  # 恢复正常的成功次数
    timeout: float = 60.0  # 熔断超时时间（秒）
    half_open_max_calls: int = 3  # 半开状态最大调用次数


class CircuitBreaker:
    """熔断器实现

    防止在服务不可用时持续发送请求，保护系统资源
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # 检查是否超时，可以进入半开状态
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.config.timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        logger.info(f"Circuit breaker {self.name} entering half-open state")
                        return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self):
        """记录成功"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(f"Circuit breaker {self.name} closed (recovered)")
            else:
                self._failure_count = 0

    async def record_failure(self):
        """记录失败"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
                logger.warning(f"Circuit breaker {self.name} opened (half-open failed)")
            elif self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} opened (threshold reached)")

    def get_stats(self) -> Dict[str, Any]:
        """获取熔断器统计信息"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time
        }


class RetryHandler:
    """重试处理器

    提供带有指数退避的重试逻辑
    """

    def __init__(self, config: RetryConfig = None):
        self.settings = get_comfyui_settings()
        self.config = config or RetryConfig(
            max_attempts=self.settings.max_retry_attempts,
            initial_delay=self.settings.retry_delay,
            max_delay=self.settings.retry_max_delay,
            exponential_base=self.settings.retry_exponential_base
        )

    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟

        使用指数退避算法，可选添加抖动
        """
        delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            jitter = delay * self.config.jitter_factor * random.random()
            delay = delay + jitter

        return delay

    def is_retryable(self, exception: Exception) -> bool:
        """判断异常是否可重试"""
        # 检查是否是不可重试的异常
        if isinstance(exception, NonRetryableError):
            return False

        # 检查是否是可重试的异常
        for exc_type in self.config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True

        # 检查常见的可重试错误
        error_msg = str(exception).lower()
        retryable_patterns = [
            "connection",
            "timeout",
            "temporarily unavailable",
            "service unavailable",
            "too many requests",
            "rate limit",
            "busy",
            "overloaded"
        ]

        for pattern in retryable_patterns:
            if pattern in error_msg:
                return True

        return False

    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        circuit_breaker: CircuitBreaker = None,
        **kwargs
    ) -> T:
        """执行带重试的函数

        Args:
            func: 要执行的异步函数
            *args: 函数参数
            circuit_breaker: 可选的熔断器
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 重试次数用尽后抛出最后一个异常
        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            # 检查熔断器
            if circuit_breaker:
                if not await circuit_breaker.can_execute():
                    raise RuntimeError(f"Circuit breaker {circuit_breaker.name} is open")

            try:
                result = await func(*args, **kwargs)

                # 记录成功
                if circuit_breaker:
                    await circuit_breaker.record_success()

                return result

            except Exception as e:
                last_exception = e

                # 记录失败
                if circuit_breaker:
                    await circuit_breaker.record_failure()

                # 检查是否可重试
                if not self.is_retryable(e):
                    logger.error(f"Non-retryable error: {e}")
                    raise

                # 检查是否还有重试次数
                if attempt < self.config.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.config.max_attempts} attempts failed. Last error: {e}"
                    )

        raise last_exception


def with_retry(
    max_attempts: int = None,
    initial_delay: float = None,
    circuit_breaker_name: str = None
):
    """重试装饰器

    用于装饰需要重试逻辑的异步函数

    Args:
        max_attempts: 最大重试次数
        initial_delay: 初始延迟
        circuit_breaker_name: 熔断器名称
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        settings = get_comfyui_settings()

        config = RetryConfig(
            max_attempts=max_attempts or settings.max_retry_attempts,
            initial_delay=initial_delay or settings.retry_delay,
            max_delay=settings.retry_max_delay,
            exponential_base=settings.retry_exponential_base
        )

        handler = RetryHandler(config)
        circuit_breaker = None

        if circuit_breaker_name:
            circuit_breaker = CircuitBreaker(circuit_breaker_name)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute_with_retry(
                func, *args,
                circuit_breaker=circuit_breaker,
                **kwargs
            )

        return wrapper

    return decorator


# 全局熔断器管理
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_cb_lock = asyncio.Lock()


async def get_circuit_breaker(name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """获取或创建熔断器"""
    async with _cb_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def get_all_circuit_breaker_stats() -> Dict[str, Any]:
    """获取所有熔断器的统计信息"""
    return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}


def classify_error(exception: Exception) -> str:
    """分类错误类型

    返回错误代码，用于前端显示和日志记录
    """
    error_msg = str(exception).lower()

    # 连接错误
    if any(p in error_msg for p in ["connection refused", "connect error", "no route"]):
        return "CONNECTION_REFUSED"

    if any(p in error_msg for p in ["timeout", "timed out"]):
        return "CONNECTION_TIMEOUT"

    # 资源错误
    if any(p in error_msg for p in ["out of memory", "cuda", "gpu"]):
        return "OUT_OF_MEMORY"

    if any(p in error_msg for p in ["model not found", "checkpoint not found"]):
        return "MODEL_NOT_FOUND"

    if any(p in error_msg for p in ["node", "plugin", "custom node"]):
        return "PLUGIN_MISSING"

    # 服务器错误
    if any(p in error_msg for p in ["busy", "overloaded", "too many"]):
        return "SERVER_BUSY"

    if any(p in error_msg for p in ["rate limit", "throttle"]):
        return "RATE_LIMITED"

    # 验证错误
    if any(p in error_msg for p in ["invalid", "validation", "parameter"]):
        return "VALIDATION_ERROR"

    return "UNKNOWN_ERROR"


def get_error_suggestion(error_code: str) -> str:
    """获取错误建议

    根据错误代码返回用户友好的建议
    """
    suggestions = {
        "CONNECTION_REFUSED": "请检查 ComfyUI 是否正在运行，以及地址和端口是否正确。",
        "CONNECTION_TIMEOUT": "连接超时，请检查网络连接和服务器状态。",
        "OUT_OF_MEMORY": "GPU 内存不足，请尝试降低图像分辨率或关闭其他占用 GPU 的程序。",
        "MODEL_NOT_FOUND": "找不到指定的模型文件，请检查模型是否存在于 ComfyUI 的 models 目录。",
        "PLUGIN_MISSING": "缺少必要的 ComfyUI 插件，请使用 ComfyUI Manager 安装缺失的插件。",
        "SERVER_BUSY": "服务器繁忙，请稍后重试。",
        "RATE_LIMITED": "请求过于频繁，请稍后重试。",
        "VALIDATION_ERROR": "参数验证失败，请检查输入参数是否正确。",
        "UNKNOWN_ERROR": "发生未知错误，请查看日志获取更多信息。"
    }

    return suggestions.get(error_code, suggestions["UNKNOWN_ERROR"])


# 重试指标收集器
class RetryMetrics:
    """重试指标收集器

    收集和报告重试机制的性能指标
    """

    def __init__(self):
        self._metrics: Dict[str, Any] = {
            "total_attempts": 0,
            "successful_attempts": 0,
            "failed_attempts": 0,
            "retries_performed": 0,
            "circuit_breaker_trips": 0,
            "errors_by_type": {},
            "last_reset": time.time()
        }
        self._lock = asyncio.Lock()

    async def record_attempt(self, success: bool, retries: int = 0):
        """记录尝试结果"""
        async with self._lock:
            self._metrics["total_attempts"] += 1
            if success:
                self._metrics["successful_attempts"] += 1
            else:
                self._metrics["failed_attempts"] += 1
            self._metrics["retries_performed"] += retries

    async def record_error(self, error_code: str):
        """记录错误类型"""
        async with self._lock:
            if error_code not in self._metrics["errors_by_type"]:
                self._metrics["errors_by_type"][error_code] = 0
            self._metrics["errors_by_type"][error_code] += 1

    async def record_circuit_breaker_trip(self):
        """记录熔断器触发"""
        async with self._lock:
            self._metrics["circuit_breaker_trips"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        metrics = self._metrics.copy()

        # 计算成功率
        if metrics["total_attempts"] > 0:
            metrics["success_rate"] = (
                metrics["successful_attempts"] / metrics["total_attempts"]
            )
        else:
            metrics["success_rate"] = 0.0

        # 计算平均重试次数
        if metrics["successful_attempts"] > 0:
            metrics["avg_retries_per_success"] = (
                metrics["retries_performed"] / metrics["successful_attempts"]
            )
        else:
            metrics["avg_retries_per_success"] = 0.0

        return metrics

    async def reset(self):
        """重置指标"""
        async with self._lock:
            self._metrics = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "retries_performed": 0,
                "circuit_breaker_trips": 0,
                "errors_by_type": {},
                "last_reset": time.time()
            }


# 全局重试指标收集器
_retry_metrics = RetryMetrics()


def get_retry_metrics() -> RetryMetrics:
    """获取全局重试指标收集器"""
    return _retry_metrics


# 增强的重试处理器（带指标收集）
class EnhancedRetryHandler(RetryHandler):
    """增强的重试处理器

    在基础重试处理器上添加指标收集功能
    """

    def __init__(self, config: RetryConfig = None):
        super().__init__(config)
        self.metrics = get_retry_metrics()

    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        circuit_breaker: CircuitBreaker = None,
        **kwargs
    ) -> T:
        """执行带重试的函数（带指标收集）"""
        retries = 0
        last_exception = None

        for attempt in range(self.config.max_attempts):
            # 检查熔断器
            if circuit_breaker:
                if not await circuit_breaker.can_execute():
                    await self.metrics.record_circuit_breaker_trip()
                    raise RuntimeError(f"Circuit breaker {circuit_breaker.name} is open")

            try:
                result = await func(*args, **kwargs)

                # 记录成功
                if circuit_breaker:
                    await circuit_breaker.record_success()

                await self.metrics.record_attempt(success=True, retries=retries)
                return result

            except Exception as e:
                last_exception = e
                retries += 1

                # 记录失败
                if circuit_breaker:
                    await circuit_breaker.record_failure()

                # 分类错误
                error_code = classify_error(e)
                await self.metrics.record_error(error_code)

                # 检查是否可重试
                if not self.is_retryable(e):
                    logger.error(f"Non-retryable error: {e}")
                    await self.metrics.record_attempt(success=False, retries=retries)
                    raise

                # 检查是否还有重试次数
                if attempt < self.config.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.config.max_attempts} attempts failed. Last error: {e}"
                    )
                    await self.metrics.record_attempt(success=False, retries=retries)

        raise last_exception
