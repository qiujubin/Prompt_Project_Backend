from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class CreditLog(Base):
    """积分变动记录表。
    
    记录用户积分的增加或消耗情况。
    """
    __tablename__ = "credit_logs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    change_amount = Column(Integer, nullable=False) # 变动数量，正数为增加，负数为消耗
    reason = Column(String(64), nullable=False) # 变动原因：daily_login, generation_cost, like_reward, recharge
    description = Column(String(255), nullable=True) # 详细描述
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    user = relationship("User", back_populates="credit_logs")
