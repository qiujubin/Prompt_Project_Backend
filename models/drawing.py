from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, BigInteger, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from database import Base

class Drawing(Base):
    """绘图记录模型。

    对应表：`drawings`
    记录提示词、模型名称、生成图片、尺寸、耗时与公开状态等。
    新增社区字段：浏览量、点赞数、收藏数、评论数。
    """
    __tablename__ = "drawings"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    prompt = Column(Text, nullable=False)
    model_name = Column(String(128), nullable=False)
    image_url = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, server_default=text("'pending'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    seed = Column(String(64), nullable=True)
    negative_prompt = Column(Text, nullable=True)
    ai_response_time_ms = Column(Integer, nullable=True)
    prompt_id = Column(String(64), nullable=True, index=True)  # 关联异步任务ID
    is_public = Column(Boolean, nullable=True, default=False)

    # 社区互动统计字段
    view_count = Column(Integer, default=0, server_default=text("0"))
    like_count = Column(Integer, default=0, server_default=text("0"))
    favorite_count = Column(Integer, default=0, server_default=text("0"))
    comment_count = Column(Integer, default=0, server_default=text("0"))

    # COS 存储相关字段
    cos_key = Column(String(512), nullable=True, index=True)  # COS 对象键
    thumbnail_url = Column(Text, nullable=True)  # 缩略图 URL
    thumbnail_key = Column(String(512), nullable=True)  # 缩略图对象键
    file_size = Column(BigInteger, nullable=True)  # 文件大小（字节）

    user = relationship("User", back_populates="drawings")
    comments = relationship("DrawingComment", back_populates="drawing", cascade="all, delete-orphan")
    content_tags = relationship("ContentTag", back_populates="content")
    interactions = relationship("UserInteraction", back_populates="content")
    features = relationship("ContentFeature", back_populates="content", uselist=False)
