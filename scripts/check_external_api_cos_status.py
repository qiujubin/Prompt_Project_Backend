"""
检查外部 API 生成的图片是否已上传到 COS
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import and_, or_
from database import SessionLocal
from models.drawing import Drawing
from core.logger import get_logger

logger = get_logger(__name__)


def check_external_api_cos_status():
    """检查外部 API 生成的图片 COS 上传状态"""
    db = SessionLocal()

    try:
        print("=" * 80)
        print("检查外部 API 生成的图片 COS 上传状态")
        print("=" * 80)

        # 1. 统计所有完成的作品
        total_finished = db.query(Drawing).filter(Drawing.status == "finish").count()
        print(f"\n📊 总完成作品数: {total_finished}")

        # 2. 统计已上传到 COS 的作品（有 cos_key）
        uploaded_to_cos = db.query(Drawing).filter(
            and_(
                Drawing.status == "finish",
                Drawing.cos_key.isnot(None),
                Drawing.cos_key != ""
            )
        ).count()
        print(f"✅ 已上传到 COS: {uploaded_to_cos}")

        # 3. 统计未上传到 COS 的作品（没有 cos_key）
        not_uploaded = db.query(Drawing).filter(
            and_(
                Drawing.status == "finish",
                or_(
                    Drawing.cos_key.is_(None),
                    Drawing.cos_key == ""
                )
            )
        ).count()
        print(f"❌ 未上传到 COS: {not_uploaded}")

        # 4. 查找可能是外部 API 生成的作品（image_url 包含 http 但不是 COS URL）
        external_api_drawings = db.query(Drawing).filter(
            and_(
                Drawing.status == "finish",
                or_(
                    Drawing.cos_key.is_(None),
                    Drawing.cos_key == ""
                ),
                or_(
                    Drawing.image_url.like("http%"),
                    Drawing.image_url.like("data:image%")
                )
            )
        ).all()

        print(f"\n🔍 疑似外部 API 生成但未上传到 COS 的作品: {len(external_api_drawings)}")

        if external_api_drawings:
            print("\n详细列表:")
            print("-" * 80)
            for drawing in external_api_drawings[:10]:  # 只显示前 10 条
                print(f"ID: {drawing.id}")
                print(f"  用户: {drawing.user_id}")
                print(f"  模型: {drawing.model_name}")
                print(f"  提示词: {drawing.prompt[:50]}...")
                print(f"  图片 URL: {drawing.image_url[:80]}...")
                print(f"  创建时间: {drawing.created_at}")
                print(f"  COS Key: {drawing.cos_key or '(空)'}")
                print("-" * 80)

            if len(external_api_drawings) > 10:
                print(f"... 还有 {len(external_api_drawings) - 10} 条记录未显示")

        # 5. 统计不同模型的分布
        print("\n📈 未上传作品的模型分布:")
        from sqlalchemy import func
        model_stats = db.query(
            Drawing.model_name,
            func.count(Drawing.id).label('count')
        ).filter(
            and_(
                Drawing.status == "finish",
                or_(
                    Drawing.cos_key.is_(None),
                    Drawing.cos_key == ""
                )
            )
        ).group_by(Drawing.model_name).all()

        for model_name, count in model_stats:
            print(f"  {model_name}: {count} 个")

        # 6. 检查 Base64 图片
        base64_drawings = db.query(Drawing).filter(
            and_(
                Drawing.status == "finish",
                Drawing.image_url.like("data:image%")
            )
        ).count()
        print(f"\n🖼️  Base64 编码的图片: {base64_drawings}")

        # 7. 给出建议
        print("\n" + "=" * 80)
        print("💡 建议:")
        print("=" * 80)

        if not_uploaded > 0:
            print(f"1. 发现 {not_uploaded} 个作品未上传到 COS")
            print("2. 这些作品可能无法在个人中心正常显示")
            print("3. 建议运行迁移脚本将这些图片上传到 COS:")
            print("   python Backend/scripts/migrate_images_to_cos.py")
        else:
            print("✅ 所有作品都已上传到 COS，状态良好！")

        print("\n" + "=" * 80)

    except Exception as e:
        logger.error(f"检查失败: {e}", exc_info=True)

    finally:
        db.close()


if __name__ == "__main__":
    check_external_api_cos_status()
