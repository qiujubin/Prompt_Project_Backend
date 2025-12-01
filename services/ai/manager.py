from .base import AIGeneratorBase
from .comfyui import ComfyUIGenerator
from .external import ExternalAIGenerator

def get_ai_generator(type: str = "comfyui") -> AIGeneratorBase:
    """工厂方法：获取 AI 生成器实例。
    
    Args:
        type: 'comfyui' 或 'external'
    """
    if type == "comfyui":
        return ComfyUIGenerator()
    elif type == "external":
        return ExternalAIGenerator()
    else:
        raise ValueError(f"Unknown AI generator type: {type}")
