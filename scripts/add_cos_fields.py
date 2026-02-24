"""添加 COS 相关字段到数据库

手动运行此脚本以添加 COS 存储所需的数据库字段。
"""

import sys
import os

# 添加 Backend 目录到 Python 路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from sqlalchemy import text
from database import engine

def add_cos_fields():
    """添加 COS 相关字段"""

    with engine.connect() as conn:
        try:
            print("开始添加 COS 相关字段...")

            # 添加 Drawing 表字段
            print("\n1. 添加 drawings 表字段...")

            conn.execute(text("""
                ALTER TABLE drawings
                ADD COLUMN IF NOT EXISTS cos_key VARCHAR(512)
            """))
            print("   ✓ 添加 cos_key 字段")

            conn.execute(text("""
                ALTER TABLE drawings
                ADD COLUMN IF NOT EXISTS thumbnail_url TEXT
            """))
            print("   ✓ 添加 thumbnail_url 字段")

            conn.execute(text("""
                ALTER TABLE drawings
                ADD COLUMN IF NOT EXISTS thumbnail_key VARCHAR(512)
            """))
            print("   ✓ 添加 thumbnail_key 字段")

            conn.execute(text("""
                ALTER TABLE drawings
                ADD COLUMN IF NOT EXISTS file_size BIGINT
            """))
            print("   ✓ 添加 file_size 字段")

            # 添加索引
            print("\n2. 添加索引...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_drawings_cos_key
                ON drawings(cos_key)
            """))
            print("   ✓ 添加 cos_key 索引")

            # 添加 User 表字段
            print("\n3. 添加 users 表字段...")
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS storage_used BIGINT DEFAULT 0
            """))
            print("   ✓ 添加 storage_used 字段")

            conn.commit()

            print("\n✅ 所有字段添加成功！")
            print("\n现在可以重启服务器了。")

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    add_cos_fields()
