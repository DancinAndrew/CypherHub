from __future__ import annotations

import os
from pathlib import Path

import pytest

# 讓 pytest 執行時能讀到 backend/.env（整合測試需要 TEST_USER_EMAIL 等）
_backend_root = Path(__file__).resolve().parent.parent.parent
_env_path = _backend_root / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from app import create_app
from app.services.supabase_client import supabase_client


@pytest.fixture()
def app():
    application = create_app({"TESTING": True})
    # 確保從 .env 讀到的變數會進 app.config，並讓 supabase_client 使用（pytest 時 dotenv 可能晚於 Config 載入）
    for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        if key in os.environ:
            application.config[key] = os.environ[key]
    supabase_client.init_app(application)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
