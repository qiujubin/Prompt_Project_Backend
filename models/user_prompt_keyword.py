from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func, text
from database import Base

class UserPromptKeyword(Base):
    """用户提示词使用统计。

    对应表：`user_prompt_keywords`
    复合主键：`user_id + keyword_id`，记录使用次数及最后使用时间。
    """
    __tablename__ = "user_prompt_keywords"
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    keyword_id = Column(BigInteger, ForeignKey("prompt_keywords.id"), primary_key=True)
    used_count = Column(Integer, nullable=False, server_default=text("1"))
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    first_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

