"""
ComfyUI WebSocket Handler
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, Callable, Set
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from core.comfyui_config import get_comfyui_settings
from core.logger import get_logger

logger = get_logger(__name__)


class ComfyUIWebSocketHandler:
    """ComfyUI WebSocket 处理器"""

    def __init__(self):
        self.settings = get_comfyui_settings()
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.client_id: str = str(uuid.uuid4())
        self.is_connected: bool = False
        self.event_handlers: Dict[str, Set[Callable]] = {}
        self._reconnect_task: Optional[asyncio.Task] = None
        self._listen_task: Optional[asyncio.Task] = None

    def on(self, event: str, handler: Callable):
        """注册事件处理器"""
        if event not in self.event_handlers:
            self.event_handlers[event] = set()
        self.event_handlers[event].add(handler)

    def off(self, event: str, handler: Optional[Callable] = None):
        """移除事件处理器"""
        if event in self.event_handlers:
            if handler:
                self.event_handlers[event].discard(handler)
            else:
                self.event_handlers[event].clear()

    def emit(self, event: str, data: Any):
        """触发事件"""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event}: {e}")

    async def connect(self) -> bool:
        """连接到 ComfyUI WebSocket"""
        try:
            logger.info(f"Connecting to ComfyUI WebSocket: {self.settings.websocket_url}")

            self.websocket = await websockets.connect(
                f"{self.settings.websocket_url}?clientId={self.client_id}",
                timeout=self.settings.connect_timeout
            )

            self.is_connected = True
            logger.info(f"Connected to ComfyUI WebSocket with client ID: {self.client_id}")

            # Start listening for messages
            self._listen_task = asyncio.create_task(self._listen_messages())

            self.emit('connected', {'client_id': self.client_id})
            return True

        except Exception as e:
            logger.error(f"Failed to connect to ComfyUI WebSocket: {e}")
            self.is_connected = False
            self.emit('error', {'error': str(e)})
            return False

    async def disconnect(self):
        """断开 WebSocket 连接"""
        self.is_connected = False

        # Cancel tasks
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        # Close websocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        logger.info("Disconnected from ComfyUI WebSocket")
        self.emit('disconnected', {})

    async def send_message(self, message: Dict[str, Any]):
        """发送消息"""
        if not self.is_connected or not self.websocket:
            raise RuntimeError("WebSocket is not connected")

        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise

    async def _listen_messages(self):
        """监听 WebSocket 消息"""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    await self._handle_message(message)

                except ConnectionClosed:
                    logger.warning("ComfyUI WebSocket connection closed")
                    self.is_connected = False
                    self.emit('disconnected', {})

                    # Attempt to reconnect
                    if not self._reconnect_task or self._reconnect_task.done():
                        self._reconnect_task = asyncio.create_task(self._reconnect())
                    break

                except WebSocketException as e:
                    logger.error(f"WebSocket error: {e}")
                    self.emit('error', {'error': str(e)})
                    break

        except asyncio.CancelledError:
            logger.info("WebSocket message listener cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in WebSocket listener: {e}")
            self.emit('error', {'error': str(e)})

    async def _handle_message(self, message: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type', 'unknown')

            logger.debug(f"Received WebSocket message: {message_type}")

            # Handle different message types
            if message_type == 'status':
                self.emit('status', data.get('data', {}))

            elif message_type == 'progress':
                self.emit('progress', data.get('data', {}))

            elif message_type == 'executing':
                self.emit('executing', data.get('data', {}))

            elif message_type == 'executed':
                self.emit('executed', data.get('data', {}))

            elif message_type == 'execution_start':
                self.emit('execution_start', data.get('data', {}))

            elif message_type == 'execution_error':
                self.emit('execution_error', data.get('data', {}))

            elif message_type == 'execution_cached':
                self.emit('execution_cached', data.get('data', {}))

            else:
                # Generic message handler
                self.emit('message', data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
            self.emit('error', {'error': f'Invalid JSON message: {str(e)}'})
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            self.emit('error', {'error': str(e)})

    async def _reconnect(self):
        """自动重连"""
        max_attempts = self.settings.max_retry_attempts
        attempt = 0

        while attempt < max_attempts and not self.is_connected:
            attempt += 1
            delay = self.settings.retry_delay * (2 ** (attempt - 1))  # Exponential backoff

            logger.info(f"Attempting to reconnect to ComfyUI WebSocket (attempt {attempt}/{max_attempts})")

            await asyncio.sleep(delay)

            if await self.connect():
                logger.info("Successfully reconnected to ComfyUI WebSocket")
                self.emit('reconnected', {'attempts': attempt})
                return

        logger.error(f"Failed to reconnect to ComfyUI WebSocket after {max_attempts} attempts")
        self.emit('reconnect_failed', {'attempts': attempt})

    @property
    def connected(self) -> bool:
        """检查连接状态"""
        return self.is_connected and self.websocket is not None

    def get_client_id(self) -> str:
        """获取客户端 ID"""
        return self.client_id
