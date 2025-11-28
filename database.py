from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

if settings.DB_URL.startswith("sqlite"):
    engine = create_engine(settings.DB_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(settings.DB_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()