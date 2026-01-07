"""用户预设收藏模型。

对应表：`user_preset_favorites`
存储用户对预设的收藏关系。
"""
from sqlalchemy import Column, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class UserPresetFavorite(Base):
    """用户预设收藏表模型。

    对应表：`user_preset_favorites`
    复合主键：`user_id + preset_id`，表示用户收藏某个预设。

    字段说明：
    - user_id: 用户ID，外键关联 users 表，复合主键之一
    - preset_id: 预设ID，外键关联 prompt_presets 表，复合主键之一，级联删除
    - favorited_at: 收藏时间

    Requirements: 8.1, 8.2
    - 8.1: THE Preset_System SHALL allow logged-in users to favorite any preset
    - 8.2: WHEN a user favorites a preset, THE Preset_System SHALL store the favorite relationship in the database
    """
    __tablename__ = "user_preset_favorites"

    user_id = Column(
        BigInteger,
        ForeignKey("users.id"),
        primary_key=True
    )
    preset_id = Column(
        BigInteger,
        ForeignKey("prompt_presets.id", ondelete="CASCADE"),
        primary_key=True
    )
    favorited_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 关系定义
    user = relationship("User")
    preset = relationship("PromptPreset", back_populates="user_favorites")
