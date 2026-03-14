"""
测试 API 模型端点
"""
import sys
import os

# 添加 Backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ai.providers_config import get_provider_config

def test_tongyi_models():
    """测试通义千问模型配置"""
    config = get_provider_config('tongyi')

    print("=" * 50)
    print("通义千问配置测试")
    print("=" * 50)
    print(f"Provider ID: {config.id}")
    print(f"Provider Name: {config.name}")
    print(f"Description: {config.description}")
    print(f"API Key: {'已配置' if config.api_key else '未配置'}")
    print(f"API URL: {config.api_url or '默认'}")
    print(f"Is Configured: {'是' if config.is_configured else '否'}")
    print(f"Supported Models: {config.supported_models}")
    print("=" * 50)

    # 模拟 API 响应
    response = {
        "code": 200,
        "msg": "OK",
        "data": {
            "provider": config.id,
            "models": config.supported_models
        }
    }

    print("\n模拟 API 响应:")
    print(response)
    print("\n前端应该访问: response.data.models")
    print(f"结果: {response['data']['models']}")

if __name__ == "__main__":
    test_tongyi_models()
