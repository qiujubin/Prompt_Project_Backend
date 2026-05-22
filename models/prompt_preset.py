"""预设模型。

对应表：`prompt_presets`
存储预设的基本信息，包括名称、所属分类、创建者、是否官方预设等。
"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from database import Base


class PromptPreset(Base):
    """预设主表模型。

    对应表：`prompt_presets`
    存储预设基本信息，支持官方预设和用户自定义预设两种类型。

    字段说明：
    - id: 主键
    - name: 预设英文名称
    - display_name: 预设中文显示名称
    - subcategory_id: 所属小分类ID
    - created_by: 创建者用户ID，NULL表示官方预设
    - is_official: 是否为官方预设
    - usage_count: 全局使用次数统计
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    __tablename__ = "prompt_presets"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    display_name = Column(String(256), nullable=False)
    subcategory_id = Column(BigInteger, ForeignKey("prompt_subcategories.id"), nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    is_official = Column(Boolean, default=False, server_default=text("false"), nullable=False)
    usage_count = Column(Integer, default=0, server_default=text("0"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # 关系定义
    creator = relationship("User", foreign_keys=[created_by])
    subcategory = relationship("PromptSubcategory", foreign_keys=[subcategory_id])
    items = relationship("PresetItem", back_populates="preset", cascade="all, delete-orphan")
    user_favorites = relationship("UserPresetFavorite", back_populates="preset", cascade="all, delete-orphan")
    user_usages = relationship("UserPresetUsage", back_populates="preset", cascade="all, delete-orphan")
