"""
验证外部 API COS 上传修复
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User
from models.drawing import Drawing
from api.v1.generation import upload_image_to_cos
from core.logger import get_logger

logger = get_logger(__name__)


async def test_base64_upload():
    """测试 Base64 图片上传功能"""
    db: Session = SessionLocal()

    try:
        # 获取测试用户
        test_user = db.query(User).first()
        if not test_user:
            logger.error("没有找到用户，请先创建用户")
            return

        logger.info(f"使用用户: {test_user.username} (ID: {test_user.id})")

        # 创建一个简单的测试图片（红色 100x100 像素）
        from PIL import Image
        import io
        import base64

        # 创建红色图片
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()

        # 转换为 Base64
        base64_str = base64.b64encode(img_data).decode('utf-8')
        base64_url = f"data:image/png;base64,{base64_str}"

        logger.info("创建了测试 Base64 图片")

        # 创建 Drawing 记录
        new_drawing = Drawing(
            user_id=test_user.id,
            prompt="test base64 upload fix",
            negative_prompt="",
            model_name="test-fix",
            width=100,
            height=100,
            seed="-1",
            status="finish",
            image_url=base64_url,
            is_public=True
        )
        db.add(new_drawing)
        db.commit()
        db.refresh(new_drawing)

        logger.info(f"创建 Drawing 记录: ID={new_drawing.id}")

        # 测试上传到 COS
        logger.info("开始测试上传到 COS...")
        await upload_image_to_cos(new_drawing, base64_url, db)

        # 刷新记录查看更新
        db.refresh(new_drawing)

        # 验证结果
        success = True
        if not new_drawing.cos_key:
            logger.error("❌ cos_key 为空")
            success = False
        if not new_drawing.thumbnail_key:
            logger.error("❌ thumbnail_key 为空")
            success = False
        if not new_drawing.image_url or not new_drawing.image_url.startswith("https://"):
            logger.error("❌ image_url 不是 COS URL")
            success = False
        if not new_drawing.file_size or new_drawing.file_size <= 0:
            logger.error("❌ file_size 无效")
            success = False

        if success:
            logger.info("✅ 测试成功！")
            logger.info(f"  - COS URL: {new_drawing.image_url}")
            logger.info(f"  - COS Key: {new_drawing.cos_key}")
            logger.info(f"  - Thumbnail URL: {new_drawing.thumbnail_url}")
            logger.info(f"  - Thumbnail Key: {new_drawing.thumbnail_key}")
            logger.info(f"  - File Size: {new_drawing.file_size} bytes")
            return True
        else:
            logger.error("❌ 测试失败")
            return False

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False

    finally:
        db.close()


async def simulate_external_api_response():
    """模拟外部 API 同步返回的情况"""
    logger.info("模拟外部 API 同步返回...")

    # 模拟通义千问 2.0 的返回结果
    mock_result = {
        "status": "completed",
        "images": ["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="],
        "backend": "external_api",
        "provider": "tongyi",
        "seed": 12345
    }

    logger.info(f"模拟结果: {mock_result}")
    return mock_result


if __name__ == "__main__":
    print("=" * 60)
    print("验证外部 API COS 上传修复")
    print("=" * 60)

    # 测试 Base64 上传
    result = asyncio.run(test_base64_upload())

    if result:
        print("\n✅ 修复验证成功！外部 API 生成的图片现在可以正确上传到 COS 了。")
    else:
        print("\n❌ 修复验证失败，请检查错误日志。")

    # 模拟外部 API 响应
    print("\n" + "=" * 60)
    print("模拟外部 API 响应")
    print("=" * 60)
    asyncio.run(simulate_external_api_response())
