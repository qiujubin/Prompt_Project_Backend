from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class CopyLog(Base):
    __tablename__ = "copy_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 类型：positive (正面), negative (负面)
    copy_type = Column(String(20), nullable=False, index=True)
    
    # 本次复制包含的词条数量
    item_count = Column(Integer, default=1)
    
    # 记录时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 预留字段：如果未来需要记录具体复制的内容摘要或ID列表
    # content_snapshot = Column(Text, nullable=True)
    
    # 关联
    user = relationship("User", backref="copy_logs")
