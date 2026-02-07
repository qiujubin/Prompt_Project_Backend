"""
ComfyUI HTTP Client
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List
import httpx
import aiofiles
from pathlib import Path

from core.comfyui_config import get_comfyui_settings, get_storage_settings
from core.logger import get_logger

logger = get_logger(__name__)


class ComfyUIClient:
    """ComfyUI HTTP API 客户端"""

    def __init__(self):
        self.settings = get_comfyui_settings()
        self.storage_settings = get_storage_settings()
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.client = httpx.AsyncClient(
            base_url=self.settings.api_url,
            timeout=httpx.Timeout(self.settings.request_timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.client:
            await self.client.aclose()

    async def test_connection(self) -> Dict[str, Any]:
        """测试 ComfyUI 连接"""
        try:
            if not self.client:
                raise RuntimeError("Client not initialized")

            response = await self.client.get("/system_stats")

            if response.status_code == 200:
                stats = response.json()
                return {
                    "success": True,
                    "latency": response.elapsed.total_seconds() * 1000,
                    "system_stats": stats,
                    "version": stats.get("system", {}).get("version", "unknown")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

        except httpx.ConnectError:
            return {
                "success": False,
                "error": "Connection refused. Please check if ComfyUI is running."
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Connection timeout. Please check ComfyUI server status."
            }
        except Exception as e:
            logger.error(f"ComfyUI connection test failed: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        try:
            if not self.client:
                raise RuntimeError("Client not initialized")

            response = await self.client.get("/queue")
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise

    async def submit_prompt(self, workflow: Dict[str, Any], client_id: str = None) -> Dict[str, Any]:
        """提交生成任务"""
        try:
            if not self.client:
                raise RuntimeError("Client not initialized")

            if not client_id:
                client_id = str(uuid.uuid4())

            payload = {
                "prompt": workflow,
                "client_id": client_id
            }

            # 记录发送的工作流以便调试
            logger.debug(f"Submitting workflow: {json.dumps(workflow, indent=2)}")

            response = await self.client.post("/prompt", json=payload)
            response.raise_for_status()

            result = response.json()

            if "prompt_id" in result:
                logger.info(f"Submitted prompt with ID: {result['prompt_id']}")
                return {
                    "success": True,
                    "prompt_id": result["prompt_id"],
                    "client_id": client_id
                }
            else:
                return {
                    "success": False,
                    "error": "No prompt_id returned from ComfyUI"
                }

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Failed to submit prompt: {error_msg}")
            logger.error(f"Workflow that caused error: {json.dumps(workflow, indent=2)}")

            # 尝试解析 ComfyUI 的错误响应
            try:
                error_detail = e.response.json()
                logger.error(f"ComfyUI error detail: {json.dumps(error_detail, indent=2)}")
                return {
                    "success": False,
                    "error": error_msg,
                    "detail": error_detail
                }
            except:
                return {
                    "success": False,
                    "error": error_msg
                }
        except Exception as e:
            logger.error(f"Failed to submit prompt: {e}")
            logger.error(f"Workflow that caused error: {json.dumps(workflow, indent=2)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_prompt_status(self, prompt_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            if not self.client:
                raise RuntimeError("Client not initialized")

            response = await self.client.get(f"/history/{prompt_id}")
            response.raise_for_status()

            history = response.json()

            if prompt_id in history:
                return {
                    "success": True,
                    "status": "completed",
                    "history": history[prompt_id]
                }
            else:
                # Check if still in queue
                queue_response = await self.client.get("/queue")
                queue_data = queue_response.json()

                # Check running queue
                for item in queue_data.get("queue_running", []):
                    if item[1] == prompt_id:
                        return {
                            "success": True,
                            "status": "running",
                            "queue_position": 0
                        }

                # Check pending queue
                for i, item in enumerate(queue_data.get("queue_pending", [])):
                    if item[1] == prompt_id:
                        return {
                            "success": True,
                            "status": "pending",
                            "queue_position": i + 1
                        }

                return {
                    "success": False,
                    "error": "Prompt not found in queue or history"
                }

        except Exception as e:
            logger.error(f"Failed to get prompt status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def cancel_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """取消任务"""
        try:
            if not self.client:
                raise RuntimeError("Client not initialized")

            payload = {"delete": [prompt_id]}
            response = await self.client.post("/queue", json=payload)
            response.raise_for_status()

            logger.info(f"Cancelled prompt: {prompt_id}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to cancel prompt: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        try:
            if not self.client:
                raise RuntimeError("Client not initialized")

            response = await self.client.get("/object_info")
            response.raise_for_status()

            object_info = response.json()

            # Extract model information
            models = {}

            # Checkpoints
            if "CheckpointLoaderSimple" in object_info:
                checkpoint_info = object_info["CheckpointLoaderSimple"]
                if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                    ckpt_name = checkpoint_info["input"]["required"].get("ckpt_name")
                    if ckpt_name and isinstance(ckpt_name, list) and len(ckpt_name) > 0:
                        models["checkpoints"] = ckpt_name[0] if isinstance(ckpt_name[0], list) else []

            # VAE
            if "VAELoader" in object_info:
                vae_info = object_info["VAELoader"]
                if "input" in vae_info and "required" in vae_info["input"]:
                    vae_name = vae_info["input"]["required"].get("vae_name")
                    if vae_name and isinstance(vae_name, list) and len(vae_name) > 0:
                        models["vae"] = vae_name[0] if isinstance(vae_name[0], list) else []

            # Samplers
            if "KSampler" in object_info:
                sampler_info = object_info["KSampler"]
                if "input" in sampler_info and "required" in sampler_info["input"]:
                    sampler_name = sampler_info["input"]["required"].get("sampler_name")
                    scheduler = sampler_info["input"]["required"].get("scheduler")

                    if sampler_name and isinstance(sampler_name, list) and len(sampler_name) > 0:
                        models["samplers"] = sampler_name[0] if isinstance(sampler_name[0], list) else []

                    if scheduler and isinstance(scheduler, list) and len(scheduler) > 0:
                        models["schedulers"] = scheduler[0] if isinstance(scheduler[0], list) else []

            return {
                "success": True,
                "models": models
            }

        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def download_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """下载生成的图像"""
        try:
            if not self.client:
                raise RuntimeError("Client not initialized")

            params = {
                "filename": filename,
                "type": folder_type
            }

            if subfolder:
                params["subfolder"] = subfolder

            response = await self.client.get("/view", params=params)
            response.raise_for_status()

            return response.content

        except Exception as e:
            logger.error(f"Failed to download image {filename}: {e}")
            return None
