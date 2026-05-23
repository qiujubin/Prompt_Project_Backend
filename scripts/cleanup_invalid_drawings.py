#!/usr/bin/env python
"""
清理 drawings 表中 image_url 无效（图片已不存在）的记录，
以及关联的 drawing_likes 和 drawing_favorites 数据。

Usage:
    python -m Backend.scripts.cleanup_invalid_drawings --dry-run  # 预览
    python -m Backend.scripts.cleanup_invalid_drawings          # 正式执行
"""
import asyncio
import sys
import argparse
from urllib.parse import urlparse

import httpx
from database import engine, Session
from sqlalchemy import text
from models.drawing import Drawing
from models.drawing_interaction import DrawingLike, DrawingFavorite
from core.logger import get_logger

logger = get_logger(__name__)


async def check_url_valid(url: str) -> bool:
    """检查 URL 是否返回 200"""
    if not url:
        return False
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.head(url)
            return resp.status_code == 200
    except Exception:
        return False


def get_invalid_drawings(db):
    """找出 image_url 无效的 drawings"""
    result = db.execute(
        text("""
            SELECT id, user_id, status, image_url
            FROM drawings
            WHERE image_url IS NOT NULL AND image_url != ''
        """)
    )
    return result.fetchall()


async def main(dry_run: bool = True):
    from database import get_db

    with Session() as db:
        logger.info("正在查找 image_url 无效的 drawings...")
        invalid_drawings = get_invalid_drawings(db)
        logger.info(f"共发现 {len(invalid_drawings)} 条 drawings 需要检查")

        to_delete_ids = []
        for row in invalid_drawings:
            drawing_id, user_id, status, image_url = row
            valid = await check_url_valid(image_url)
            if not valid:
                logger.info(f"  [!] drawing {drawing_id} ({status}): {image_url[:60]}... -> 无效")
                to_delete_ids.append(drawing_id)
            else:
                logger.info(f"  [OK] drawing {drawing_id}: {image_url[:60]}... -> 有效")

        logger.info(f"\n将删除 {len(to_delete_ids)} 条无效 drawings")

        if dry_run:
            logger.info("[DRY-RUN] 预览要删除的 drawing IDs:")
            for did in to_delete_ids:
                print(f"  - {did}")
        else:
            # 1. 先删 likes/favorites（不设外键级联）
            for did in to_delete_ids:
                db.execute(
                    text("DELETE FROM drawing_likes WHERE drawing_id = :did"),
                    {"did": did}
                )
                db.execute(
                    text("DELETE FROM drawing_favorites WHERE drawing_id = :did"),
                    {"did": did}
                )
                db.execute(
                    text("DELETE FROM drawings WHERE id = :did"),
                    {"did": did}
                )
                logger.info(f"  [DEL] drawing {did} 及其 likes/favorites 已删除")

            db.commit()
            logger.info(f"\n完成！共删除 {len(to_delete_ids)} 条记录")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", dest="dry_run", action="store_false")
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY-RUN 模式（预览）===")
    else:
        print("=== 正式执行模式 ===")

    asyncio.run(main(dry_run=args.dry_run))