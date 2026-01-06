from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, BigInteger, Integer, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from database import Base

class UserPreference(Base):
    """用户偏好模型。

    对应表：`user_preferences`
    存储用户的兴趣偏好和权重信息，用于个性化推荐。
    """
    __tablename__ = "user_preferences"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    preference_type = Column(String(50), nullable=False, index=True)  # tag, style, color, creator
    preference_value = Column(String(200), nullable=False)
    weight = Column(Float, default=1.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关联关系
    user = relationship("User", back_populates="preferences")

class UserInteraction(Base):
    """用户交互行为模型。

    对应表：`user_interactions`
    记录用户与内容的各种交互行为，用于分析用户偏好。
    """
    __tablename__ = "user_interactions"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(BigInteger, ForeignKey("drawings.id"), nullable=False, index=True)
    interaction_type = Column(String(20), nullable=False, index=True)  # view, like, favorite, comment, share
    duration = Column(Integer, nullable=True)  # 浏览时长（秒）
    extra_data = Column(JSON, nullable=True)  # 额外的交互数据
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 关联关系
    user = relationship("User", back_populates="interactions")
    content = relationship("Drawing", back_populates="interactions")
