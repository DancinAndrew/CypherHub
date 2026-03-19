"""API 整合測試：未 mock，直連 Supabase。

依據 note.md 低優先級建議：選 1–2 個關鍵 public endpoint 做整合測試。
需 SUPABASE_URL、SUPABASE_ANON_KEY；POST /register 另需
SUPABASE_SERVICE_ROLE_KEY、TEST_USER_EMAIL、TEST_USER_PASSWORD。
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

UTC = getattr(datetime, "UTC", timezone(timedelta(0)))


def _supabase_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


def _register_integration_configured() -> bool:
    return _supabase_configured() and bool(
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        and os.getenv("TEST_USER_EMAIL")
        and os.getenv("TEST_USER_PASSWORD")
    )


@pytest.mark.integration
@pytest.mark.skipif(not _supabase_configured(), reason="SUPABASE_URL + SUPABASE_ANON_KEY required")
def test_get_events_integration(client) -> None:
    """GET /api/v1/events：未 mock，直連 Supabase。"""
    response = client.get("/api/v1/events")

    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.integration
@pytest.mark.skipif(
    not _register_integration_configured(),
    reason="SUPABASE_SERVICE_ROLE_KEY + TEST_USER_* required",
)
def test_post_register_integration(client, app) -> None:
    """POST /api/v1/events/<id>/register：未 mock，直連 Supabase + seed 資料。"""
    from app.services.supabase_client import supabase_client

    with app.app_context():
        sr = supabase_client.service_role_client()
        user_id: str | None = None
        jwt_token: str | None = None

        # 1. 登入取得 JWT
        anon = supabase_client.public_client()
        sign_in = anon.auth.sign_in_with_password(
            {
                "email": os.environ["TEST_USER_EMAIL"],
                "password": os.environ["TEST_USER_PASSWORD"],
            }
        )
        if hasattr(sign_in, "session") and sign_in.session:
            sess = sign_in.session
            jwt_token = getattr(sess, "access_token", None) or (
                sess.get("access_token") if isinstance(sess, dict) else None
            )
        if hasattr(sign_in, "user") and sign_in.user:
            user = sign_in.user
            user_id = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)

        if not jwt_token or not user_id:
            pytest.skip("Could not obtain JWT from test user")

        # 2. Seed: org -> event (published) -> ticket_type
        org_id = str(uuid4())
        event_id = str(uuid4())
        ticket_type_id = str(uuid4())
        now = datetime.now(UTC)
        start = now + timedelta(days=1)
        end = start + timedelta(hours=2)

        sr.table("organizations").insert(
            {
                "id": org_id,
                "name": "Integration Test Org",
                "owner_user_id": user_id,
            }
        ).execute()
        # organizer_members 由 organizations 的 trigger 自動寫入 owner 列，勿重複 insert

        sr.table("events").insert(
            {
                "id": event_id,
                "org_id": org_id,
                "title": "Integration Test Event",
                "start_at": start.isoformat(),
                "end_at": end.isoformat(),
                "status": "published",
                "published_at": now.isoformat(),
                "created_by": user_id,
            }
        ).execute()

        sr.table("ticket_types").insert(
            {
                "id": ticket_type_id,
                "event_id": event_id,
                "name": "Free",
                "price_cents": 0,
                "capacity": 10,
                "sold_count": 0,
                "per_user_limit": 2,
                "is_active": True,
            }
        ).execute()

        try:
            # 3. POST /register
            response = client.post(
                f"/api/v1/events/{event_id}/register",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"ticket_type_id": ticket_type_id, "quantity": 1},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data is not None
            assert "tickets" in data
            assert isinstance(data["tickets"], list)
            assert len(data["tickets"]) >= 1
            ticket = data["tickets"][0]
            assert "ticket_id" in ticket
            assert ticket.get("event_id") == event_id
            assert ticket.get("ticket_type_id") == ticket_type_id
        finally:
            # 4. 清理 seed 資料（逆序刪除避免 FK）
            sr.table("ticket_form_responses").delete().eq("event_id", event_id).execute()
            sr.table("tickets").delete().eq("event_id", event_id).execute()
            sr.table("ticket_types").delete().eq("id", ticket_type_id).execute()
            sr.table("events").delete().eq("id", event_id).execute()
            sr.table("organizer_members").delete().eq("org_id", org_id).execute()
            sr.table("organizations").delete().eq("id", org_id).execute()
