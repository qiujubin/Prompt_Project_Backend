"""预设项模型。

对应表：`preset_items`
存储预设包含的提示词及其权重配置。
"""
from sqlalchemy import Column, BigInteger, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from database import Base


class PresetItem(Base):
    """预设项表模型。

    对应表：`preset_items`
    存储预设中包含的单个提示词及其权重配置。

    字段说明：
    - id: 主键
    - preset_id: 所属预设ID，外键关联 prompt_presets 表，级联删除
    - keyword_id: 关联的提示词ID，外键关联 prompt_keywords 表
    - weight: 提示词权重，范围 0.1-2.0，默认 1.0
    - sort_order: 排序顺序，默认 0
    """
    __tablename__ = "preset_items"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    preset_id = Column(
        BigInteger,
        ForeignKey("prompt_presets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    keyword_id = Column(
        BigInteger,
        ForeignKey("prompt_keywords.id"),
        nullable=False,
        index=True
    )
    weight = Column(Float, default=1.0, server_default=text("1.0"), nullable=False)
    sort_order = Column(Integer, default=0, server_default=text("0"), nullable=False)

    # 关系定义
    preset = relationship("PromptPreset", back_populates="items")
    keyword = relationship("PromptKeyword")
