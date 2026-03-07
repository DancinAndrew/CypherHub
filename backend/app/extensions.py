from __future__ import annotations

from flask import Flask

from .services.supabase_client import supabase_client


class MailStub:
    def __init__(self) -> None:
        self.initialized = False

    def init_app(self, _: Flask) -> None:
        self.initialized = True


class RateLimiterStub:
    def __init__(self) -> None:
        self.initialized = False

    def init_app(self, _: Flask) -> None:
        self.initialized = True


mail = MailStub()
rate_limiter = RateLimiterStub()


def init_extensions(app: Flask) -> None:
    supabase_client.init_app(app)
    mail.init_app(app)
    rate_limiter.init_app(app)
