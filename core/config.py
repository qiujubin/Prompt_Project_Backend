"""核心配置模块。

通过环境变量加载项目所需配置项，例如数据库连接串、JWT 算法、
验证码策略与跨域来源等。
"""
import os

class Settings:
    """项目配置对象。

    属性说明：
    - SECRET_KEY: JWT 加密密钥
    - ACCESS_TOKEN_EXPIRE_MINUTES: 访问令牌过期分钟数
    - ALGORITHM: JWT 算法名称
    - DB_URL: 数据库连接串（默认使用 PostgreSQL）
    - CORS_ORIGINS: 允许跨域的前端来源列表
    - WECHAT_APPID/WECHAT_SECRET: 微信开放平台配置
    - VERIFICATION_CODE_*: 验证码过期/重试/重发限制
    """
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    DB_URL = os.getenv("DB_URL", "postgresql+psycopg://postgres:123456@localhost/graduation")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    WECHAT_APPID = os.getenv("WECHAT_APPID", "")
    WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")
    # 验证码配置
    VERIFICATION_CODE_EXPIRE_SECONDS = int(os.getenv("VERIFICATION_CODE_EXPIRE_SECONDS", "300"))
    VERIFICATION_CODE_MAX_ATTEMPTS = int(os.getenv("VERIFICATION_CODE_MAX_ATTEMPTS", "5"))
    VERIFICATION_CODE_RESEND_INTERVAL = int(os.getenv("VERIFICATION_CODE_RESEND_INTERVAL", "60"))

    # AI 配置
    COMFYUI_HOST = os.getenv("COMFYUI_HOST", "127.0.0.1:8188")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_API_URL = os.getenv("AI_API_URL", "https://api.openai.com/v1")

settings = Settings()

# Safety check for production
if settings.SECRET_KEY == "dev-secret":
    print("WARNING: You are using the default SECRET_KEY. Please change it in production.")
