import time
import random
from typing import Dict, Tuple
from core.config import settings

class CodeService:
    """验证码服务。

    负责生成与校验邮箱/短信验证码，支持过期、重发间隔与最大尝试次数限制。
    当前为内存实现，生产环境建议替换为缓存/数据库持久化。
    """

    def __init__(self):
        self._store: Dict[Tuple[str, str], dict] = {}

    def _now(self):
        """返回当前 UNIX 时间戳（秒）。"""
        return int(time.time())

    def generate(self, channel: str, account: str) -> str:
        """生成验证码并写入内存存储。

        参数：
        - channel: 验证渠道（email/sms）
        - account: 邮箱地址或手机号
        返回：验证码字符串
        """
        key = (channel, account)
        entry = self._store.get(key)
        now = self._now()
        if entry and now - entry["sent_at"] < settings.VERIFICATION_CODE_RESEND_INTERVAL:
            raise ValueError("发送过于频繁")
        code = f"{random.randint(100000, 999999)}"
        self._store[key] = {
            "code": code,
            "sent_at": now,
            "expire_at": now + settings.VERIFICATION_CODE_EXPIRE_SECONDS,
            "attempts": 0,
        }
        return code

    def verify(self, channel: str, account: str, code: str) -> bool:
        """校验验证码是否有效。

        包含过期、最大尝试次数控制。
        """
        key = (channel, account)
        entry = self._store.get(key)
        now = self._now()
        if not entry:
            return False
        if now > entry["expire_at"]:
            return False
        if entry["attempts"] >= settings.VERIFICATION_CODE_MAX_ATTEMPTS:
            return False
        entry["attempts"] += 1
        return entry["code"] == code

code_service = CodeService()

