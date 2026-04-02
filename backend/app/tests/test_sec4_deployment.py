"""SEC-4: Secrets 與部署檢查測試。

驗證項目：
- 生產環境 error response 不含 details.raw（防洩露 Supabase 內部資訊）
- 開發環境 error response 保留 details.raw（方便除錯）
- 500 error 不含 stack trace
- 生產環境啟動時驗證必要環境變數
- 開發環境可正常啟動（空 config）
"""

from __future__ import annotations

import pytest

from app import create_app
from app.domain.errors import AppError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(**overrides):
    """建立具有指定 config 的測試 app。"""
    config = {"TESTING": True, **overrides}
    return create_app(config)


def _production_config(**overrides):
    """回傳最小可啟動的生產環境 config。"""
    base = {
        "TESTING": True,
        "APP_ENV": "production",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "fake-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "fake-service-role-key",
        "CRON_SECRET": "fake-cron-secret",
        "FLASK_DEBUG": False,
        "CORS_ORIGINS": ["https://example.com"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Error response: details.raw 洩露防護
# ---------------------------------------------------------------------------


def test_error_details_raw_hidden_in_production() -> None:
    """APP_ENV=production 時，AppError 的 details.raw 不在 response 中。"""
    app = _make_app(
        APP_ENV="production",
        CORS_ORIGINS=["https://example.com"],
        SUPABASE_URL="https://x.supabase.co",
        SUPABASE_ANON_KEY="k",
        SUPABASE_SERVICE_ROLE_KEY="k",
        CRON_SECRET="s",
        FLASK_DEBUG=False,
    )

    @app.get("/test-error")
    def trigger():
        raise AppError(
            code="TEST_ERROR",
            message="Something failed",
            details={"raw": "permission denied for function foo (RLS)"},
            http_status=403,
        )

    with app.test_client() as c:
        resp = c.get("/test-error")
        data = resp.get_json()
        assert resp.status_code == 403
        assert data["error"]["code"] == "TEST_ERROR"
        details = data["error"]["details"]
        # raw 應被移除
        assert details is None or "raw" not in details


def test_error_details_raw_visible_in_development() -> None:
    """開發環境（非 production）details.raw 應保留，方便除錯。"""
    app = _make_app(APP_ENV="development")

    @app.get("/test-error")
    def trigger():
        raise AppError(
            code="TEST_ERROR",
            message="Something failed",
            details={"raw": "internal db error info"},
            http_status=400,
        )

    with app.test_client() as c:
        resp = c.get("/test-error")
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["details"]["raw"] == "internal db error info"


def test_error_details_non_raw_preserved_in_production() -> None:
    """生產環境中，details 裡非 raw 的欄位應保留。"""
    app = _make_app(
        APP_ENV="production",
        CORS_ORIGINS=["https://example.com"],
        SUPABASE_URL="https://x.supabase.co",
        SUPABASE_ANON_KEY="k",
        SUPABASE_SERVICE_ROLE_KEY="k",
        CRON_SECRET="s",
        FLASK_DEBUG=False,
    )

    @app.get("/test-error")
    def trigger():
        raise AppError(
            code="TEST_ERROR",
            message="fail",
            details={"raw": "secret stuff", "field": "email"},
            http_status=400,
        )

    with app.test_client() as c:
        resp = c.get("/test-error")
        data = resp.get_json()
        assert data["error"]["details"] == {"field": "email"}


# ---------------------------------------------------------------------------
# 500 error: no stack trace
# ---------------------------------------------------------------------------


def test_500_no_stack_trace() -> None:
    """未捕獲例外回傳通用訊息，不含 stack trace 或路徑。"""
    app = _make_app()

    @app.get("/test-crash")
    def trigger():
        raise RuntimeError("unexpected internal failure with /secret/path")

    with app.test_client() as c:
        resp = c.get("/test-crash")
        data = resp.get_json()
        assert resp.status_code == 500
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert data["error"]["message"] == "Unexpected server error"
        # 不應包含任何內部細節
        assert "unexpected internal failure" not in str(data)
        assert "/secret/path" not in str(data)


# ---------------------------------------------------------------------------
# 生產環境 env var 檢查
# ---------------------------------------------------------------------------


def test_production_requires_supabase_url() -> None:
    """生產缺少 SUPABASE_URL → ValueError。"""
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        _make_app(**_production_config(SUPABASE_URL=""))


def test_production_requires_anon_key() -> None:
    """生產缺少 SUPABASE_ANON_KEY → ValueError。"""
    with pytest.raises(ValueError, match="SUPABASE_ANON_KEY"):
        _make_app(**_production_config(SUPABASE_ANON_KEY=""))


def test_production_requires_service_role_key() -> None:
    """生產缺少 SUPABASE_SERVICE_ROLE_KEY → ValueError。"""
    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
        _make_app(**_production_config(SUPABASE_SERVICE_ROLE_KEY=""))


def test_production_rejects_flask_debug() -> None:
    """生產 FLASK_DEBUG=True → ValueError。"""
    with pytest.raises(ValueError, match="FLASK_DEBUG"):
        _make_app(**_production_config(FLASK_DEBUG=True))


def test_production_requires_cron_secret() -> None:
    """生產缺少 CRON_SECRET → ValueError。"""
    with pytest.raises(ValueError, match="CRON_SECRET"):
        _make_app(**_production_config(CRON_SECRET=""))


def test_development_allows_empty_config() -> None:
    """開發環境空 config 可正常啟動，不拋出 ValueError。"""
    app = _make_app(APP_ENV="development")
    assert app is not None


def test_production_valid_config_starts_ok() -> None:
    """生產環境設定完整時可正常啟動。"""
    app = _make_app(**_production_config())
    assert app is not None
