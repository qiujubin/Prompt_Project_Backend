from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from database import Base

class User(Base):
    """用户表模型。

    对应表：`users`
    常用字段：用户名、邮箱、头像、是否活跃、角色、注册来源等。
    """
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    nickname = Column(String(64), unique=True, index=True, nullable=True)
    email = Column(String(128), unique=True, index=True, nullable=True)
    hashed_password = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    role = Column(String(32), server_default=text("'user'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    full_name = Column(String(128), nullable=True)
    signature = Column(Text, nullable=True)
    phone = Column(String(32), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(64), nullable=True)
    credits = Column(BigInteger, default=100, server_default=text("100")) # 初始积分
    
    drawings = relationship("Drawing", back_populates="user")
    social_accounts = relationship("SocialAccount", back_populates="user")
    credit_logs = relationship("CreditLog", back_populates="user")

class SocialAccount(Base):
    """社交账号绑定模型。

    对应表：`social_accounts`
    记录微信等第三方账号的 openid、令牌与昵称信息。
    """
    __tablename__ = "social_accounts"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    openid = Column(Text, nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    nickname = Column(Text, nullable=True)
    unionid = Column(Text, nullable=True)
    user = relationship("User", back_populates="social_accounts")
