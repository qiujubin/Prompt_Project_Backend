"""检查 COS 图片存储情况

这个脚本帮助你验证图片是否成功上传到 COS。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.drawing import Drawing
from models.user import User
from core.config import get_settings
from tabulate import tabulate

def check_cos_images():
    """检查数据库中的 COS 图片记录"""
    settings = get_settings()
    engine = create_engine(settings.db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 查询最近的 10 条记录
        drawings = db.query(Drawing).order_by(Drawing.created_at.desc()).limit(10).all()

        if not drawings:
            print("❌ 数据库中没有找到任何作品记录")
            return

        print(f"\n✅ 找到 {len(drawings)} 条最近的作品记录\n")

        # 准备表格数据
        table_data = []
        for drawing in drawings:
            user = db.query(User).filter(User.id == drawing.user_id).first()
            username = user.username if user else "Unknown"

            # 检查是否有 COS 字段
            has_cos = bool(drawing.cos_key)
            status_icon = "✅" if has_cos else "❌"

            table_data.append([
                drawing.id,
                username,
                drawing.status,
                status_icon,
                drawing.cos_key[:50] + "..." if drawing.cos_key and len(drawing.cos_key) > 50 else (drawing.cos_key or "N/A"),
                f"{drawing.file_size / 1024:.1f} KB" if drawing.file_size else "N/A",
                drawing.created_at.strftime("%Y-%m-%d %H:%M:%S")
            ])

        # 打印表格
        headers = ["ID", "用户", "状态", "COS", "COS Key", "大小", "创建时间"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # 统计信息
        total = len(drawings)
        with_cos = sum(1 for d in drawings if d.cos_key)
        without_cos = total - with_cos

        print(f"\n📊 统计信息:")
        print(f"  总记录数: {total}")
        print(f"  已上传 COS: {with_cos} ({with_cos/total*100:.1f}%)")
        print(f"  未上传 COS: {without_cos} ({without_cos/total*100:.1f}%)")

        # 显示完整的 COS URL 示例
        if with_cos > 0:
            first_with_cos = next(d for d in drawings if d.cos_key)
            print(f"\n🔗 COS URL 示例:")
            print(f"  原图: {first_with_cos.image_url}")
            if first_with_cos.thumbnail_url:
                print(f"  缩略图: {first_with_cos.thumbnail_url}")

            print(f"\n💡 提示:")
            print(f"  1. 复制上面的 URL 到浏览器中访问，验证图片是否可以正常显示")
            print(f"  2. 登录腾讯云控制台: https://console.cloud.tencent.com/cos")
            print(f"  3. 进入 Bucket: photo-db-1304922788")
            print(f"  4. 导航到路径: ai-drawing-platform/images/{first_with_cos.user_id}/")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("COS 图片存储检查工具")
    print("=" * 80)
    check_cos_images()
    print("\n" + "=" * 80)
