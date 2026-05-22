from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class DrawingLike(Base):
    """绘图点赞记录。
    
    对应表: `drawing_likes`
    """
    __tablename__ = "drawing_likes"
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    drawing_id = Column(BigInteger, ForeignKey("drawings.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class DrawingFavorite(Base):
    """绘图收藏记录。
    
    对应表: `drawing_favorites`
    """
    __tablename__ = "drawing_favorites"
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    drawing_id = Column(BigInteger, ForeignKey("drawings.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class DrawingComment(Base):
    """绘图评论记录。
    
    对应表: `drawing_comments`
    """
    __tablename__ = "drawing_comments"
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    drawing_id = Column(BigInteger, ForeignKey("drawings.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("drawing_comments.id"), nullable=True)

    user = relationship("User")
    drawing = relationship("Drawing", back_populates="comments")
    # parent = relationship("DrawingComment", remote_side=[id])
