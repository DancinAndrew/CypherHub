"""MVP-3.1: 主辦方成員細權限。staff 不可建立/編輯活動、票種、表單。"""

from __future__ import annotations

from unittest.mock import patch

from app.services.supabase_client import supabase_client


def test_staff_cannot_create_event(client, monkeypatch) -> None:
    """staff 建立活動應得 403 STAFF_CANNOT_MANAGE。"""
    user_id = "staff-user-123"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": user_id})

    with patch(
        "app.services.events_service.EventsService._get_org_role",
        return_value="staff",
    ):
        resp = client.post(
            "/api/v1/organizer/events",
            headers={"Authorization": f"Bearer {user_id}"},
            json={
                "org_id": "00000000-0000-0000-0000-000000000001",
                "title": "Test Event",
                "start_at": "2025-06-01T10:00:00Z",
                "end_at": "2025-06-01T12:00:00Z",
            },
        )

    assert resp.status_code == 403
    assert resp.get_json().get("error", {}).get("code") == "STAFF_CANNOT_MANAGE"


def test_staff_cannot_create_ticket_type(client, monkeypatch) -> None:
    """staff 建立票種應得 403 STAFF_CANNOT_MANAGE。"""
    from app.domain.errors import AppError
    from app.services.events_service import events_service

    user_id = "staff-user-456"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": user_id})

    def _raise_staff(*_args, **_kwargs):
        raise AppError(
            code="STAFF_CANNOT_MANAGE",
            message="Staff role cannot create or edit events.",
            http_status=403,
        )

    monkeypatch.setattr(events_service, "require_event_admin", _raise_staff)

    resp = client.post(
        "/api/v1/organizer/events/00000000-0000-0000-0000-000000000002/ticket-types",
        headers={"Authorization": f"Bearer {user_id}"},
        json={
            "name": "VIP",
            "capacity": 10,
            "per_user_limit": 2,
            "price_cents": 500,
        },
    )

    assert resp.status_code == 403
    assert resp.get_json().get("error", {}).get("code") == "STAFF_CANNOT_MANAGE"


def test_list_org_members_requires_admin(client, monkeypatch) -> None:
    """非 owner/admin 呼叫 GET /organizations/:id/members 應得 403。"""
    user_id = "staff-user-789"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": user_id})

    with patch(
        "app.services.events_service.EventsService._get_org_role",
        return_value="staff",
    ):
        resp = client.get(
            "/api/v1/organizer/organizations/00000000-0000-0000-0000-000000000001/members",
            headers={"Authorization": f"Bearer {user_id}"},
        )

    assert resp.status_code == 403
    assert resp.get_json().get("error", {}).get("code") == "STAFF_CANNOT_MANAGE"
