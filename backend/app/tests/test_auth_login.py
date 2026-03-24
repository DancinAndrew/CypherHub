"""登入 API 測試：區分「後端邏輯正確」與「帳密在 Supabase 是否有效」。

- 單元：mock _supabase_token，驗證 200/400 與 response 形狀。
- 整合：直連 Supabase，用 TEST_USER_EMAIL / TEST_USER_PASSWORD。若過但真人仍 400 即帳密/環境問題。
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app.blueprints import auth as auth_bp
from app.domain.errors import AppError


# --- 單元：成功時回傳形狀 ---
def test_login_success_returns_200_and_session_shape(client, monkeypatch) -> None:
    """POST /auth/login 成功時 200，body 含 access_token、refresh_token（前端 setSession 用）。"""
    fake_session = {
        "access_token": "eyJ.fake.access",
        "refresh_token": "fake-refresh-token",
        "expires_in": 3600,
        "token_type": "bearer",
        "user": {"id": "user-123", "email": "test@example.com"},
    }

    monkeypatch.setattr(auth_bp, "_supabase_token", lambda _e, _p: fake_session)

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "Test@Example.com", "password": "secret123"},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert data.get("access_token") == "eyJ.fake.access"
    assert data.get("refresh_token") == "fake-refresh-token"


# --- 單元：帳密錯誤時 400 + AUTH_FAILED ---
def test_login_invalid_credentials_returns_400_auth_failed(client, monkeypatch) -> None:
    """帳密錯誤時後端回 400、error.code 為 AUTH_FAILED（前端顯示「帳號或密碼不正確」）。"""

    def raise_auth_failed(_email: str, _password: str) -> None:
        raise AppError(
            code="AUTH_FAILED",
            message="Invalid login credentials",
            http_status=400,
        )

    monkeypatch.setattr(auth_bp, "_supabase_token", raise_auth_failed)

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong"},
    )

    assert resp.status_code == 400
    body = resp.get_json()
    assert body is not None
    assert body.get("error", {}).get("code") == "AUTH_FAILED"
    err_msg = (body.get("error", {}).get("message") or "").lower()
    assert "credentials" in err_msg or "password" in err_msg


# --- 單元：請求體驗證 ---
def _fake_token_ok(_e: str, _p: str) -> dict:
    return {"access_token": "x", "refresh_token": "y"}


def test_login_missing_email_returns_400(client, monkeypatch) -> None:
    """缺少 email 應 400（parse_json / LoginRequest）。"""
    monkeypatch.setattr(auth_bp, "_supabase_token", _fake_token_ok)

    resp = client.post("/api/v1/auth/login", json={"password": "secret"})

    assert resp.status_code == 400


def test_login_missing_password_returns_400(client, monkeypatch) -> None:
    """缺少 password 應 400。"""
    monkeypatch.setattr(auth_bp, "_supabase_token", _fake_token_ok)

    resp = client.post("/api/v1/auth/login", json={"email": "a@b.com"})

    assert resp.status_code == 400


# --- 單元：blueprint 把 body 傳給 _supabase_token（normalize 在 _supabase_token 內）---
def test_login_passes_body_to_supabase_token(client) -> None:
    """Blueprint 將 body 原樣傳給 _supabase_token；strip 在 _supabase_token 內完成。"""
    captured = {}

    def capture_and_succeed(email: str, password: str):
        captured["email"] = email
        captured["password"] = password
        return {"access_token": "ok", "refresh_token": "ok"}

    with patch.object(auth_bp, "_supabase_token", side_effect=capture_and_succeed):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "  User@Example.COM  ", "password": "  pwd123  "},
        )

    assert resp.status_code == 200
    assert captured.get("email") == "  User@Example.COM  "
    assert captured.get("password") == "  pwd123  "


# --- 單元：_supabase_token 回傳形狀（改用 client 後仍含 access_token, refresh_token）---
def test_supabase_token_returns_session_shape(app) -> None:
    """_supabase_token 成功時回傳 dict 含 access_token、refresh_token。"""

    class FakeSession:
        access_token = "access"
        refresh_token = "refresh"
        expires_in = 3600
        token_type = "bearer"
        user = {"id": "u1"}

    def fake_sign_in(_creds):
        r = MagicMock()
        r.session = FakeSession()
        return r

    with app.test_request_context():
        app.config["SUPABASE_URL"] = "https://x.supabase.co"
        app.config["SUPABASE_ANON_KEY"] = "key"
        with patch.object(auth_bp.supabase_client, "public_client") as mock_pc:
            mock_client = MagicMock()
            mock_client.auth.sign_in_with_password = fake_sign_in
            mock_pc.return_value = mock_client
            out = auth_bp._supabase_token("  u@x.com  ", "  pwd  ")
    assert out["access_token"] == "access"
    assert out["refresh_token"] == "refresh"


# --- 整合：直連 Supabase，用環境變數的測試帳密 ---
def _login_integration_env_ready() -> bool:
    return bool(
        os.getenv("SUPABASE_URL")
        and os.getenv("SUPABASE_ANON_KEY")
        and os.getenv("TEST_USER_EMAIL")
        and os.getenv("TEST_USER_PASSWORD")
    )


@pytest.mark.integration
@pytest.mark.skipif(
    not _login_integration_env_ready(),
    reason="SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD required",
)
def test_login_integration_real_supabase(client) -> None:
    """用真實 Supabase 與 TEST_USER_* 呼叫 POST /auth/login。過=邏輯正常；不過=查 .env。"""
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": os.environ["TEST_USER_EMAIL"],
            "password": os.environ["TEST_USER_PASSWORD"],
        },
    )

    err_hint = "Check SUPABASE_* and TEST_USER_EMAIL/TEST_USER_PASSWORD in Supabase Auth."
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}. {err_hint}"
    data = resp.get_json()
    assert data is not None
    assert isinstance(data.get("access_token"), str) and len(data["access_token"]) > 0
    assert isinstance(data.get("refresh_token"), str) and len(data["refresh_token"]) > 0
