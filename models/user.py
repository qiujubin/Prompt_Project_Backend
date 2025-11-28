from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    drawings = relationship("Drawing", back_populates="user")
    social_accounts = relationship("SocialAccount", back_populates="user")

class SocialAccount(Base):
    __tablename__ = "social_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String(32), nullable=False)
    openid = Column(String(128), nullable=True)
    unionid = Column(String(128), nullable=True)
    user = relationship("User", back_populates="social_accounts")