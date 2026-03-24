"""MVP-3.2: 主辦方入駐審核。"""

from __future__ import annotations

from unittest.mock import patch

from app.services.supabase_client import supabase_client


def test_create_event_requires_org_approved(client, app, monkeypatch) -> None:
    """org approval_status 非 approved 時建立活動應得 403 ORG_NOT_APPROVED。"""
    from app.domain.errors import AppError

    user_id = "admin-user-123"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": user_id})

    with patch(
        "app.services.events_service.EventsService._get_org_role",
        return_value="admin",
    ):
        with patch("app.services.events_service.EventsService._require_org_approved") as mock_req:
            mock_req.side_effect = AppError(
                code="ORG_NOT_APPROVED",
                message="Organization approval required before creating events",
                http_status=403,
            )
            resp = client.post(
                "/api/v1/organizer/events",
                headers={"Authorization": f"Bearer {user_id}"},
                json={
                    "org_id": "00000000-0000-0000-0000-000000000001",
                    "title": "Test",
                    "start_at": "2025-06-01T10:00:00Z",
                    "end_at": "2025-06-01T12:00:00Z",
                },
            )

    assert resp.status_code == 403
    assert resp.get_json().get("error", {}).get("code") == "ORG_NOT_APPROVED"


def test_admin_approval_requires_admin(client, app, monkeypatch) -> None:
    """PATCH /admin/organizations/:id/approval 需 Admin。"""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": "random-user"})
    app.config["ADMIN_ALLOWLIST"] = {"admin-id"}

    resp = client.patch(
        "/api/v1/admin/organizations/00000000-0000-0000-0000-000000000001/approval",
        headers={"Authorization": "Bearer fake.jwt"},
        json={"status": "approved"},
    )
    assert resp.status_code == 403


def test_admin_approval_success(client, app, monkeypatch) -> None:
    """Admin 審核通過回傳 organization。"""
    admin_id = "admin-456"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}

    with patch(
        "app.services.events_service.events_service.admin_approve_organization"
    ) as mock_approve:
        mock_approve.return_value = {
            "id": "00000000-0000-0000-0000-000000000001",
            "name": "Test Org",
            "approval_status": "approved",
        }
        resp = client.patch(
            "/api/v1/admin/organizations/00000000-0000-0000-0000-000000000001/approval",
            headers={"Authorization": f"Bearer {admin_id}"},
            json={"status": "approved"},
        )

    assert resp.status_code == 200
    assert resp.get_json().get("organization", {}).get("approval_status") == "approved"
