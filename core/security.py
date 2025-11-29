"""安全相关工具函数。

提供密码哈希与校验、JWT 令牌生成与解析。
"""
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """校验明文密码与哈希值是否匹配。"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """生成密码哈希（bcrypt）。"""
    return pwd_context.hash(password)

def create_access_token(data, expires_minutes=None):
    """生成带过期时间的 JWT 访问令牌。"""
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {**data, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token):
    """解析并验证 JWT 令牌，返回 payload。"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
