"""
ComfyUI Connection Pool Management

Provides efficient connection pooling for both WebSocket and HTTP connections
to ComfyUI servers, with health checking and automatic reconnection.

Performance Optimizations:
- Connection reuse to reduce connection overhead
- Health checking to maintain connection quality
- Automatic cleanup of idle connections
- Metrics collection for monitoring
"""
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import websockets
from utils.httpx_compat import httpx_compat as httpx
from websockets.exceptions import ConnectionClosed, WebSocketException

from core.comfyui_config import get_comfyui_settings
from core.logger import get_logger

logger = get_logger(__name__)


class ConnectionState(Enum):
    """连接状态枚举"""
    IDLE = "idle"
    IN_USE = "in_use"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class PooledConnection:
    """连接池中的连接对象"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    websocket: Optional[websockets.WebSocketClientProtocol] = None
    state: ConnectionState = ConnectionState.DISCONNECTED
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    last_health_check: float = field(default_factory=time.time)
    error_count: int = 0
    client_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class WebSocketConnectionPool:
    """WebSocket 连接池管理器

    提供高效的 WebSocket 连接复用，支持：
    - 连接池大小限制
    - 空闲连接回收
    - 健康检查
    - 自动重连
    """

    def __init__(self, server_address: str = None):
        self.settings = get_comfyui_settings()
        self.server_address = server_address or f"{self.settings.host}:{self.settings.port}"
        self._pool: Dict[str, PooledConnection] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动连接池"""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting WebSocket connection pool for {self.server_address}")

        # 启动健康检查任务
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """停止连接池"""
        self._running = False

        # 取消后台任务
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 关闭所有连接
        async with self._lock:
            for conn in self._pool.values():
                if conn.websocket:
                    try:
                        await conn.websocket.close()
                    except Exception as e:
                        logger.warning(f"Error closing connection {conn.id}: {e}")
            self._pool.clear()

        logger.info("WebSocket connection pool stopped")

    async def acquire(self, timeout: float = None) -> PooledConnection:
        """获取一个可用连接

        Args:
            timeout: 获取连接的超时时间

        Returns:
            PooledConnection: 可用的连接对象

        Raises:
            TimeoutError: 获取连接超时
            RuntimeError: 连接池已满且无法创建新连接
        """
        timeout = timeout or self.settings.connect_timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            async with self._lock:
                # 尝试获取空闲连接
                for conn_id, conn in self._pool.items():
                    if conn.state == ConnectionState.IDLE and conn.websocket:
                        conn.state = ConnectionState.IN_USE
                        conn.last_used_at = time.time()
                        logger.debug(f"Acquired existing connection {conn.id}")
                        return conn

                # 如果池未满，创建新连接
                if len(self._pool) < self.settings.pool_size:
                    conn = await self._create_connection()
                    if conn:
                        conn.state = ConnectionState.IN_USE
                        self._pool[conn.id] = conn
                        logger.debug(f"Created new connection {conn.id}")
                        return conn

            # 等待一段时间后重试
            await asyncio.sleep(0.1)

        raise TimeoutError("Failed to acquire connection from pool")

    async def release(self, conn: PooledConnection):
        """释放连接回连接池

        Args:
            conn: 要释放的连接对象
        """
        async with self._lock:
            if conn.id in self._pool:
                if conn.websocket and not conn.websocket.closed:
                    conn.state = ConnectionState.IDLE
                    conn.last_used_at = time.time()
                    logger.debug(f"Released connection {conn.id}")
                else:
                    # 连接已关闭，从池中移除
                    del self._pool[conn.id]
                    logger.debug(f"Removed closed connection {conn.id}")

    async def _create_connection(self) -> Optional[PooledConnection]:
        """创建新的 WebSocket 连接"""
        conn = PooledConnection()
        conn.state = ConnectionState.CONNECTING

        try:
            ws_protocol = "wss" if self.settings.protocol == "https" else "ws"
            ws_url = f"{ws_protocol}://{self.server_address}/ws?clientId={conn.client_id}"

            conn.websocket = await asyncio.wait_for(
                websockets.connect(ws_url),
                timeout=self.settings.connect_timeout
            )

            conn.state = ConnectionState.IDLE
            conn.created_at = time.time()
            conn.last_used_at = time.time()
            conn.last_health_check = time.time()

            logger.info(f"Created WebSocket connection {conn.id} to {self.server_address}")
            return conn

        except Exception as e:
            logger.error(f"Failed to create WebSocket connection: {e}")
            conn.state = ConnectionState.ERROR
            conn.error_count += 1
            return None

    async def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                await asyncio.sleep(self.settings.pool_health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _perform_health_check(self):
        """执行健康检查"""
        async with self._lock:
            for conn_id, conn in list(self._pool.items()):
                if conn.state == ConnectionState.IDLE:
                    try:
                        # 发送 ping 检查连接是否存活
                        if conn.websocket and not conn.websocket.closed:
                            pong = await asyncio.wait_for(
                                conn.websocket.ping(),
                                timeout=5.0
                            )
                            await pong
                            conn.last_health_check = time.time()
                            conn.error_count = 0
                        else:
                            raise ConnectionError("WebSocket is closed")
                    except Exception as e:
                        logger.warning(f"Health check failed for connection {conn.id}: {e}")
                        conn.error_count += 1

                        # 如果错误次数过多，移除连接
                        if conn.error_count >= 3:
                            if conn.websocket:
                                try:
                                    await conn.websocket.close()
                                except:
                                    pass
                            del self._pool[conn_id]
                            logger.info(f"Removed unhealthy connection {conn.id}")

    async def _cleanup_loop(self):
        """清理空闲连接循环"""
        while self._running:
            try:
                await asyncio.sleep(self.settings.cleanup_interval)
                await self._cleanup_idle_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_idle_connections(self):
        """清理空闲时间过长的连接"""
        current_time = time.time()

        async with self._lock:
            for conn_id, conn in list(self._pool.items()):
                if conn.state == ConnectionState.IDLE:
                    idle_time = current_time - conn.last_used_at

                    if idle_time > self.settings.pool_max_idle_time:
                        if conn.websocket:
                            try:
                                await conn.websocket.close()
                            except:
                                pass
                        del self._pool[conn_id]
                        logger.info(f"Cleaned up idle connection {conn.id} (idle for {idle_time:.1f}s)")

    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        stats = {
            "total_connections": len(self._pool),
            "idle_connections": 0,
            "in_use_connections": 0,
            "error_connections": 0,
            "pool_size_limit": self.settings.pool_size,
        }

        for conn in self._pool.values():
            if conn.state == ConnectionState.IDLE:
                stats["idle_connections"] += 1
            elif conn.state == ConnectionState.IN_USE:
                stats["in_use_connections"] += 1
            elif conn.state == ConnectionState.ERROR:
                stats["error_connections"] += 1

        return stats


class HTTPClientPool:
    """HTTP 客户端连接池

    使用 httpx 的连接池功能，提供高效的 HTTP 请求复用
    """

    def __init__(self, server_address: str = None):
        self.settings = get_comfyui_settings()
        self.server_address = server_address or f"{self.settings.host}:{self.settings.port}"
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端实例"""
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        base_url=f"http://{self.server_address}",
                        timeout=httpx.Timeout(
                            connect=self.settings.connect_timeout,
                            read=self.settings.request_timeout,
                            write=self.settings.request_timeout,
                            pool=self.settings.connect_timeout
                        ),
                        limits=httpx.Limits(
                            max_connections=self.settings.http_pool_size,
                            max_keepalive_connections=self.settings.http_pool_size,
                            keepalive_expiry=self.settings.http_keepalive_expiry
                        )
                    )
        return self._client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


# 全局连接池管理器
class ConnectionPoolManager:
    """全局连接池管理器

    管理多个服务器地址的连接池
    """

    _instance: Optional['ConnectionPoolManager'] = None
    _ws_pools: Dict[str, WebSocketConnectionPool] = {}
    _http_pools: Dict[str, HTTPClientPool] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> 'ConnectionPoolManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_ws_pool(self, server_address: str = None) -> WebSocketConnectionPool:
        """获取指定服务器的 WebSocket 连接池"""
        settings = get_comfyui_settings()
        address = server_address or f"{settings.host}:{settings.port}"

        async with self._lock:
            if address not in self._ws_pools:
                pool = WebSocketConnectionPool(address)
                await pool.start()
                self._ws_pools[address] = pool
            return self._ws_pools[address]

    async def get_http_pool(self, server_address: str = None) -> HTTPClientPool:
        """获取指定服务器的 HTTP 连接池"""
        settings = get_comfyui_settings()
        address = server_address or f"{settings.host}:{settings.port}"

        async with self._lock:
            if address not in self._http_pools:
                self._http_pools[address] = HTTPClientPool(address)
            return self._http_pools[address]

    async def close_all(self):
        """关闭所有连接池"""
        async with self._lock:
            for pool in self._ws_pools.values():
                await pool.stop()
            for pool in self._http_pools.values():
                await pool.close()
            self._ws_pools.clear()
            self._http_pools.clear()

    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有连接池的统计信息"""
        stats = {
            "websocket_pools": {},
            "http_pools": len(self._http_pools)
        }

        for address, pool in self._ws_pools.items():
            stats["websocket_pools"][address] = pool.get_stats()

        return stats


# 连接池性能指标收集器
class ConnectionPoolMetrics:
    """连接池性能指标收集器

    收集和报告连接池的性能指标，用于监控和优化
    """

    def __init__(self):
        self._metrics: Dict[str, Any] = {
            "connections_created": 0,
            "connections_reused": 0,
            "connections_failed": 0,
            "connections_closed": 0,
            "health_checks_passed": 0,
            "health_checks_failed": 0,
            "acquire_wait_time_total": 0.0,
            "acquire_count": 0,
            "last_reset": time.time()
        }
        self._lock = asyncio.Lock()

    async def record_connection_created(self):
        """记录新连接创建"""
        async with self._lock:
            self._metrics["connections_created"] += 1

    async def record_connection_reused(self):
        """记录连接复用"""
        async with self._lock:
            self._metrics["connections_reused"] += 1

    async def record_connection_failed(self):
        """记录连接失败"""
        async with self._lock:
            self._metrics["connections_failed"] += 1

    async def record_connection_closed(self):
        """记录连接关闭"""
        async with self._lock:
            self._metrics["connections_closed"] += 1

    async def record_health_check(self, passed: bool):
        """记录健康检查结果"""
        async with self._lock:
            if passed:
                self._metrics["health_checks_passed"] += 1
            else:
                self._metrics["health_checks_failed"] += 1

    async def record_acquire_time(self, wait_time: float):
        """记录获取连接等待时间"""
        async with self._lock:
            self._metrics["acquire_wait_time_total"] += wait_time
            self._metrics["acquire_count"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        metrics = self._metrics.copy()
        if metrics["acquire_count"] > 0:
            metrics["avg_acquire_wait_time"] = (
                metrics["acquire_wait_time_total"] / metrics["acquire_count"]
            )
        else:
            metrics["avg_acquire_wait_time"] = 0.0

        # 计算连接复用率
        total_acquires = metrics["connections_created"] + metrics["connections_reused"]
        if total_acquires > 0:
            metrics["reuse_rate"] = metrics["connections_reused"] / total_acquires
        else:
            metrics["reuse_rate"] = 0.0

        return metrics

    async def reset(self):
        """重置指标"""
        async with self._lock:
            for key in self._metrics:
                if key == "last_reset":
                    self._metrics[key] = time.time()
                elif isinstance(self._metrics[key], float):
                    self._metrics[key] = 0.0
                else:
                    self._metrics[key] = 0


# 全局指标收集器实例
_pool_metrics = ConnectionPoolMetrics()


def get_pool_metrics() -> ConnectionPoolMetrics:
    """获取全局连接池指标收集器"""
    return _pool_metrics
