from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, BigInteger, Integer, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from database import Base

class Tag(Base):
    """标签模型。

    对应表：`tags`
    用于对作品进行分类和标记，支持智能标签生成和分类管理。
    """
    __tablename__ = "tags"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # style, theme, technique, color
    usage_count = Column(Integer, default=0, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关联关系
    content_tags = relationship("ContentTag", back_populates="tag", cascade="all, delete-orphan")

class ContentTag(Base):
    """内容标签关联模型。

    对应表：`content_tags`
    记录作品与标签的多对多关系，包含置信度和来源信息。
    """
    __tablename__ = "content_tags"

    content_id = Column(BigInteger, ForeignKey("drawings.id"), primary_key=True)
    tag_id = Column(BigInteger, ForeignKey("tags.id"), primary_key=True)
    confidence = Column(Float, default=1.0)  # AI生成标签的置信度
    source = Column(String(20), default="manual")  # manual, auto, suggested
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 关联关系
    tag = relationship("Tag", back_populates="content_tags")
    content = relationship("Drawing", back_populates="content_tags")
