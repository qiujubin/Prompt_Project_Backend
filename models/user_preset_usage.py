"""用户预设使用统计模型。

对应表：`user_preset_usage`
存储用户对预设的使用统计信息，包括使用次数和最后使用时间。
"""
from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from database import Base


class UserPresetUsage(Base):
    """用户预设使用统计表模型。

    对应表：`user_preset_usage`
    复合主键：`user_id + preset_id`，记录用户对特定预设的使用统计。

    字段说明：
    - user_id: 用户ID，外键关联 users 表，复合主键之一
    - preset_id: 预设ID，外键关联 prompt_presets 表，复合主键之一，级联删除
    - used_count: 使用次数统计
    - last_used_at: 最后使用时间

    Requirements: 1.6, 1.7, 9.1, 9.2
    - 1.6: THE Preset_System SHALL support preset usage_count for global popularity tracking
    - 1.7: THE Preset_System SHALL support user-specific preset usage tracking
    - 9.1: THE Preset_System SHALL track global usage_count for each preset
    - 9.2: THE Preset_System SHALL track user-specific usage_count for each preset
    """
    __tablename__ = "user_preset_usage"

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
    used_count = Column(Integer, default=0, server_default=text("0"), nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # 关系定义
    user = relationship("User")
    preset = relationship("PromptPreset", back_populates="user_usages")
