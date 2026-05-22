import base64
import random
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional


_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


@dataclass
class _CaptchaEntry:
    code: str
    expire_at: int
    attempts: int


class CaptchaService:
    def __init__(self, *, ttl_seconds: int = 120, max_attempts: int = 5):
        self._store: Dict[str, _CaptchaEntry] = {}
        self._ttl_seconds = ttl_seconds
        self._max_attempts = max_attempts

    def _now(self) -> int:
        return int(time.time())

    def _purge_expired(self) -> None:
        now = self._now()
        expired_keys = [k for k, v in self._store.items() if now > v.expire_at]
        for k in expired_keys:
            self._store.pop(k, None)

    def _random_code(self, length: int) -> str:
        return "".join(random.choice(_ALPHABET) for _ in range(length))

    def _render_svg(self, code: str, *, width: int = 120, height: int = 40) -> str:
        random.seed(f"{code}:{self._now()}")
        char_gap = width / (len(code) + 1)
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        ]

        for _ in range(6):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            color = random.choice(["#e5e7eb", "#d1d5db", "#cbd5e1"])
            parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1"/>')

        for i, ch in enumerate(code):
            x = int((i + 1) * char_gap)
            y = int(height * 0.68)
            angle = random.randint(-18, 18)
            color = random.choice(["#111827", "#1f2937", "#374151"])
            parts.append(
                f'<text x="{x}" y="{y}" fill="{color}" font-size="22" font-family="Arial, sans-serif" font-weight="700" text-anchor="middle" transform="rotate({angle} {x} {y})">{ch}</text>'
            )

        parts.append("</svg>")
        return "".join(parts)

    def create(self, *, length: int = 4) -> dict:
        self._purge_expired()
        captcha_id = uuid.uuid4().hex
        code = self._random_code(length)
        expire_at = self._now() + self._ttl_seconds
        self._store[captcha_id] = _CaptchaEntry(code=code, expire_at=expire_at, attempts=0)

        svg = self._render_svg(code)
        data_url = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return {"captchaId": captcha_id, "image": data_url}

    def verify(self, captcha_id: Optional[str], answer: str) -> bool:
        self._purge_expired()
        if not captcha_id:
            return False
        entry = self._store.get(captcha_id)
        if not entry:
            return False
        if self._now() > entry.expire_at:
            self._store.pop(captcha_id, None)
            return False
        if entry.attempts >= self._max_attempts:
            self._store.pop(captcha_id, None)
            return False
        entry.attempts += 1
        if (answer or "").strip().upper() == entry.code:
            self._store.pop(captcha_id, None)
            return True
        return False


captcha_service = CaptchaService()
