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

from app import create_app  # noqa: E402
from app.services.supabase_client import supabase_client  # noqa: E402


@pytest.fixture()
def app():
    application = create_app({"TESTING": True})
    # 從 .env 寫入 app.config 並 re-init supabase_client（pytest 時 dotenv 可能晚於 Config）
    for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        if key in os.environ:
            application.config[key] = os.environ[key]
    supabase_client.init_app(application)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
