"""SEC-1: Security Headers 測試"""

from __future__ import annotations

import pytest

from app import create_app
from app.services.supabase_client import supabase_client


class TestSecurityHeaders:
    """所有回應必須包含安全 headers"""

    def test_x_content_type_options(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_cross_origin_opener_policy(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("Cross-Origin-Opener-Policy") == "same-origin"

    def test_no_server_header(self, client):
        resp = client.get("/api/v1/health")
        assert "Server" not in resp.headers

    def test_error_responses_include_security_headers(self, client):
        """404 回應也必須包含安全 headers"""
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_hsts_disabled_by_default(self, client):
        """預設不啟用 HSTS（開發環境）"""
        resp = client.get("/api/v1/health")
        assert "Strict-Transport-Security" not in resp.headers


class TestHSTS:
    """SEC-1: HSTS Header 測試"""

    @pytest.fixture()
    def hsts_app(self):
        app = create_app({"TESTING": True, "ENABLE_HSTS": True, "HSTS_MAX_AGE": 31536000})
        supabase_client.init_app(app)
        return app

    @pytest.fixture()
    def hsts_client(self, hsts_app):
        return hsts_app.test_client()

    def test_hsts_enabled(self, hsts_client):
        """ENABLE_HSTS=true 時回應包含 HSTS header"""
        resp = hsts_client.get("/api/v1/health")
        hsts = resp.headers.get("Strict-Transport-Security")
        assert hsts is not None
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts

    def test_hsts_custom_max_age(self):
        """自訂 HSTS_MAX_AGE"""
        app = create_app({"TESTING": True, "ENABLE_HSTS": True, "HSTS_MAX_AGE": 86400})
        supabase_client.init_app(app)
        with app.test_client() as c:
            resp = c.get("/api/v1/health")
            assert "max-age=86400" in resp.headers.get("Strict-Transport-Security", "")


class TestCORSSecurity:
    """SEC-1: CORS 設定安全測試"""

    def test_cors_wildcard_rejected_in_production(self):
        """生產環境不允許 CORS_ORIGINS='*'"""
        with pytest.raises(ValueError, match="禁止"):
            create_app({"TESTING": True, "APP_ENV": "production", "CORS_ORIGINS": ["*"]})

    def test_cors_wildcard_allowed_in_development(self):
        """開發環境允許 '*'（僅 warning）"""
        app = create_app({"TESTING": True, "APP_ENV": "development", "CORS_ORIGINS": ["*"]})
        assert app is not None

    def test_cors_rejects_unknown_origin(self, client):
        """不在白名單的 origin 不回傳 Access-Control-Allow-Origin"""
        resp = client.get("/api/v1/health", headers={"Origin": "https://evil.com"})
        assert resp.headers.get("Access-Control-Allow-Origin") != "https://evil.com"

    def test_cors_allows_configured_origin(self, client):
        """白名單內的 origin 正確回傳 CORS header"""
        resp = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"


class TestProductionURLValidation:
    """SEC-1: 生產環境 URL 安全檢查"""

    def test_localhost_supabase_rejected_in_production(self):
        """生產環境不允許 SUPABASE_URL 指向 localhost"""
        with pytest.raises(ValueError, match="localhost"):
            create_app(
                {
                    "TESTING": True,
                    "APP_ENV": "production",
                    "SUPABASE_URL": "http://localhost:54321",
                }
            )

    def test_http_supabase_rejected_in_production(self):
        """生產環境不允許 SUPABASE_URL 使用 HTTP"""
        with pytest.raises(ValueError, match="HTTPS"):
            create_app(
                {
                    "TESTING": True,
                    "APP_ENV": "production",
                    "SUPABASE_URL": "http://example.supabase.co",
                }
            )

    def test_https_supabase_allowed_in_production(self):
        """生產環境允許 HTTPS Supabase URL"""
        app = create_app(
            {
                "TESTING": True,
                "APP_ENV": "production",
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_ANON_KEY": "k",
                "SUPABASE_SERVICE_ROLE_KEY": "k",
                "CRON_SECRET": "s",
                "CORS_ORIGINS": ["https://example.com"],
            }
        )
        assert app is not None

    def test_localhost_allowed_in_development(self):
        """開發環境允許 localhost Supabase URL"""
        app = create_app(
            {
                "TESTING": True,
                "APP_ENV": "development",
                "SUPABASE_URL": "http://localhost:54321",
            }
        )
        assert app is not None
