from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class AIGeneratorBase(ABC):
    """AI 生成器抽象基类。
    
    定义了所有 AI 生成服务（如 ComfyUI、External API）必须实现的接口。
    """

    @abstractmethod
    async def generate_image(self, prompt: str, negative_prompt: str = "", params: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成图片。

        Args:
            prompt: 正向提示词
            negative_prompt: 反向提示词
            params: 其他参数（如 seed, width, height, model_name 等）

        Returns:
            Dict: 包含生成结果的字典，例如 {"image_url": "...", "seed": "...", "status": "success"}
        """
        pass

    @abstractmethod
    async def check_status(self, task_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查任务状态。"""
        pass
