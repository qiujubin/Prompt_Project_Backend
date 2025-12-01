import json
import uuid
import websockets
import httpx
import urllib.request
import urllib.parse
import random
from typing import Dict, Any
from core.config import settings
from .base import AIGeneratorBase

class ComfyUIGenerator(AIGeneratorBase):
    """ComfyUI 本地生成器实现。"""

    def __init__(self):
        self.server_address = settings.COMFYUI_HOST
        self.client_id = str(uuid.uuid4())

    def _get_default_workflow(self, prompt: str, negative_prompt: str, seed: int, width: int = 512, height: int = 512, model_name: str = "v1-5-pruned-emaonly.ckpt"):
        """构建默认的 Text-to-Image 工作流。
        注意：这取决于 ComfyUI 中实际节点的 ID。这里使用默认安装的常见 ID。
        如果用户的 ComfyUI 节点 ID 不同，需要调整此模板。
        """
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 8,
                    "denoise": 1,
                    "dpmpp_2m_sde_gpu": "enable",
                    "karras": "disable",
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": seed,
                    "steps": 20
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": model_name
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": negative_prompt
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                }
            }
        }
        return workflow

    async def queue_prompt(self, workflow: Dict[str, Any], server_address: str = None):
        """向 ComfyUI 发送绘图请求。"""
        addr = server_address or self.server_address
        p = {"prompt": workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"http://{addr}/prompt", data=data)
            return resp.json()

    async def get_history(self, prompt_id: str, server_address: str = None):
        """获取任务历史结果。"""
        addr = server_address or self.server_address
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://{addr}/history/{prompt_id}")
            return resp.json()

    async def get_image(self, filename: str, subfolder: str, folder_type: str, server_address: str = None):
        """获取图片二进制数据。"""
        addr = server_address or self.server_address
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(params)
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://{addr}/view?{url_values}")
            return resp.content

    async def generate_image(self, prompt: str, negative_prompt: str = "", params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行生成逻辑。"""
        if params is None:
            params = {}
        
        seed = params.get("seed", random.randint(1, 1000000000))
        width = params.get("width", 512)
        height = params.get("height", 512)
        model_name = params.get("model_name", "v1-5-pruned-emaonly.ckpt")
        server_address = params.get("server_address")

        # 1. 构建工作流
        workflow = self._get_default_workflow(prompt, negative_prompt, seed, width, height, model_name)

        # 2. 连接 WebSocket 监听进度（简化版：暂不阻塞监听 WS，而是提交后轮询或返回 prompt_id）
        # 在生产环境中，应该使用 WS 监听 execution_success
        # 这里为了演示完整流程，我们先提交任务
        
        try:
            resp = await self.queue_prompt(workflow, server_address=server_address)
            prompt_id = resp.get("prompt_id")
            if not prompt_id:
                return {"status": "error", "msg": "Failed to queue prompt"}
            
            # 返回 prompt_id，让前端或后续逻辑轮询状态，或者在这里阻塞等待 WS
            # 为了简单起见，这里我们假设这是一个异步触发的操作
            return {
                "status": "queued",
                "prompt_id": prompt_id,
                "seed": seed,
                "backend": "comfyui"
            }
        except Exception as e:
            return {"status": "error", "msg": str(e)}

    async def check_status(self, prompt_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查任务状态并获取结果。"""
        if params is None:
            params = {}
        server_address = params.get("server_address")
        
        history = await self.get_history(prompt_id, server_address=server_address)
        if prompt_id in history:
            # 任务完成
            outputs = history[prompt_id]['outputs']
            # 假设 SaveImage 节点 ID 为 "9"
            images = []
            addr = server_address or self.server_address
            for node_id, node_output in outputs.items():
                if 'images' in node_output:
                    for image in node_output['images']:
                        # 构建查看图片的 URL
                        image_url = f"http://{addr}/view?filename={image['filename']}&subfolder={image['subfolder']}&type={image['type']}"
                        images.append(image_url)
            
            return {"status": "completed", "images": images}
        else:
            # 任务可能还在运行或排队
            return {"status": "processing"}
