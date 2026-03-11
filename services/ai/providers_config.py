"""
外部 API 提供商配置
管理所有支持的外部 AI 图像生成服务提供商
"""
import os
from typing import Dict, List, Optional
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    """提供商配置模型"""
    id: str
    name: str
    description: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    secret_key: Optional[str] = None
    is_configured: bool = False
    requires_secret_key: bool = False
    supported_models: List[str] = []


# 支持的提供商配置
PROVIDERS = {
    "tongyi": {
        "name": "通义千问",
        "description": "阿里云通义千问 AI 绘图",
        "env_key": "TONGYI_API_KEY",
        "env_url": "TONGYI_API_URL",
        "requires_secret": False,
        "default_models": ["qwen-image-2.0", "qwen-image-plus", "z-image-turbo"]
    },
    "baidu": {
        "name": "百度文心",
        "description": "百度文心一言 AI 绘图",
        "env_key": "BAIDU_API_KEY",
        "env_secret": "BAIDU_SECRET_KEY",
        "env_url": "BAIDU_API_URL",
        "requires_secret": True,
        "default_models": ["sd_xl", "ernie-vilg-v2"]
    },
    "deepseek": {
        "name": "DeepSeek",
        "description": "DeepSeek AI 绘图",
        "env_key": "DEEPSEEK_API_KEY",
        "env_url": "DEEPSEEK_API_URL",
        "requires_secret": False,
        "default_models": ["deepseek-draw"]
    },
    "openai": {
        "name": "OpenAI DALL-E",
        "description": "OpenAI DALL-E 图像生成",
        "env_key": "OPENAI_API_KEY",
        "env_url": "OPENAI_API_URL",
        "requires_secret": False,
        "default_models": ["dall-e-3", "dall-e-2"]
    },
    "custom": {
        "name": "自定义",
        "description": "使用自定义 API 配置",
        "env_key": None,
        "requires_secret": False,
        "default_models": []
    }
}


def load_provider_configs() -> Dict[str, ProviderConfig]:
    """
    从环境变量加载提供商配置

    Returns:
        Dict[str, ProviderConfig]: 提供商配置字典
    """
    configs = {}

    for provider_id, provider_info in PROVIDERS.items():
        api_key = None
        api_url = None
        secret_key = None
        is_configured = True

        if provider_id != "custom":
            # 从环境变量读取
            env_key = provider_info.get("env_key")
            if env_key:
                api_key = os.getenv(env_key)

            env_url = provider_info.get("env_url")
            if env_url:
                api_url = os.getenv(env_url)

            # 检查是否需要 Secret Key
            if provider_info.get("requires_secret"):
                env_secret = provider_info.get("env_secret")
                if env_secret:
                    secret_key = os.getenv(env_secret)

            # 检查是否配置完整
            is_configured = bool(api_key)
            if provider_info.get("requires_secret"):
                is_configured = is_configured and bool(secret_key)

        configs[provider_id] = ProviderConfig(
            id=provider_id,
            name=provider_info["name"],
            description=provider_info["description"],
            api_key=api_key,
            api_url=api_url,
            secret_key=secret_key,
            is_configured=is_configured,
            requires_secret_key=provider_info.get("requires_secret", False),
            supported_models=provider_info.get("default_models", [])
        )

    return configs


def get_provider_config(provider_id: str) -> Optional[ProviderConfig]:
    """
    获取指定提供商的配置

    Args:
        provider_id: 提供商 ID

    Returns:
        ProviderConfig: 提供商配置，如果不存在返回 None
    """
    configs = load_provider_configs()
    return configs.get(provider_id)
