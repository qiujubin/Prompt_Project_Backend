from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text
from datetime import datetime
from database import Base

class PromptLog(Base):
    __tablename__ = "prompt_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)