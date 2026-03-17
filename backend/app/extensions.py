from __future__ import annotations

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .services.supabase_client import supabase_client


class MailStub:
    def __init__(self) -> None:
        self.initialized = False

    def init_app(self, _: Flask) -> None:
        self.initialized = True


mail = MailStub()
rate_limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


def init_extensions(app: Flask) -> None:
    supabase_client.init_app(app)
    mail.init_app(app)
    rate_limiter.init_app(app)
