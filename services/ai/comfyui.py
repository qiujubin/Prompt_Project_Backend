import json
import uuid
import websockets
import httpx
import urllib.request
import urllib.parse
import random
from typing import Dict, Any, Optional
from core.config import settings
from .base import AIGeneratorBase
from services.comfyui.retry import (
    RetryHandler, RetryConfig, with_retry,
    get_circuit_breaker, classify_error, get_error_suggestion
)
from services.comfyui.connection_pool import ConnectionPoolManager
from core.comfyui_config import get_comfyui_settings
from core.logger import get_logger

logger = get_logger(__name__)


class ComfyUIGenerator(AIGeneratorBase):
    """ComfyUI 本地生成器实现。

    支持功能：
    - 图像生成任务提交
    - 任务状态查询
    - 任务取消
    - 自定义生成参数（CFG、步数、采样器、调度器等）
    - 连接池管理
    - 错误重试机制

    Requirements: 4.1, 4.2, 4.3
    """

    def __init__(self):
        self.server_address = settings.COMFYUI_HOST
        self.client_id = str(uuid.uuid4())
        self.comfyui_settings = get_comfyui_settings()
        self.retry_handler = RetryHandler(RetryConfig(
            max_attempts=self.comfyui_settings.max_retry_attempts,
            initial_delay=self.comfyui_settings.retry_delay,
            max_delay=self.comfyui_settings.retry_max_delay,
            exponential_base=self.comfyui_settings.retry_exponential_base
        ))

    def _get_default_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int = 512,
        height: int = 512,
        model_name: str = "v1-5-pruned-emaonly.ckpt",
        cfg: float = 7.0,
        steps: int = 20,
        sampler_name: str = "euler",
        scheduler: str = "normal",
        denoise: float = 1.0
    ) -> Dict[str, Any]:
        """构建默认的 Text-to-Image 工作流。

        Args:
            prompt: 正面提示词
            negative_prompt: 负面提示词
            seed: 随机种子 (-1 表示随机)
            width: 图像宽度
            height: 图像高度
            model_name: 模型名称
            cfg: CFG Scale (引导强度)
            steps: 采样步数
            sampler_name: 采样器名称
            scheduler: 调度器名称
            denoise: 去噪强度

        Returns:
            ComfyUI 工作流字典

        Requirements: 4.2 - 生成任务包含所有必要参数
        """
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": cfg,
                    "denoise": denoise,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "seed": seed,
                    "steps": steps
                },
                "_meta": {
                    "title": "KSampler"
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": model_name
                },
                "_meta": {
                    "title": "Load Checkpoint"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                },
                "_meta": {
                    "title": "Empty Latent Image"
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt
                },
                "_meta": {
                    "title": "CLIP Text Encode (Positive)"
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": negative_prompt
                },
                "_meta": {
                    "title": "CLIP Text Encode (Negative)"
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "_meta": {
                    "title": "VAE Decode"
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": f"ComfyUI_{uuid.uuid4().hex[:8]}",
                    "images": ["8", 0]
                },
                "_meta": {
                    "title": "Save Image"
                }
            }
        }
        return workflow

    async def queue_prompt(self, workflow: Dict[str, Any], server_address: str = None) -> Dict[str, Any]:
        """向 ComfyUI 发送绘图请求。

        Args:
            workflow: ComfyUI 工作流配置
            server_address: 可选的自定义服务器地址

        Returns:
            包含 prompt_id 的响应字典

        Requirements: 4.1 - 创建并发送生成任务
        """
        addr = server_address or self.server_address

        # 获取熔断器
        circuit_breaker = await get_circuit_breaker(f"comfyui_{addr}")

        async def _do_queue():
            p = {"prompt": workflow, "client_id": self.client_id}
            data = json.dumps(p).encode('utf-8')

            # 使用连接池
            pool_manager = await ConnectionPoolManager.get_instance()
            http_pool = await pool_manager.get_http_pool(addr)
            client = await http_pool.get_client()

            resp = await client.post("/prompt", data=data)
            resp.raise_for_status()
            return resp.json()

        return await self.retry_handler.execute_with_retry(
            _do_queue,
            circuit_breaker=circuit_breaker
        )

    async def get_history(self, prompt_id: str, server_address: str = None) -> Dict[str, Any]:
        """获取任务历史结果。

        Args:
            prompt_id: 任务 ID
            server_address: 可选的自定义服务器地址

        Returns:
            任务历史记录
        """
        addr = server_address or self.server_address
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"http://{addr}/history/{prompt_id}")
            return resp.json()

    async def get_queue(self, server_address: str = None) -> Dict[str, Any]:
        """获取当前队列状态。

        Args:
            server_address: 可选的自定义服务器地址

        Returns:
            队列状态信息
        """
        addr = server_address or self.server_address
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"http://{addr}/queue")
            return resp.json()

    async def cancel_task(self, prompt_id: str, server_address: str = None) -> Dict[str, Any]:
        """取消正在进行的生成任务。

        Args:
            prompt_id: 要取消的任务 ID
            server_address: 可选的自定义服务器地址

        Returns:
            取消操作结果

        Requirements: 4.6 - 支持取消正在进行的生成任务
        """
        addr = server_address or self.server_address
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 首先尝试从队列中删除
                delete_data = json.dumps({"delete": [prompt_id]}).encode('utf-8')
                resp = await client.post(f"http://{addr}/queue", data=delete_data)

                # 然后尝试中断当前执行
                interrupt_resp = await client.post(f"http://{addr}/interrupt")

                return {
                    "status": "cancelled",
                    "prompt_id": prompt_id,
                    "message": "Task cancelled successfully"
                }
        except Exception as e:
            return {
                "status": "error",
                "prompt_id": prompt_id,
                "message": f"Failed to cancel task: {str(e)}"
            }

    async def get_image(self, filename: str, subfolder: str, folder_type: str, server_address: str = None) -> bytes:
        """获取图片二进制数据。

        Args:
            filename: 文件名
            subfolder: 子文件夹
            folder_type: 文件夹类型
            server_address: 可选的自定义服务器地址

        Returns:
            图片二进制数据
        """
        addr = server_address or self.server_address
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(params)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"http://{addr}/view?{url_values}")
            return resp.content

    async def generate_image(self, prompt: str, negative_prompt: str = "", params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行生成逻辑。

        Args:
            prompt: 正面提示词
            negative_prompt: 负面提示词
            params: 生成参数字典，支持以下参数：
                - seed: 随机种子 (-1 表示随机)
                - width: 图像宽度
                - height: 图像高度
                - model_name: 模型名称
                - cfg: CFG Scale
                - steps: 采样步数
                - sampler: 采样器名称
                - scheduler: 调度器名称
                - server_address: 自定义 ComfyUI 地址

        Returns:
            包含任务状态和 prompt_id 的字典

        Requirements: 4.1, 4.2 - 创建包含所有参数的生成任务
        """
        if params is None:
            params = {}

        # 解析生成参数
        seed = params.get("seed", -1)
        if seed == -1:
            seed = random.randint(1, 2147483647)

        width = params.get("width", 512)
        height = params.get("height", 512)
        model_name = params.get("model_name", "v1-5-pruned-emaonly.ckpt")
        cfg = params.get("cfg", params.get("cfg_scale", 7.0))
        steps = params.get("steps", 20)
        sampler_name = params.get("sampler", params.get("sampler_name", "euler"))
        scheduler = params.get("scheduler", "normal")
        server_address = params.get("server_address")

        # 构建工作流
        workflow = self._get_default_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            width=width,
            height=height,
            model_name=model_name,
            cfg=cfg,
            steps=steps,
            sampler_name=sampler_name,
            scheduler=scheduler
        )

        try:
            resp = await self.queue_prompt(workflow, server_address=server_address)
            prompt_id = resp.get("prompt_id")

            if not prompt_id:
                error_msg = resp.get("error", {}).get("message", "Failed to queue prompt")
                return {"status": "error", "msg": error_msg}

            return {
                "status": "queued",
                "prompt_id": prompt_id,
                "seed": seed,
                "backend": "comfyui",
                "params": {
                    "width": width,
                    "height": height,
                    "cfg": cfg,
                    "steps": steps,
                    "sampler": sampler_name,
                    "scheduler": scheduler,
                    "model": model_name
                }
            }
        except httpx.ConnectError:
            return {"status": "error", "msg": "无法连接到 ComfyUI 服务。请检查 ComfyUI 是否正在运行，以及地址和端口是否正确。", "error_code": "CONNECTION_REFUSED"}
        except httpx.TimeoutException:
            return {"status": "error", "msg": "连接 ComfyUI 超时。请检查服务器状态和网络连接。", "error_code": "CONNECTION_TIMEOUT"}
        except Exception as e:
            error_msg = str(e)
            error_code = "UNKNOWN_ERROR"

            # 检测特定错误类型
            if "out of memory" in error_msg.lower() or "cuda" in error_msg.lower():
                error_code = "OUT_OF_MEMORY"
                error_msg = "GPU 内存不足。请尝试降低图像分辨率或关闭其他占用 GPU 的程序。"
            elif "model" in error_msg.lower() and ("not found" in error_msg.lower() or "找不到" in error_msg):
                error_code = "MODEL_NOT_FOUND"
                error_msg = f"找不到指定的模型文件。请检查模型是否存在于 ComfyUI 的 models 目录。原始错误: {str(e)}"
            elif "node" in error_msg.lower() or "plugin" in error_msg.lower():
                error_code = "PLUGIN_MISSING"
                error_msg = f"缺少必要的 ComfyUI 插件或节点。请使用 ComfyUI Manager 安装缺失的插件。原始错误: {str(e)}"

            return {"status": "error", "msg": error_msg, "error_code": error_code}

    async def check_status(self, prompt_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查任务状态并获取结果。

        Args:
            prompt_id: 任务 ID
            params: 可选参数，包含 server_address

        Returns:
            任务状态和结果

        Requirements: 4.4 - 显示生成进度和状态更新
        """
        if params is None:
            params = {}
        server_address = params.get("server_address")
        addr = server_address or self.server_address

        try:
            # 首先检查历史记录（已完成的任务）
            history = await self.get_history(prompt_id, server_address=server_address)

            if prompt_id in history:
                # 任务完成
                task_data = history[prompt_id]
                outputs = task_data.get('outputs', {})

                # 检查是否有错误
                if task_data.get('status', {}).get('status_str') == 'error':
                    return {
                        "status": "failed",
                        "error": task_data.get('status', {}).get('messages', ['Unknown error'])[0]
                    }

                # 提取图像
                images = []
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        for image in node_output['images']:
                            # 构建查看图片的 URL
                            image_url = f"http://{addr}/view?filename={image['filename']}&subfolder={image.get('subfolder', '')}&type={image.get('type', 'output')}"
                            images.append(image_url)

                return {
                    "status": "completed",
                    "images": images,
                    "prompt_id": prompt_id
                }

            # 检查队列状态
            queue_data = await self.get_queue(server_address=server_address)

            # 检查是否在运行队列中
            running_queue = queue_data.get("queue_running", [])
            for item in running_queue:
                if len(item) > 1 and item[1] == prompt_id:
                    return {
                        "status": "generating",
                        "prompt_id": prompt_id,
                        "queue_position": 0,
                        "message": "正在生成中..."
                    }

            # 检查是否在等待队列中
            pending_queue = queue_data.get("queue_pending", [])
            for i, item in enumerate(pending_queue):
                if len(item) > 1 and item[1] == prompt_id:
                    return {
                        "status": "processing",
                        "prompt_id": prompt_id,
                        "queue_position": i + 1,
                        "message": f"排队中，前面还有 {i} 个任务"
                    }

            # 任务不在队列中也不在历史中
            return {
                "status": "processing",
                "prompt_id": prompt_id,
                "message": "任务处理中..."
            }

        except httpx.ConnectError:
            return {
                "status": "error",
                "error": "无法连接到 ComfyUI 服务。请检查 ComfyUI 是否正在运行。",
                "error_code": "CONNECTION_REFUSED"
            }
        except httpx.TimeoutException:
            return {
                "status": "error",
                "error": "连接 ComfyUI 超时。请检查服务器状态。",
                "error_code": "CONNECTION_TIMEOUT"
            }
        except Exception as e:
            error_msg = str(e)
            error_code = "UNKNOWN_ERROR"

            # 检测特定错误类型
            if "out of memory" in error_msg.lower() or "cuda" in error_msg.lower():
                error_code = "OUT_OF_MEMORY"
                error_msg = "GPU 内存不足。请尝试降低图像分辨率。"

            return {
                "status": "error",
                "error": error_msg,
                "error_code": error_code
            }
