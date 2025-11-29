"""数据库与会话管理。

负责创建 SQLAlchemy Engine、配置连接池以及提供请求级别的 Session 依赖。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings
from sqlalchemy.pool import QueuePool

if settings.DB_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
else:
    engine = create_engine(
        settings.DB_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI 依赖：按请求提供数据库会话。

    使用 `yield` 以确保请求结束后安全关闭会话。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
