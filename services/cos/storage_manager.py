"""存储空间管理服务

负责管理用户存储空间使用情况。
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.user import User
from models.drawing import Drawing
from core.logger import get_logger

logger = get_logger(__name__)


class StorageManager:
    """存储空间管理服务

    提供用户存储空间管理功能：
    - 更新用户存储使用量
    - 查询用户存储统计
    - 计算实际存储使用量

    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """

    @staticmethod
    def update_user_storage(
        user_id: int,
        size_delta: int,
        db: Session
    ) -> None:
        """更新用户存储使用量

        Args:
            user_id: 用户 ID
            size_delta: 大小变化（字节，可为负数）
            db: 数据库会话

        Requirements: 7.2, 7.3
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return

            # 更新存储使用量
            current_storage = user.storage_used or 0
            new_storage = max(0, current_storage + size_delta)  # 确保不为负数
            user.storage_used = new_storage

            db.commit()

            logger.info(
                f"User {user_id} storage updated: {current_storage} -> {new_storage} "
                f"(delta: {size_delta})"
            )

        except Exception as e:
            logger.error(f"Failed to update user storage: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_user_storage_stats(
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """获取用户存储统计

        Args:
            user_id: 用户 ID
            db: 数据库会话

        Returns:
            {
                "total_images": 图片总数,
                "storage_used": 已使用空间（字节）,
                "storage_used_mb": 已使用空间（MB）,
                "average_size": 平均文件大小（字节）
            }

        Requirements: 7.4
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    "total_images": 0,
                    "storage_used": 0,
                    "storage_used_mb": 0.0,
                    "average_size": 0
                }

            # 统计图片数量
            total_images = db.query(Drawing).filter(
                Drawing.user_id == user_id,
                Drawing.file_size.isnot(None)
            ).count()

            # 获取存储使用量
            storage_used = user.storage_used or 0
            storage_used_mb = storage_used / (1024 * 1024)

            # 计算平均大小
            average_size = storage_used // total_images if total_images > 0 else 0

            return {
                "total_images": total_images,
                "storage_used": storage_used,
                "storage_used_mb": round(storage_used_mb, 2),
                "average_size": average_size
            }

        except Exception as e:
            logger.error(f"Failed to get user storage stats: {e}")
            raise

    @staticmethod
    def calculate_user_storage(
        user_id: int,
        db: Session
    ) -> int:
        """计算用户实际存储使用量（从 drawings 表统计）

        用于验证和修复 storage_used 字段。

        Args:
            user_id: 用户 ID
            db: 数据库会话

        Returns:
            实际存储使用量（字节）

        Requirements: 7.5
        """
        try:
            result = db.query(func.sum(Drawing.file_size)).filter(
                Drawing.user_id == user_id,
                Drawing.file_size.isnot(None)
            ).scalar()

            return result or 0

        except Exception as e:
            logger.error(f"Failed to calculate user storage: {e}")
            raise

    @staticmethod
    def sync_user_storage(
        user_id: int,
        db: Session
    ) -> Dict[str, int]:
        """同步用户存储使用量

        重新计算实际使用量并更新到 storage_used 字段。

        Args:
            user_id: 用户 ID
            db: 数据库会话

        Returns:
            {
                "old_storage": 旧的存储值,
                "new_storage": 新的存储值,
                "difference": 差异
            }
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return {"old_storage": 0, "new_storage": 0, "difference": 0}

            old_storage = user.storage_used or 0
            new_storage = StorageManager.calculate_user_storage(user_id, db)
            difference = new_storage - old_storage

            user.storage_used = new_storage
            db.commit()

            logger.info(
                f"User {user_id} storage synced: {old_storage} -> {new_storage} "
                f"(difference: {difference})"
            )

            return {
                "old_storage": old_storage,
                "new_storage": new_storage,
                "difference": difference
            }

        except Exception as e:
            logger.error(f"Failed to sync user storage: {e}")
            db.rollback()
            raise
