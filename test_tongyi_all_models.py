"""
测试通义千问所有模型
"""
import asyncio
import os
from dotenv import load_dotenv
from services.ai.external import ExternalAIGenerator

load_dotenv()

async def test_model(model_name: str, description: str):
    """测试指定模型"""
    print("=" * 60)
    print(f"测试模型: {model_name}")
    print(f"描述: {description}")
    print("=" * 60)

    generator = ExternalAIGenerator()
    prompt = "一只可爱的橘猫"
    negative_prompt = "低分辨率"

    params = {
        "model_name": model_name,
        "width": 1024,
        "height": 1024,
        "seed": 42,
        "prompt_extend": True,
        "watermark": False,
        "api_key": os.getenv("TONGYI_API_KEY"),
        "api_url": os.getenv("TONGYI_API_URL", "https://dashscope.aliyuncs.com/api/v1")
    }

    print(f"\n提示词: {prompt}")
    print(f"API Key: {params['api_key'][:20]}..." if params['api_key'] else "未配置")
    print("\n正在调用...")

    try:
        result = await generator.generate_image(prompt, negative_prompt, params)
        status = result.get('status')

        if status == "completed":
            print(f"✓ 成功! URL: {result.get('image_url')[:50]}...")
        elif status == "queued":
            print(f"✓ 任务创建! ID: {result.get('prompt_id')}")
        elif status == "error":
            print(f"✗ 失败: {result.get('msg')}")
        else:
            print(f"状态: {result}")
    except Exception as e:
        print(f"✗ 异常: {str(e)}")

    print("\n")

async def main():
    api_key = os.getenv("TONGYI_API_KEY")
    if not api_key:
        print("错误: 未设置 TONGYI_API_KEY")
        return

    models = [
        ("qwen-image-2.0", "新 API - 标准版（同步）"),
        ("qwen-image-plus", "新 API - Plus 版（同步）"),
        ("z-image-turbo", "新 API - Turbo 版（同步）"),
    ]

    for model_name, description in models:
        await test_model(model_name, description)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
