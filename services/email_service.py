"""邮件发送服务 - 使用 SMTP"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from core.config import settings

class SMTPEmailService:
    """SMTP 邮件服务"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM

    def send_verification_code(self, to_email: str, code: str) -> bool:
        """发送验证码邮件"""
        try:
            # 创建邮件对象
            message = MIMEMultipart('alternative')
            message['From'] = self.from_email  # 直接使用邮箱地址
            message['To'] = to_email
            message['Subject'] = Header('【AI绘图平台】验证码', 'utf-8')

            # HTML 邮件内容
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 10px;
                        padding: 40px;
                        text-align: center;
                    }}
                    .content {{
                        background: white;
                        border-radius: 8px;
                        padding: 30px;
                        margin-top: 20px;
                    }}
                    .code {{
                        font-size: 36px;
                        font-weight: bold;
                        color: #667eea;
                        letter-spacing: 8px;
                        margin: 20px 0;
                        font-family: 'Courier New', monospace;
                    }}
                    .title {{
                        color: white;
                        font-size: 24px;
                        margin: 0;
                    }}
                    .info {{
                        color: #666;
                        font-size: 14px;
                        margin-top: 20px;
                    }}
                    .footer {{
                        color: rgba(255,255,255,0.8);
                        font-size: 12px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="title">🎨 AI绘图平台</h1>
                    <div class="content">
                        <h2>您的验证码</h2>
                        <div class="code">{code}</div>
                        <div class="info">
                            <p>✅ 验证码有效期为 <strong>5分钟</strong></p>
                            <p>⚠️ 请勿将验证码告诉他人</p>
                            <p>💡 如果这不是您的操作，请忽略此邮件</p>
                        </div>
                    </div>
                    <div class="footer">
                        <p>此邮件由系统自动发送，请勿回复</p>
                        <p>© 2026 AI绘图平台 - 智能创作与社区分享</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # 纯文本内容（备用）
            text_content = f"""
            【AI绘图平台】验证码

            您的验证码是：{code}

            验证码有效期为5分钟，请尽快使用。
            如果这不是您的操作，请忽略此邮件。

            此邮件由系统自动发送，请勿回复。
            """

            # 添加邮件内容
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(text_part)
            message.attach(html_part)

            # 连接 SMTP 服务器并发送
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, message.as_string())

            print(f"✅ 邮件发送成功: {to_email}")
            return True

        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False

# 单例实例
email_service = SMTPEmailService()
