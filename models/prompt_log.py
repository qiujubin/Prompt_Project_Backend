from sqlalchemy import Column, DateTime, ForeignKey, BigInteger, Numeric, Boolean
from sqlalchemy.sql import func
from database import Base

class PromptLog(Base):
    """提示词使用日志模型。

    对应表：`prompt_logs`
    记录用户在某次绘图的提示词选择、权重与是否为反向词等。
    """
    __tablename__ = "prompt_logs"
    id = Column(BigInteger, primary_key=True, index=True)
    prompt_id = Column(BigInteger, ForeignKey("prompt_keywords.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    small_category_id = Column(BigInteger, nullable=False)
    weight = Column(Numeric, nullable=False)
    is_navigate = Column(Boolean, nullable=True)
    drawing_id = Column(BigInteger, nullable=True)
