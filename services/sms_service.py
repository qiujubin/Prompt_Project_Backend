"""阿里云短信认证服务"""
import json
import uuid
from typing import Optional
from core.config import settings

class AliyunSMSVerifyService:
    """阿里云号码认证短信验证服务"""

    def __init__(self):
        self.access_key_id = settings.ALIYUN_ACCESS_KEY_ID
        self.access_key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        self.scheme_name = settings.SMS_SCHEME_NAME
        self.sign_name = settings.SMS_SIGN_NAME
        self.template_code = settings.SMS_TEMPLATE_CODE

    def send_sms_verify_code(self, phone_number: str) -> dict:
        """发送短信验证码

        Args:
            phone_number: 手机号码

        Returns:
            dict: 包含验证码和请求结果的字典
        """
        try:
            from alibabacloud_dypnsapi20170525.client import Client as DypnsapiClient
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_dypnsapi20170525 import models as dypnsapi_models
            from alibabacloud_tea_util import models as util_models

            # 创建配置
            config = open_api_models.Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret
            )
            config.endpoint = 'dypnsapi.aliyuncs.com'

            # 创建客户端
            client = DypnsapiClient(config)

            # 创建请求
            request = dypnsapi_models.SendSmsVerifyCodeRequest(
                scheme_name=self.scheme_name,
                country_code="86",
                phone_number=phone_number,
                sign_name=self.sign_name,
                template_code=self.template_code,
                template_param='{"code":"##code##","min":"5"}',  # 验证码占位符和有效期
                code_length=6,  # 6位验证码
                valid_time=300,  # 5分钟有效期
                duplicate_policy=1,  # 新验证码覆盖旧验证码
                interval=60,  # 60秒发送间隔
                code_type=1,  # 数字验证码
                return_verify_code=True,  # 返回验证码（测试环境）
                auto_retry=1  # 自动重试
            )

            # 发送请求
            runtime = util_models.RuntimeOptions()
            response = client.send_sms_verify_code_with_options(request, runtime)

            if response.body.code == "OK" and response.body.success:
                # 发送成功
                verify_code = response.body.model.verify_code if response.body.model else None
                return {
                    "success": True,
                    "verify_code": verify_code,
                    "request_id": response.body.request_id,
                    "message": "短信发送成功"
                }
            else:
                # 发送失败
                return {
                    "success": False,
                    "error_code": response.body.code,
                    "message": response.body.message or "短信发送失败",
                    "request_id": response.body.request_id
                }

        except Exception as e:
            print(f"❌ 阿里云短信发送异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "短信服务异常"
            }

    def get_error_message(self, error_code: str) -> str:
        """获取友好的错误提示"""
        error_messages = {
            "MOBILE_NUMBER_ILLEGAL": "手机号格式不正确",
            "BUSINESS_LIMIT_CONTROL": "今日发送次数已达上限",
            "FREQUENCY_FAIL": "发送过于频繁，请稍后再试",
            "INVALID_PARAMETERS": "参数无效",
            "FUNCTION_NOT_OPENED": "服务未开通，请先开通短信服务"
        }
        return error_messages.get(error_code, f"发送失败: {error_code}")

# 单例实例
sms_service = AliyunSMSVerifyService()
