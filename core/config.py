"""核心配置模块。

通过环境变量加载项目所需配置项，例如数据库连接串、JWT 算法、
验证码策略与跨域来源等。
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

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
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    DB_URL = os.getenv("DB_URL", "postgresql+psycopg://postgres:123456@localhost/graduation")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    WECHAT_APPID = os.getenv("WECHAT_APPID", "")
    WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")
    # 验证码配置
    VERIFICATION_CODE_EXPIRE_SECONDS = int(os.getenv("VERIFICATION_CODE_EXPIRE_SECONDS", "300"))
    VERIFICATION_CODE_MAX_ATTEMPTS = int(os.getenv("VERIFICATION_CODE_MAX_ATTEMPTS", "5"))
    VERIFICATION_CODE_RESEND_INTERVAL = int(os.getenv("VERIFICATION_CODE_RESEND_INTERVAL", "60"))

    # SMTP 邮件配置
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")

    # 阿里云短信认证服务配置
    ALIYUN_ACCESS_KEY_ID = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
    ALIYUN_ACCESS_KEY_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")
    SMS_SCHEME_NAME = os.getenv("SMS_SCHEME_NAME", "默认方案")
    SMS_SIGN_NAME = os.getenv("SMS_SIGN_NAME", "速通互联验证码")  # 系统赠送签名
    SMS_TEMPLATE_CODE = os.getenv("SMS_TEMPLATE_CODE", "100001")  # 系统赠送模板

    # AI 配置
    COMFYUI_HOST = os.getenv("COMFYUI_HOST", "127.0.0.1:8188")

    # 外部 AI API 配置
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_API_URL = os.getenv("AI_API_URL", "https://api.openai.com/v1")

    # 通义千问配置
    TONGYI_API_KEY = os.getenv("TONGYI_API_KEY", "")
    TONGYI_API_URL = os.getenv("TONGYI_API_URL", "https://dashscope.aliyuncs.com/api/v1")

    # 百度文心一言配置
    BAIDU_AI_API_KEY = os.getenv("BAIDU_AI_API_KEY", "")
    BAIDU_AI_SECRET_KEY = os.getenv("BAIDU_AI_SECRET_KEY", "")
    BAIDU_AI_API_URL = os.getenv("BAIDU_AI_API_URL", "https://aip.baidubce.com")

    # 腾讯混元配置
    TENCENT_API_KEY = os.getenv("TENCENT_API_KEY", "")
    TENCENT_API_URL = os.getenv("TENCENT_API_URL", "https://hunyuan.tencentcloudapi.com")

    # DeepSeek Config
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

    # Baidu Translate Config
    BAIDU_TRANS_APPID = os.getenv("BAIDU_TRANS_APPID", "")
    BAIDU_TRANS_KEY = os.getenv("BAIDU_TRANS_KEY", "")

settings = Settings()

# Safety check for production
if settings.SECRET_KEY == "dev-secret":
    print("WARNING: You are using the default SECRET_KEY. Please change it in production.")
