from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, BigInteger, Integer, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from database import Base

class SearchLog(Base):
    """搜索日志模型。

    对应表：`search_logs`
    记录用户的搜索行为，用于搜索优化和分析。
    """
    __tablename__ = "search_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    query = Column(Text, nullable=False)
    filters = Column(JSON, nullable=True)  # 过滤条件
    result_count = Column(Integer, default=0)
    clicked_results = Column(JSON, nullable=True)  # 点击的结果ID列表
    session_id = Column(String(64), nullable=True, index=True)  # 会话标识
    ip_address = Column(String(45), nullable=True)  # IP地址
    user_agent = Column(Text, nullable=True)  # 用户代理
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 关联关系
    user = relationship("User", back_populates="search_logs")

class ContentFeature(Base):
    """内容特征模型。

    对应表：`content_features`
    存储内容的各种特征信息，用于相似度计算和推荐。
    """
    __tablename__ = "content_features"

    content_id = Column(BigInteger, ForeignKey("drawings.id"), primary_key=True)
    feature_vector = Column(JSON, nullable=True)  # 存储特征向量
    dominant_colors = Column(JSON, nullable=True)  # 主色调信息
    style_scores = Column(JSON, nullable=True)  # 各种风格的得分
    complexity_score = Column(Float, nullable=True)  # 复杂度评分
    visual_features = Column(JSON, nullable=True)  # 视觉特征
    text_features = Column(JSON, nullable=True)  # 文本特征
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关联关系
    content = relationship("Drawing", back_populates="features")
