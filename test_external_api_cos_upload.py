"""
测试外部 API 生成图片并上传到 COS 的功能
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models.user import User
from models.drawing import Drawing
from services.ai.external import ExternalAIGenerator
from api.v1.generation import upload_image_to_cos
from core.logger import get_logger

logger = get_logger(__name__)


async def test_external_api_generation():
    """测试外部 API 生成并上传到 COS"""
    db: Session = SessionLocal()

    try:
        # 1. 获取测试用户
        test_user = db.query(User).filter(User.username == "test_user").first()
        if not test_user:
            logger.error("测试用户不存在，请先创建 test_user")
            return

        logger.info(f"使用测试用户: {test_user.username} (ID: {test_user.id})")

        # 2. 测试通义千问 API 生成
        generator = ExternalAIGenerator()

        params = {
            "provider": "tongyi",
            "model_name": "qwen-image-2.0",
            "width": 1024,
            "height": 1024,
            "seed": -1
        }

        logger.info("开始测试通义千问图片生成...")
        result = await generator.generate_image(
            "a beautiful sunset over the ocean",
            "ugly, blurry",
            params
        )

        logger.info(f"生成结果: {result}")

        # 3. 如果生成成功，创建 Drawing 记录并上传到 COS
        if result.get("status") == "completed":
            images = result.get("images", [])
            if images:
                image_url = images[0]
                logger.info(f"图片 URL: {image_url}")

                # 创建 Drawing 记录
                new_drawing = Drawing(
                    user_id=test_user.id,
                    prompt="a beautiful sunset over the ocean",
                    negative_prompt="ugly, blurry",
                    model_name="qwen-image-2.0",
                    width=1024,
                    height=1024,
                    seed=str(result.get("seed", -1)),
                    status="finish",
                    image_url=image_url,
                    is_public=True
                )
                db.add(new_drawing)
                db.commit()
                db.refresh(new_drawing)

                logger.info(f"创建 Drawing 记录: ID={new_drawing.id}")

                # 上传到 COS
                logger.info("开始上传到 COS...")
                await upload_image_to_cos(new_drawing, image_url, db)

                # 刷新记录查看更新
                db.refresh(new_drawing)
                logger.info(f"上传成功！")
                logger.info(f"  - COS URL: {new_drawing.image_url}")
                logger.info(f"  - COS Key: {new_drawing.cos_key}")
                logger.info(f"  - Thumbnail URL: {new_drawing.thumbnail_url}")
                logger.info(f"  - Thumbnail Key: {new_drawing.thumbnail_key}")
                logger.info(f"  - File Size: {new_drawing.file_size} bytes")

                return new_drawing

        elif result.get("status") == "queued":
            logger.info("任务已加入队列，需要轮询状态")
            task_id = result.get("prompt_id")
            logger.info(f"任务 ID: {task_id}")

            # 轮询任务状态
            max_attempts = 30
            for i in range(max_attempts):
                await asyncio.sleep(2)
                status_result = await generator.check_status(task_id, params)
                logger.info(f"轮询 {i+1}/{max_attempts}: {status_result.get('status')}")

                if status_result.get("status") == "completed":
                    images = status_result.get("images", [])
                    if images:
                        image_url = images[0]
                        logger.info(f"图片 URL: {image_url}")

                        # 创建 Drawing 记录
                        new_drawing = Drawing(
                            user_id=test_user.id,
                            prompt="a beautiful sunset over the ocean",
                            negative_prompt="ugly, blurry",
                            model_name="qwen-image-2.0",
                            width=1024,
                            height=1024,
                            seed=str(status_result.get("seed", -1)),
                            status="finish",
                            image_url=image_url,
                            is_public=True,
                            prompt_id=task_id
                        )
                        db.add(new_drawing)
                        db.commit()
                        db.refresh(new_drawing)

                        logger.info(f"创建 Drawing 记录: ID={new_drawing.id}")

                        # 上传到 COS
                        logger.info("开始上传到 COS...")
                        await upload_image_to_cos(new_drawing, image_url, db)

                        # 刷新记录查看更新
                        db.refresh(new_drawing)
                        logger.info(f"上传成功！")
                        logger.info(f"  - COS URL: {new_drawing.image_url}")
                        logger.info(f"  - COS Key: {new_drawing.cos_key}")
                        logger.info(f"  - Thumbnail URL: {new_drawing.thumbnail_url}")
                        logger.info(f"  - Thumbnail Key: {new_drawing.thumbnail_key}")
                        logger.info(f"  - File Size: {new_drawing.file_size} bytes")

                        return new_drawing

                elif status_result.get("status") == "error":
                    logger.error(f"任务失败: {status_result.get('msg')}")
                    break

            logger.warning("轮询超时")

        else:
            logger.error(f"生成失败: {result.get('msg')}")

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)

    finally:
        db.close()


async def test_base64_image_upload():
    """测试 Base64 图片上传到 COS"""
    db: Session = SessionLocal()

    try:
        # 1. 获取测试用户
        test_user = db.query(User).filter(User.username == "test_user").first()
        if not test_user:
            logger.error("测试用户不存在，请先创建 test_user")
            return

        logger.info(f"使用测试用户: {test_user.username} (ID: {test_user.id})")

        # 2. 创建一个简单的测试图片（1x1 像素的红色图片）
        import base64
        from PIL import Image
        import io

        # 创建 1x1 红色图片
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()

        # 转换为 Base64
        base64_str = base64.b64encode(img_data).decode('utf-8')
        base64_url = f"data:image/png;base64,{base64_str}"

        logger.info("创建测试 Base64 图片")

        # 3. 创建 Drawing 记录
        new_drawing = Drawing(
            user_id=test_user.id,
            prompt="test base64 image",
            negative_prompt="",
            model_name="test",
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

        # 4. 上传到 COS
        logger.info("开始上传 Base64 图片到 COS...")
        await upload_image_to_cos(new_drawing, base64_url, db)

        # 5. 刷新记录查看更新
        db.refresh(new_drawing)
        logger.info(f"上传成功！")
        logger.info(f"  - COS URL: {new_drawing.image_url}")
        logger.info(f"  - COS Key: {new_drawing.cos_key}")
        logger.info(f"  - Thumbnail URL: {new_drawing.thumbnail_url}")
        logger.info(f"  - Thumbnail Key: {new_drawing.thumbnail_key}")
        logger.info(f"  - File Size: {new_drawing.file_size} bytes")

        return new_drawing

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("测试 1: 外部 API 生成并上传到 COS")
    print("=" * 60)
    asyncio.run(test_external_api_generation())

    print("\n" + "=" * 60)
    print("测试 2: Base64 图片上传到 COS")
    print("=" * 60)
    asyncio.run(test_base64_image_upload())
