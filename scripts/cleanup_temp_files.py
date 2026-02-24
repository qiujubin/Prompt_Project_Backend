"""清理临时文件脚本

清理超过 24 小时的临时图片文件。

Usage:
    python -m Backend.scripts.cleanup_temp_files
    python -m Backend.scripts.cleanup_temp_files --max-age 48  # 48 小时
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from Backend.core.logger import get_logger

logger = get_logger(__name__)


def cleanup_temp_files(max_age_hours: int = 24, dry_run: bool = False):
    """清理过期的临时文件

    Args:
        max_age_hours: 文件最大保留时间（小时）
        dry_run: 是否为试运行（不实际删除）

    Requirements: 9.2, 9.3, 9.4
    """
    import tempfile
    temp_dir = tempfile.gettempdir()

    # 要清理的文件模式
    patterns = [
        "drawing_*",
        "migrate_*",
        "*.tmp"
    ]

    cutoff_time = time.time() - (max_age_hours * 3600)
    deleted_count = 0
    deleted_size = 0
    failed_count = 0

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting cleanup of temp files")
    logger.info(f"Temp directory: {temp_dir}")
    logger.info(f"Max age: {max_age_hours} hours")
    logger.info(f"Cutoff time: {datetime.fromtimestamp(cutoff_time)}")

    try:
        temp_path = Path(temp_dir)

        for pattern in patterns:
            for file_path in temp_path.glob(pattern):
                try:
                    # 跳过目录
                    if file_path.is_dir():
                        continue

                    # 检查文件修改时间
                    file_mtime = file_path.stat().st_mtime
                    if file_mtime > cutoff_time:
                        continue

                    file_size = file_path.stat().st_size
                    file_age_hours = (time.time() - file_mtime) / 3600

                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would delete: {file_path.name} "
                            f"(age: {file_age_hours:.1f}h, size: {file_size} bytes)"
                        )
                        deleted_count += 1
                        deleted_size += file_size
                    else:
                        file_path.unlink()
                        logger.info(
                            f"Deleted: {file_path.name} "
                            f"(age: {file_age_hours:.1f}h, size: {file_size} bytes)"
                        )
                        deleted_count += 1
                        deleted_size += file_size

                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
                    failed_count += 1

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise

    # 生成报告
    deleted_size_mb = deleted_size / (1024 * 1024)

    logger.info("=" * 60)
    logger.info("Cleanup Report")
    logger.info("=" * 60)
    logger.info(f"Files deleted: {deleted_count}")
    logger.info(f"Space freed: {deleted_size_mb:.2f} MB")
    logger.info(f"Failed: {failed_count}")
    if dry_run:
        logger.info("[DRY RUN] No actual changes were made")
    logger.info("=" * 60)

    return {
        "deleted_count": deleted_count,
        "deleted_size": deleted_size,
        "failed_count": failed_count,
        "dry_run": dry_run
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup temporary files")
    parser.add_argument("--max-age", type=int, default=24, help="Maximum file age in hours")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without actual deletion")

    args = parser.parse_args()

    # 运行清理
    cleanup_temp_files(
        max_age_hours=args.max_age,
        dry_run=args.dry_run
    )
