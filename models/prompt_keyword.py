from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func, text
from database import Base

class PromptKeyword(Base):
    """提示词关键词模型。

    对应表：`prompt_keywords`
    存放具体提示词文本与其所属的小类、创建者等信息。
    """
    __tablename__ = "prompt_keywords"
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    word = Column(String(256), nullable=False)
    display_name = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    small_category_id = Column(BigInteger, ForeignKey("prompt_subcategories.id"), nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    usage_count = Column(Integer, default=0, server_default="0")
    is_hidden = Column(Integer, nullable=True, server_default=text("0"))

