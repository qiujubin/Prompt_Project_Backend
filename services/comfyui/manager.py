"""
ComfyUI Manager - High-level interface for ComfyUI integration
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from .client import ComfyUIClient
from .websocket import ComfyUIWebSocketHandler
from core.comfyui_config import get_comfyui_settings, get_workflow_settings, get_storage_settings
from core.logger import get_logger

logger = get_logger(__name__)


class ComfyUIManager:
    """ComfyUI 管理器 - 统一的 ComfyUI 接口"""

    def __init__(self):
        self.settings = get_comfyui_settings()
        self.workflow_settings = get_workflow_settings()
        self.storage_settings = get_storage_settings()

        self.client: Optional[ComfyUIClient] = None
        self.websocket: Optional[ComfyUIWebSocketHandler] = None

        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_callbacks: Dict[str, List[Callable]] = {}

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()

    async def initialize(self):
        """初始化管理器"""
        try:
            # Initialize HTTP client
            self.client = ComfyUIClient()
            await self.client.__aenter__()

            # Initialize WebSocket handler
            self.websocket = ComfyUIWebSocketHandler()

            # Set up WebSocket event handlers
            self._setup_websocket_handlers()

            logger.info("ComfyUI Manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize ComfyUI Manager: {e}")
            raise

    async def cleanup(self):
        """清理资源"""
        try:
            if self.websocket:
                await self.websocket.disconnect()

            if self.client:
                await self.client.__aexit__(None, None, None)

            logger.info("ComfyUI Manager cleaned up")

        except Exception as e:
            logger.error(f"Error during ComfyUI Manager cleanup: {e}")

    def _setup_websocket_handlers(self):
        """设置 WebSocket 事件处理器"""
        if not self.websocket:
            return

        self.websocket.on('executing', self._handle_executing)
        self.websocket.on('executed', self._handle_executed)
        self.websocket.on('execution_error', self._handle_execution_error)
        self.websocket.on('progress', self._handle_progress)
        self.websocket.on('status', self._handle_status)

    async def test_connection(self) -> Dict[str, Any]:
        """测试 ComfyUI 连接"""
        if not self.client:
            return {"success": False, "error": "Client not initialized"}

        # Test HTTP connection
        http_result = await self.client.test_connection()

        if not http_result["success"]:
            return http_result

        # Test WebSocket connection
        try:
            ws_connected = await self.websocket.connect()
            if ws_connected:
                await self.websocket.disconnect()
                return {
                    "success": True,
                    "latency": http_result.get("latency"),
                    "version": http_result.get("version"),
                    "websocket": True
                }
            else:
                return {
                    "success": False,
                    "error": "WebSocket connection failed"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"WebSocket test failed: {str(e)}"
            }

    async def connect_websocket(self) -> bool:
        """连接 WebSocket"""
        if not self.websocket:
            return False

        return await self.websocket.connect()

    async def disconnect_websocket(self):
        """断开 WebSocket 连接"""
        if self.websocket:
            await self.websocket.disconnect()

    async def generate_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成图像"""
        try:
            if not self.client or not self.websocket:
                return {"success": False, "error": "Manager not initialized"}

            # Ensure WebSocket is connected
            if not self.websocket.connected:
                connected = await self.websocket.connect()
                if not connected:
                    return {"success": False, "error": "Failed to connect WebSocket"}

            # Create workflow from parameters
            workflow = await self._create_workflow(params)

            # Submit prompt
            result = await self.client.submit_prompt(workflow, self.websocket.get_client_id())

            if result["success"]:
                prompt_id = result["prompt_id"]

                # Track the task
                self.active_tasks[prompt_id] = {
                    "status": "queued",
                    "params": params,
                    "created_at": asyncio.get_event_loop().time(),
                    "client_id": result["client_id"]
                }

                logger.info(f"Started image generation task: {prompt_id}")

                return {
                    "success": True,
                    "task_id": prompt_id,
                    "client_id": result["client_id"]
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_generation(self, task_id: str) -> Dict[str, Any]:
        """取消生成任务"""
        try:
            if not self.client:
                return {"success": False, "error": "Client not initialized"}

            result = await self.client.cancel_prompt(task_id)

            if result["success"] and task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "cancelled"

            return result

        except Exception as e:
            logger.error(f"Failed to cancel generation: {e}")
            return {"success": False, "error": str(e)}

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id].copy()

                # Get latest status from ComfyUI if still active
                if task_info["status"] in ["queued", "running"]:
                    if self.client:
                        status_result = await self.client.get_prompt_status(task_id)
                        if status_result["success"]:
                            task_info.update(status_result)

                return {"success": True, "task": task_info}
            else:
                return {"success": False, "error": "Task not found"}

        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return {"success": False, "error": str(e)}

    async def get_models(self) -> Dict[str, Any]:
        """获取可用模型"""
        if not self.client:
            return {"success": False, "error": "Client not initialized"}

        return await self.client.get_models()

    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        if not self.client:
            return {"success": False, "error": "Client not initialized"}

        return await self.client.get_queue_status()

    def add_task_callback(self, task_id: str, callback: Callable):
        """添加任务回调"""
        if task_id not in self.task_callbacks:
            self.task_callbacks[task_id] = []
        self.task_callbacks[task_id].append(callback)

    def remove_task_callback(self, task_id: str, callback: Optional[Callable] = None):
        """移除任务回调"""
        if task_id in self.task_callbacks:
            if callback:
                try:
                    self.task_callbacks[task_id].remove(callback)
                except ValueError:
                    pass
            else:
                self.task_callbacks[task_id].clear()

    async def _create_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """根据参数创建工作流"""
        # This is a simplified workflow creation
        # In a real implementation, you would load and customize workflow templates

        workflow = {
            "1": {
                "inputs": {
                    "ckpt_name": params.get("model", "v1-5-pruned-emaonly.ckpt")
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {
                    "text": params.get("positive_prompt", ""),
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "3": {
                "inputs": {
                    "text": params.get("negative_prompt", ""),
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "4": {
                "inputs": {
                    "width": params.get("width", self.workflow_settings.default_width),
                    "height": params.get("height", self.workflow_settings.default_height),
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "5": {
                "inputs": {
                    "seed": params.get("seed", -1),
                    "steps": params.get("steps", self.workflow_settings.default_steps),
                    "cfg": params.get("cfg", self.workflow_settings.default_cfg),
                    "sampler_name": params.get("sampler", self.workflow_settings.default_sampler),
                    "scheduler": params.get("scheduler", self.workflow_settings.default_scheduler),
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "model": ["1", 0]
                },
                "class_type": "KSampler"
            },
            "6": {
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode"
            },
            "7": {
                "inputs": {
                    "filename_prefix": f"comfyui_output_{uuid.uuid4().hex[:8]}",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage"
            }
        }

        return workflow

    # WebSocket event handlers
    async def _handle_executing(self, data: Dict[str, Any]):
        """处理执行开始事件"""
        prompt_id = data.get("prompt_id")
        if prompt_id and prompt_id in self.active_tasks:
            self.active_tasks[prompt_id]["status"] = "running"
            self.active_tasks[prompt_id]["current_node"] = data.get("node")

            # Notify callbacks
            await self._notify_callbacks(prompt_id, "executing", data)

    async def _handle_executed(self, data: Dict[str, Any]):
        """处理执行完成事件"""
        prompt_id = data.get("prompt_id")
        if prompt_id and prompt_id in self.active_tasks:
            self.active_tasks[prompt_id]["status"] = "completed"
            self.active_tasks[prompt_id]["output"] = data.get("output", {})

            # Notify callbacks
            await self._notify_callbacks(prompt_id, "completed", data)

    async def _handle_execution_error(self, data: Dict[str, Any]):
        """处理执行错误事件"""
        prompt_id = data.get("prompt_id")
        if prompt_id and prompt_id in self.active_tasks:
            self.active_tasks[prompt_id]["status"] = "failed"
            self.active_tasks[prompt_id]["error"] = data

            # Notify callbacks
            await self._notify_callbacks(prompt_id, "failed", data)

    async def _handle_progress(self, data: Dict[str, Any]):
        """处理进度更新事件"""
        prompt_id = data.get("prompt_id")
        if prompt_id and prompt_id in self.active_tasks:
            self.active_tasks[prompt_id]["progress"] = {
                "current": data.get("value", 0),
                "total": data.get("max", 100),
                "percentage": (data.get("value", 0) / max(data.get("max", 1), 1)) * 100
            }

            # Notify callbacks
            await self._notify_callbacks(prompt_id, "progress", data)

    async def _handle_status(self, data: Dict[str, Any]):
        """处理状态更新事件"""
        # Handle general status updates
        logger.debug(f"ComfyUI status update: {data}")

    async def _notify_callbacks(self, task_id: str, event: str, data: Dict[str, Any]):
        """通知任务回调"""
        if task_id in self.task_callbacks:
            for callback in self.task_callbacks[task_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event, data)
                    else:
                        callback(event, data)
                except Exception as e:
                    logger.error(f"Error in task callback: {e}")

    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃任务列表"""
        return self.active_tasks.copy()

    def cleanup_completed_tasks(self, max_age: int = 3600):
        """清理已完成的任务"""
        current_time = asyncio.get_event_loop().time()
        to_remove = []

        for task_id, task_info in self.active_tasks.items():
            if (task_info["status"] in ["completed", "failed", "cancelled"] and
                current_time - task_info["created_at"] > max_age):
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.active_tasks[task_id]
            if task_id in self.task_callbacks:
                del self.task_callbacks[task_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} completed tasks")
