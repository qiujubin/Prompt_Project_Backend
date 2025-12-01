import httpx
from typing import Dict, Any
from core.config import settings
from .base import AIGeneratorBase

class ExternalAIGenerator(AIGeneratorBase):
    """外部 AI API 生成器（示例：OpenAI DALL-E）。"""

    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.api_url = settings.AI_API_URL

    async def generate_image(self, prompt: str, negative_prompt: str = "", params: Dict[str, Any] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
            
        api_key = params.get("api_key") or self.api_key
        api_url = params.get("api_url") or self.api_url
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 示例请求体 (OpenAI DALL-E 3)
        data = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024"
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{api_url}/images/generations", json=data, headers=headers, timeout=60.0)
                
                if resp.status_code != 200:
                    return {"status": "error", "msg": f"API Error: {resp.text}"}
                
                result = resp.json()
                image_url = result['data'][0]['url']
                
                return {
                    "status": "completed",
                    "image_url": image_url,
                    "backend": "external_api"
                }
        except Exception as e:
            return {"status": "error", "msg": str(e)}

    async def check_status(self, task_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        # 对于同步返回的 API，此方法可能用不到，直接返回完成
        return {"status": "completed"}
