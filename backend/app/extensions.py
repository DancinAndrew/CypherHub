from __future__ import annotations

from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .services.supabase_client import supabase_client


def _default_limits_exempt_options() -> bool:
    """CORS preflight 不應佔用額度，否則瀏覽器每次 GET 會送 OPTIONS+GET 兩次。"""
    return request.method == "OPTIONS"


class MailStub:
    def __init__(self) -> None:
        self.initialized = False

    def init_app(self, _: Flask) -> None:
        self.initialized = True


mail = MailStub()
rate_limiter = Limiter(
    key_func=get_remote_address,
    # 公開 GET（活動列表等）需可頻繁篩選；敏感路由另用 @limit 加緊（auth/register/checkin）
    default_limits=["5000 per day", "500 per hour"],
    storage_uri="memory://",
    default_limits_exempt_when=_default_limits_exempt_options,
)


def init_extensions(app: Flask) -> None:
    supabase_client.init_app(app)
    mail.init_app(app)
    rate_limiter.init_app(app)
