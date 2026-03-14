"""
测试提供商配置系统
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ai.providers_config import load_provider_configs, get_provider_config

def test_load_providers():
    """测试加载提供商配置"""
    print("=" * 50)
    print("测试加载提供商配置")
    print("=" * 50)

    configs = load_provider_configs()

    print(f"\n找到 {len(configs)} 个提供商:\n")

    for provider_id, config in configs.items():
        print(f"提供商: {config.name} ({config.id})")
        print(f"  描述: {config.description}")
        print(f"  已配置: {'是' if config.is_configured else '否'}")
        print(f"  需要 Secret Key: {'是' if config.requires_secret_key else '否'}")
        print(f"  支持的模型: {', '.join(config.supported_models) if config.supported_models else '无'}")
        if config.api_url:
            print(f"  API URL: {config.api_url}")
        print()

def test_get_provider():
    """测试获取单个提供商配置"""
    print("=" * 50)
    print("测试获取单个提供商配置")
    print("=" * 50)

    provider_id = "tongyi"
    config = get_provider_config(provider_id)

    if config:
        print(f"\n提供商: {config.name}")
        print(f"已配置: {'是' if config.is_configured else '否'}")
        print(f"支持的模型: {config.supported_models}")
    else:
        print(f"\n未找到提供商: {provider_id}")

if __name__ == "__main__":
    test_load_providers()
    test_get_provider()
