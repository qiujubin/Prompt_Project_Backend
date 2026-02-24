"""历史图片迁移到 COS 脚本

将现有的本地图片迁移到腾讯云 COS。
支持断点续传和批量处理。

Usage:
    python -m Backend.scripts.migrate_images_to_cos --batch-size 100
    python -m Backend.scripts.migrate_images_to_cos --resume-from 1000
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from Backend.database import SessionLocal
from Backend.models.drawing import Drawing
from Backend.services.cos import COSStorageService, ImageProcessor, StorageManager
from Backend.core.logger import get_logger

logger = get_logger(__name__)


async def migrate_images_to_cos(
    batch_size: int = 100,
    resume_from: Optional[int] = None,
    dry_run: bool = False
):
    """迁移现有本地图片到 COS

    Args:
        batch_size: 每批处理的图片数量
        resume_from: 从指定的 drawing_id 开始恢复
        dry_run: 是否为试运行（不实际上传）

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
    """
    db = SessionLocal()
    cos_service = COSStorageService()
    image_processor = ImageProcessor()

    # 查询需要迁移的 drawings（没有 cos_key 的记录）
    query = db.query(Drawing).filter(Drawing.cos_key == None)
    if resume_from:
        query = query.filter(Drawing.id >= resume_from)

    total = query.count()
    migrated = 0
    skipped = 0
    failed = []

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting migration of {total} images")
    logger.info(f"Batch size: {batch_size}, Resume from: {resume_from or 'start'}")

    start_time = datetime.now()

    try:
        # 分批处理
        offset = 0
        while True:
            batch = query.offset(offset).limit(batch_size).all()
            if not batch:
                break

            for drawing in batch:
                try:
                    # 跳过已经是 COS URL 的记录
                    if drawing.image_url and "cos." in drawing.image_url:
                        logger.info(f"Skipping drawing {drawing.id}: already on COS")
                        skipped += 1
                        continue

                    # 检查本地文件是否存在
                    local_path = drawing.image_url
                    if not local_path or not os.path.exists(local_path):
                        logger.warning(f"Image not found for drawing {drawing.id}: {local_path}")
                        failed.append((drawing.id, "File not found"))
                        continue

                    if dry_run:
                        logger.info(f"[DRY RUN] Would migrate drawing {drawing.id}: {local_path}")
                        migrated += 1
                        continue

                    # 生成缩略图
                    thumbnail_data = image_processor.generate_thumbnail(local_path)
                    thumbnail_path = f"/tmp/migrate_{drawing.id}_thumb.png"
                    with open(thumbnail_path, 'wb') as f:
                        f.write(thumbnail_data)

                    # 上传原图到 COS
                    original_result = await cos_service.upload_image(
                        local_path,
                        drawing.user_id,
                        drawing.id,
                        is_thumbnail=False
                    )

                    # 上传缩略图到 COS
                    thumbnail_result = await cos_service.upload_image(
                        thumbnail_path,
                        drawing.user_id,
                        drawing.id,
                        is_thumbnail=True
                    )

                    # 更新数据库
                    drawing.image_url = original_result["cos_url"]
                    drawing.cos_key = original_result["cos_key"]
                    drawing.thumbnail_url = thumbnail_result["cos_url"]
                    drawing.thumbnail_key = thumbnail_result["cos_key"]
                    drawing.file_size = original_result["file_size"]

                    # 更新用户存储统计
                    StorageManager.update_user_storage(
                        drawing.user_id,
                        original_result["file_size"],
                        db
                    )

                    db.commit()
                    migrated += 1

                    # 清理临时文件
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)

                    if migrated % 10 == 0:
                        logger.info(f"Progress: {migrated}/{total} images migrated")

                except Exception as e:
                    logger.error(f"Failed to migrate drawing {drawing.id}: {e}")
                    failed.append((drawing.id, str(e)))
                    db.rollback()

            offset += batch_size

    finally:
        db.close()

    # 生成报告
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    report = {
        "total": total,
        "migrated": migrated,
        "skipped": skipped,
        "failed": len(failed),
        "failed_details": failed,
        "duration_seconds": duration,
        "dry_run": dry_run
    }

    logger.info("=" * 60)
    logger.info("Migration Report")
    logger.info("=" * 60)
    logger.info(f"Total images: {total}")
    logger.info(f"Migrated: {migrated}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"Failed: {len(failed)}")
    logger.info(f"Duration: {duration:.2f} seconds")
    if dry_run:
        logger.info("[DRY RUN] No actual changes were made")
    logger.info("=" * 60)

    if failed:
        logger.info("Failed migrations:")
        for drawing_id, error in failed[:10]:  # 只显示前 10 个
            logger.info(f"  - Drawing {drawing_id}: {error}")
        if len(failed) > 10:
            logger.info(f"  ... and {len(failed) - 10} more")

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate images to Tencent Cloud COS")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--resume-from", type=int, help="Resume from drawing ID")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without actual upload")

    args = parser.parse_args()

    # 运行迁移
    asyncio.run(migrate_images_to_cos(
        batch_size=args.batch_size,
        resume_from=args.resume_from,
        dry_run=args.dry_run
    ))
