import os

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    DB_URL = os.getenv("DB_URL", "sqlite:///./backend.db")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    WECHAT_APPID = os.getenv("WECHAT_APPID", "")
    WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")

settings = Settings()