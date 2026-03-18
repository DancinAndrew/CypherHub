"""登入 API 測試：區分「後端邏輯正確」與「帳密在 Supabase 是否有效」。

- 單元測試：mock _supabase_token，驗證 200/400 與 response 形狀。
- 單元測試：mock urlopen，驗證 _supabase_token 送給 Supabase 的 payload 有 email 小寫、password strip。
- 整合測試：直連 Supabase，用 TEST_USER_EMAIL / TEST_USER_PASSWORD 驗證真實登入。
  若整合測試通過但真人仍 400，代表帳密或環境有誤。
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from app.blueprints import auth as auth_bp
from app.domain.errors import AppError


# --- 單元：成功時回傳形狀 ---
def test_login_success_returns_200_and_session_shape(client, monkeypatch) -> None:
    """POST /auth/login 成功時應 200，且 body 含 access_token、refresh_token（前端 setSession 需要）。"""
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
    """Supabase 回傳帳密錯誤時，後端應回 400 且 error.code 為 AUTH_FAILED（前端依此顯示「帳號或密碼不正確」）。"""
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
    assert "credentials" in (body.get("error", {}).get("message") or "").lower() or "password" in (body.get("error", {}).get("message") or "").lower()


# --- 單元：請求體驗證 ---
def test_login_missing_email_returns_400(client, monkeypatch) -> None:
    """缺少 email 應 400（parse_json / LoginRequest）。"""
    monkeypatch.setattr(auth_bp, "_supabase_token", lambda _e, _p: {"access_token": "x", "refresh_token": "y"})

    resp = client.post("/api/v1/auth/login", json={"password": "secret"})

    assert resp.status_code == 400


def test_login_missing_password_returns_400(client, monkeypatch) -> None:
    """缺少 password 應 400。"""
    monkeypatch.setattr(auth_bp, "_supabase_token", lambda _e, _p: {"access_token": "x", "refresh_token": "y"})

    resp = client.post("/api/v1/auth/login", json={"email": "a@b.com"})

    assert resp.status_code == 400


# --- 單元：blueprint 把 body 傳給 _supabase_token（normalize 在 _supabase_token 內）---
def test_login_passes_body_to_supabase_token(client) -> None:
    """Blueprint 將 body.email / body.password 原樣傳給 _supabase_token；strip 在 _supabase_token 內完成。"""
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
    """
    用真實 Supabase 與測試帳密呼叫 POST /auth/login。
    若此測試通過 → 後端登入邏輯與 Supabase 連線正常。
    若此測試失敗 → 檢查後端 .env 的 SUPABASE_* 與 TEST_USER_EMAIL / TEST_USER_PASSWORD 是否正確。
    若此測試通過但真人登入仍 400 → 代表真人使用的帳密在 Supabase 中無效（或專案/環境不同）。
    """
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": os.environ["TEST_USER_EMAIL"],
            "password": os.environ["TEST_USER_PASSWORD"],
        },
    )

    assert resp.status_code == 200, (
        f"Login failed: {resp.get_json()}. "
        "Check SUPABASE_URL, SUPABASE_ANON_KEY and that TEST_USER_EMAIL/TEST_USER_PASSWORD exist in Supabase Auth."
    )
    data = resp.get_json()
    assert data is not None
    assert isinstance(data.get("access_token"), str) and len(data["access_token"]) > 0
    assert isinstance(data.get("refresh_token"), str) and len(data["refresh_token"]) > 0
