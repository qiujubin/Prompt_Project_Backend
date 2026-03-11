import httpx
import json
import base64
from typing import Dict, Any, Optional
from core.config import settings
from .base import AIGeneratorBase
from core.logger import get_logger

logger = get_logger(__name__)

class ExternalAIGenerator(AIGeneratorBase):
    """外部 AI API 生成器，支持多种 AI 服务提供商。"""

    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.api_url = settings.AI_API_URL

    async def generate_image(self, prompt: str, negative_prompt: str = "", params: Dict[str, Any] = None) -> Dict[str, Any]:
        if params is None:
            params = {}

        api_key = params.get("api_key") or self.api_key
        api_url = params.get("api_url") or self.api_url
        provider = params.get("provider", "openai")  # 默认使用 OpenAI

        # 验证 API Key
        if not api_key or api_key.strip() == "":
            return {"status": "error", "msg": "API Key 未配置"}

        # 验证 API URL
        if not api_url or api_url.strip() == "":
            # 使用默认 URL 如果没有提供
            if provider.lower() in ["openai", "openai-compatible"]:
                api_url = "https://api.openai.com/v1"
            elif provider.lower() in ["tongyi", "qwen", "aliyun"]:
                api_url = "https://dashscope.aliyuncs.com/api/v1"
            elif provider.lower() in ["baidu", "wenxin", "ernie"]:
                api_url = "https://aip.baidubce.com"
            elif provider.lower() in ["tencent", "hunyuan"]:
                api_url = "https://hunyuan.tencentcloudapi.com"
            else:
                return {"status": "error", "msg": "API URL 未配置"}

        try:
            # 根据不同的提供商调用相应的方法
            if provider.lower() in ["openai", "openai-compatible"]:
                return await self._generate_openai_style(prompt, negative_prompt, api_key, api_url, params)
            elif provider.lower() in ["tongyi", "qwen", "aliyun"]:
                return await self._generate_tongyi(prompt, negative_prompt, api_key, api_url, params)
            elif provider.lower() in ["baidu", "wenxin", "ernie"]:
                return await self._generate_baidu(prompt, negative_prompt, api_key, api_url, params)
            elif provider.lower() in ["tencent", "hunyuan"]:
                return await self._generate_tencent(prompt, negative_prompt, api_key, api_url, params)
            else:
                # 默认尝试 OpenAI 兼容格式
                return await self._generate_openai_style(prompt, negative_prompt, api_key, api_url, params)

        except Exception as e:
            logger.error(f"External API generation failed: {e}")
            return {"status": "error", "msg": str(e)}

    async def _generate_openai_style(self, prompt: str, negative_prompt: str, api_key: str, api_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI DALL-E 或兼容格式的 API 调用"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 构建完整提示词
        full_prompt = prompt
        if negative_prompt:
            full_prompt += f" (避免: {negative_prompt})"

        # 获取图像尺寸
        width = params.get("width", 1024)
        height = params.get("height", 1024)
        size = f"{width}x{height}"

        # 支持的尺寸映射
        size_mapping = {
            "512x512": "512x512",
            "1024x1024": "1024x1024",
            "1024x1792": "1024x1792",
            "1792x1024": "1792x1024"
        }

        # 选择最接近的支持尺寸
        if size not in size_mapping:
            if width >= height:
                size = "1024x1024" if width <= 1024 else "1792x1024"
            else:
                size = "1024x1024" if height <= 1024 else "1024x1792"

        data = {
            "model": params.get("model_name", "dall-e-3"),
            "prompt": full_prompt,
            "n": 1,
            "size": size,
            "quality": "standard",
            "response_format": "url"
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{api_url}/images/generations", json=data, headers=headers)

            if resp.status_code != 200:
                error_text = resp.text
                return {"status": "error", "msg": f"OpenAI API Error ({resp.status_code}): {error_text}"}

            result = resp.json()
            if "data" not in result or not result["data"]:
                return {"status": "error", "msg": "API 返回数据格式错误"}

            image_url = result["data"][0]["url"]

            return {
                "status": "completed",
                "images": [image_url],
                "image_url": image_url,
                "backend": "external_api",
                "provider": "openai",
                "seed": params.get("seed", -1)
            }

    async def _generate_tongyi(self, prompt: str, negative_prompt: str, api_key: str, api_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """阿里云通义千问图像生成 API 调用

        支持两种模型系列：
        1. 新 API（同步）: qwen-image-2.0 系列、qwen-image-plus、qwen-image-max、z-image-turbo
        2. 旧 API（异步）: qwen-image（标准版）
        """
        model_name = params.get("model_name", "qwen-image-2.0")

        # 判断使用哪种 API
        # 新 API: qwen-image-2.0 系列（包括 qwen-image-2.0, qwen-image-2.0-pro）, qwen-image-plus, qwen-image-max, z-image-turbo
        # 旧 API: qwen-image（标准版，异步）
        is_new_api = (
            model_name.startswith("qwen-image-2.0") or
            model_name.startswith("qwen-image-max") or
            model_name == "qwen-image-plus" or
            model_name.lower() == "z-image-turbo"
        )

        if is_new_api:
            # 新 API：同步接口，使用 multimodal-generation
            return await self._generate_tongyi_new_api(prompt, negative_prompt, api_key, api_url, params)
        else:
            # 旧 API：异步接口，使用 text2image
            return await self._generate_tongyi_legacy_api(prompt, negative_prompt, api_key, api_url, params)

    async def _generate_tongyi_new_api(self, prompt: str, negative_prompt: str, api_key: str, api_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """通义千问新 API - 同步接口

        支持的模型：
        - qwen-image-2.0 系列（qwen-image-2.0, qwen-image-2.0-pro 等）
        - qwen-image-plus
        - qwen-image-max
        - z-image-turbo（参数受限，不支持 n 和 watermark）
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        model_name = params.get("model_name", "qwen-image-2.0")

        # 新 API 使用 messages 格式
        data = {
            "model": model_name,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": prompt}
                        ]
                    }
                ]
            },
            "parameters": {
                "size": f"{params.get('width', 1024)}*{params.get('height', 1024)}",
                "prompt_extend": params.get("prompt_extend", True)
            }
        }

        # z-image-turbo 只支持基础参数，不支持 n 和 watermark
        # qwen-image-2.0 系列和 qwen-image-plus 支持完整参数
        if model_name.lower() != "z-image-turbo":
            data["parameters"]["n"] = params.get("n", 1)
            data["parameters"]["watermark"] = params.get("watermark", False)

        # 添加负面提示词
        if negative_prompt:
            data["parameters"]["negative_prompt"] = negative_prompt

        # 添加随机种子
        if params.get("seed") and params.get("seed", -1) != -1:
            data["parameters"]["seed"] = params.get("seed")

        # 记录请求数据用于调试
        logger.info(f"Tongyi new API request for model {model_name}: {json.dumps(data, ensure_ascii=False)}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{api_url}/services/aigc/multimodal-generation/generation",
                json=data,
                headers=headers
            )

            if resp.status_code != 200:
                error_text = resp.text
                logger.error(f"Tongyi new API error for model {model_name}: {error_text}")
                return {"status": "error", "msg": f"通义千问 API Error ({resp.status_code}): {error_text}"}

            result = resp.json()

            # 新 API 直接返回结果
            if "output" in result and "choices" in result["output"]:
                choices = result["output"]["choices"]
                if choices and len(choices) > 0:
                    content = choices[0].get("message", {}).get("content", [])
                    if content and len(content) > 0:
                        image_url = content[0].get("image")
                        if image_url:
                            return {
                                "status": "completed",
                                "images": [image_url],
                                "image_url": image_url,
                                "backend": "external_api",
                                "provider": "tongyi",
                                "seed": params.get("seed", -1)
                            }

            return {"status": "error", "msg": "通义千问 API 返回数据格式错误"}

    async def _generate_tongyi_legacy_api(self, prompt: str, negative_prompt: str, api_key: str, api_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """通义千问旧 API（qwen-image-plus/qwen-image）- 异步接口"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"  # 启用异步模式
        }

        data = {
            "model": params.get("model_name", "qwen-image-plus"),
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "size": f"{params.get('width', 1024)}*{params.get('height', 1024)}",
                "n": 1,
                "prompt_extend": params.get("prompt_extend", True),
                "watermark": params.get("watermark", False)
            }
        }

        # 添加负面提示词
        if negative_prompt:
            data["parameters"]["negative_prompt"] = negative_prompt

        # 添加随机种子
        if params.get("seed") and params.get("seed", -1) != -1:
            data["parameters"]["seed"] = params.get("seed")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{api_url}/services/aigc/text2image/image-synthesis",
                json=data,
                headers=headers
            )

            if resp.status_code != 200:
                error_text = resp.text
                return {"status": "error", "msg": f"通义千问 API Error ({resp.status_code}): {error_text}"}

            result = resp.json()

            # 检查是否是异步任务
            if result.get("output", {}).get("task_status") == "PENDING":
                task_id = result.get("output", {}).get("task_id")
                return {
                    "status": "queued",
                    "prompt_id": task_id,
                    "backend": "external_api",
                    "provider": "tongyi"
                }

            # 同步返回结果（某些情况下可能直接返回）
            if "output" in result and "results" in result["output"]:
                image_url = result["output"]["results"][0]["url"]
                return {
                    "status": "completed",
                    "images": [image_url],
                    "image_url": image_url,
                    "backend": "external_api",
                    "provider": "tongyi",
                    "seed": params.get("seed", -1)
                }

            return {"status": "error", "msg": "通义千问 API 返回数据格式错误"}

    async def _generate_baidu(self, prompt: str, negative_prompt: str, api_key: str, api_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """百度文心一言图像生成 API 调用"""
        # 百度 API 需要先获取 access_token
        access_token = await self._get_baidu_access_token(api_key, params.get("secret_key", ""))
        if not access_token:
            return {"status": "error", "msg": "获取百度 access_token 失败"}

        headers = {
            "Content-Type": "application/json"
        }

        # 构建完整提示词
        full_prompt = prompt
        if negative_prompt:
            full_prompt += f"，不要: {negative_prompt}"

        data = {
            "prompt": full_prompt,
            "width": params.get("width", 1024),
            "height": params.get("height", 1024),
            "image_num": 1
        }

        url = f"{api_url}/rpc/2.0/ai_custom/v1/wenxinworkshop/text2image/sd_xl?access_token={access_token}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=data, headers=headers)

            if resp.status_code != 200:
                error_text = resp.text
                return {"status": "error", "msg": f"百度文心 API Error ({resp.status_code}): {error_text}"}

            result = resp.json()

            if "data" in result and result["data"]:
                # 百度返回的是 base64 编码的图片
                image_data = result["data"][0]["b64_image"]
                # 这里需要将 base64 转换为可访问的 URL，或者直接返回 base64
                return {
                    "status": "completed",
                    "images": [f"data:image/png;base64,{image_data}"],
                    "image_url": f"data:image/png;base64,{image_data}",
                    "backend": "external_api",
                    "provider": "baidu",
                    "seed": params.get("seed", -1)
                }

            return {"status": "error", "msg": "百度文心 API 返回数据格式错误"}

    async def _generate_tencent(self, prompt: str, negative_prompt: str, api_key: str, api_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """腾讯混元图像生成 API 调用"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 构建完整提示词
        full_prompt = prompt
        if negative_prompt:
            full_prompt += f"，负面提示词: {negative_prompt}"

        data = {
            "Prompt": full_prompt,
            "NegativePrompt": negative_prompt,
            "Styles": [params.get("style", "201")],  # 201 表示默认风格
            "ResultConfig": {
                "Resolution": f"{params.get('width', 1024)}:{params.get('height', 1024)}"
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{api_url}/", json=data, headers=headers)

            if resp.status_code != 200:
                error_text = resp.text
                return {"status": "error", "msg": f"腾讯混元 API Error ({resp.status_code}): {error_text}"}

            result = resp.json()

            if "Response" in result and "ResultImage" in result["Response"]:
                image_data = result["Response"]["ResultImage"]
                return {
                    "status": "completed",
                    "images": [f"data:image/png;base64,{image_data}"],
                    "image_url": f"data:image/png;base64,{image_data}",
                    "backend": "external_api",
                    "provider": "tencent",
                    "seed": params.get("seed", -1)
                }

            return {"status": "error", "msg": "腾讯混元 API 返回数据格式错误"}

    async def _get_baidu_access_token(self, api_key: str, secret_key: str) -> Optional[str]:
        """获取百度 API 的 access_token"""
        if not secret_key:
            return None

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, params=params)
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get("access_token")
        except Exception as e:
            logger.error(f"Failed to get Baidu access token: {e}")

        return None

    async def check_status(self, task_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查异步任务状态（主要用于通义千问等支持异步的 API）"""
        if params is None:
            params = {}

        provider = params.get("provider", "openai")

        if provider.lower() in ["tongyi", "qwen", "aliyun"]:
            return await self._check_tongyi_status(task_id, params)
        else:
            # 对于同步返回的 API，直接返回完成状态
            return {"status": "completed"}

    async def _check_tongyi_status(self, task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """检查通义千问异步任务状态"""
        api_key = params.get("api_key") or self.api_key
        api_url = params.get("api_url") or self.api_url

        # 验证 API Key
        if not api_key or api_key.strip() == "":
            return {"status": "error", "msg": "API Key 未配置"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{api_url}/tasks/{task_id}", headers=headers)

                if resp.status_code != 200:
                    return {"status": "error", "msg": f"查询任务状态失败: {resp.text}"}

                result = resp.json()
                task_status = result.get("output", {}).get("task_status", "UNKNOWN")

                if task_status == "SUCCEEDED":
                    image_url = result.get("output", {}).get("results", [{}])[0].get("url", "")
                    return {
                        "status": "completed",
                        "images": [image_url],
                        "image_url": image_url,
                        "backend": "external_api",
                        "provider": "tongyi"
                    }
                elif task_status == "FAILED":
                    return {"status": "error", "msg": "任务执行失败"}
                else:
                    return {"status": "processing", "progress": 50}

        except Exception as e:
            logger.error(f"Failed to check Tongyi task status: {e}")
            return {"status": "error", "msg": str(e)}
