from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Drawing(Base):
    __tablename__ = "drawings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    image_url = Column(String(256), nullable=True)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="drawings")