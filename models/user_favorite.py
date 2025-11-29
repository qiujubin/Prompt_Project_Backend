from sqlalchemy import Column, BigInteger, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class UserFavorite(Base):
    """用户收藏关系。

    对应表：`user_favorites`
    复合主键：`user_id + keyword_id`，表示用户收藏某个关键词。
    """
    __tablename__ = "user_favorites"
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    keyword_id = Column(BigInteger, ForeignKey("prompt_keywords.id"), primary_key=True)
    favorited_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

