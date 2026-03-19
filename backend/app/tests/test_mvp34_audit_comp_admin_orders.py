"""MVP-3.4: 平台治理與 Audit、Comp 票、Admin 訂單 API 測試。"""

from __future__ import annotations

from unittest.mock import patch

from app.domain.errors import AppError
from app.services.supabase_client import supabase_client


def test_comp_ticket_requires_auth(client) -> None:
    """POST /organizer/events/:id/comp-ticket 需登入。"""
    resp = client.post(
        "/api/v1/organizer/events/00000000-0000-0000-0000-000000000001/comp-ticket",
        json={"ticket_type_id": "00000000-0000-0000-0000-000000000002", "email": "a@b.com"},
    )
    assert resp.status_code == 401


def test_comp_ticket_requires_event_admin(client, monkeypatch) -> None:
    """只有 event admin 可發 comp 票。"""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": "user-123"})
    with patch("app.services.events_service.events_service.create_comp_ticket") as m:
        m.side_effect = AppError(code="FORBIDDEN", message="Not event admin", http_status=403)
        resp = client.post(
            "/api/v1/organizer/events/00000000-0000-0000-0000-000000000001/comp-ticket",
            headers={"Authorization": "Bearer fake.jwt"},
            json={"ticket_type_id": "00000000-0000-0000-0000-000000000002", "email": "a@b.com"},
        )
    assert resp.status_code == 403


def test_comp_ticket_success(client, monkeypatch) -> None:
    """Comp 票成功回傳 ticket。"""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": "admin-user"})
    with patch("app.services.events_service.events_service.create_comp_ticket") as m:
        m.return_value = {
            "id": "ticket-uuid",
            "event_id": "ev-1",
            "ticket_type_id": "tt-1",
            "user_id": "recipient-1",
            "qr_secret": "secret",
            "status": "issued",
        }
        resp = client.post(
            "/api/v1/organizer/events/00000000-0000-0000-0000-000000000001/comp-ticket",
            headers={"Authorization": "Bearer fake.jwt"},
            json={"ticket_type_id": "00000000-0000-0000-0000-000000000002", "email": "a@b.com"},
        )
    assert resp.status_code == 201
    data = resp.get_json()
    assert "ticket" in data
    assert data["ticket"]["status"] == "issued"


def test_admin_orders_requires_admin(client, monkeypatch) -> None:
    """GET /admin/orders 需 Admin 身分。"""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": "random-user"})
    resp = client.get(
        "/api/v1/admin/orders",
        headers={"Authorization": "Bearer fake.jwt"},
    )
    assert resp.status_code == 403


def test_admin_orders_success(client, app, monkeypatch) -> None:
    """Admin 可查全站訂單。"""
    admin_id = "admin-123"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}
    with patch("app.services.orders_service.orders_service.list_admin_orders") as m:
        m.return_value = [
            {
                "order": {"id": "o1", "user_id": "u1", "status": "issued", "total_cents": 100},
                "items": [],
                "payments": [],
            }
        ]
        resp = client.get(
            "/api/v1/admin/orders",
            headers={"Authorization": f"Bearer {admin_id}"},
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["order"]["status"] == "issued"
