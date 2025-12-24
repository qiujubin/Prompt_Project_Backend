from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base

class WeightLog(Base):
    """权重调整日志模型。

    对应表：`weight_logs`
    记录用户调整提示词权重的行为。
    """
    __tablename__ = "weight_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    keyword_id = Column(Integer, ForeignKey("prompt_keywords.id"), nullable=True) # 可以为空，如果是自定义词
    old_weight = Column(Float, nullable=True)
    new_weight = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
