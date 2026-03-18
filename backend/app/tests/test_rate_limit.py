"""Rate limit 單元測試：超過 limit 時回 429、各 endpoint limit 正確。

依據 note.md 優先級：
- auth/login: 10/min
- register: 20/min
- checkin/verify: 60/min
- checkin/commit: 60/min
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.blueprints import auth as auth_bp
from app.services.checkin_service import checkin_service
from app.services.forms_service import forms_service
from app.services.supabase_client import supabase_client


# --- Auth helpers ---
def _fake_supabase_token(_email: str, _password: str) -> dict:
    return {"access_token": "fake", "user": {"id": "user-123"}}


# --- Register helpers (from test_register_route_unit) ---
class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return {"data": self.rows}


class _FakeClient:
    def __init__(self, ticket_type_rows):
        self.ticket_type_rows = ticket_type_rows

    def table(self, table_name: str):
        assert table_name == "ticket_types"
        return _FakeQuery(self.ticket_type_rows)


def test_auth_login_returns_429_over_limit(client, monkeypatch) -> None:
    """POST /auth/login：10/min，第 11 次應回 429。"""
    monkeypatch.setattr(auth_bp, "_supabase_token", _fake_supabase_token)

    for i in range(10):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "any"},
        )
        assert resp.status_code == 200, f"Request {i+1} expected 200, got {resp.status_code}"

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "any"},
    )
    assert resp.status_code == 429


def test_register_returns_429_over_limit(client, monkeypatch) -> None:
    """POST /events/<id>/register：20/min，第 21 次應回 429。"""
    event_id = "ff895f3f-dd7b-496c-a6ff-6c9d95de43e6"
    ticket_type_id = "34f9bc6e-bfdf-4668-a2a4-4e6ff2f3f0ce"
    user_id = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"
    jwt = "fake.jwt.token"

    monkeypatch.setattr(supabase_client, "get_user", lambda token: {"id": user_id})
    monkeypatch.setattr(
        supabase_client,
        "authed_client",
        lambda token: _FakeClient(
            [
                {
                    "id": ticket_type_id,
                    "event_id": event_id,
                    "price_cents": 0,
                    "is_active": True,
                }
            ]
        ),
    )
    monkeypatch.setattr(forms_service, "get_public_form", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        supabase_client,
        "call_rpc",
        MagicMock(
            return_value=[
                {
                    "id": "f5de9492-6fcb-49f8-bb27-a9ff728acbbf",
                    "event_id": event_id,
                    "ticket_type_id": ticket_type_id,
                    "user_id": user_id,
                    "status": "issued",
                    "qr_secret": "abcdef123456",
                    "issued_at": "2026-02-26T00:00:00+00:00",
                    "checked_in_at": None,
                }
            ]
        ),
    )

    for i in range(20):
        resp = client.post(
            f"/api/v1/events/{event_id}/register",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"ticket_type_id": ticket_type_id, "quantity": 1},
        )
        assert resp.status_code == 200, f"Request {i+1} expected 200, got {resp.status_code}"

    resp = client.post(
        f"/api/v1/events/{event_id}/register",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"ticket_type_id": ticket_type_id, "quantity": 1},
    )
    assert resp.status_code == 429


def test_checkin_verify_returns_429_over_limit(client, monkeypatch) -> None:
    """POST /organizer/events/<id>/checkin/verify：60/min，第 61 次應回 429。"""
    event_id = "ff895f3f-dd7b-496c-a6ff-6c9d95de43e6"
    jwt = "fake.jwt.token"

    monkeypatch.setattr(supabase_client, "get_user", lambda token: {"id": "org-user"})
    monkeypatch.setattr(
        checkin_service,
        "verify_ticket_qr",
        MagicMock(return_value={"ticket_id": "t1", "status": "verified"}),
    )

    for i in range(60):
        resp = client.post(
            f"/api/v1/organizer/events/{event_id}/checkin/verify",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "ticket_id": "f5de9492-6fcb-49f8-bb27-a9ff728acbbf",
                "qr_secret": "abcdef123456",
            },
        )
        assert resp.status_code == 200, f"Request {i+1} expected 200, got {resp.status_code}"

    resp = client.post(
        f"/api/v1/organizer/events/{event_id}/checkin/verify",
        headers={"Authorization": f"Bearer {jwt}"},
        json={
            "ticket_id": "f5de9492-6fcb-49f8-bb27-a9ff728acbbf",
            "qr_secret": "abcdef123456",
        },
    )
    assert resp.status_code == 429


def test_checkin_commit_returns_429_over_limit(client, monkeypatch) -> None:
    """POST /organizer/events/<id>/checkin/commit：60/min，第 61 次應回 429。"""
    event_id = "ff895f3f-dd7b-496c-a6ff-6c9d95de43e6"
    jwt = "fake.jwt.token"

    monkeypatch.setattr(supabase_client, "get_user", lambda token: {"id": "org-user"})
    monkeypatch.setattr(
        checkin_service,
        "commit_checkin",
        MagicMock(return_value={"ticket_id": "t1", "status": "checked_in"}),
    )

    for i in range(60):
        resp = client.post(
            f"/api/v1/organizer/events/{event_id}/checkin/commit",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "ticket_id": "f5de9492-6fcb-49f8-bb27-a9ff728acbbf",
                "qr_secret": "abcdef123456",
            },
        )
        assert resp.status_code == 200, f"Request {i+1} expected 200, got {resp.status_code}"

    resp = client.post(
        f"/api/v1/organizer/events/{event_id}/checkin/commit",
        headers={"Authorization": f"Bearer {jwt}"},
        json={
            "ticket_id": "f5de9492-6fcb-49f8-bb27-a9ff728acbbf",
            "qr_secret": "abcdef123456",
        },
    )
    assert resp.status_code == 429
