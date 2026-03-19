"""Admin 退款 API 測試。develop.md MVP-2.6。"""

from __future__ import annotations

from unittest.mock import patch

from app.domain.errors import AppError
from app.services.supabase_client import supabase_client


def test_refund_order_requires_admin(client, app, monkeypatch) -> None:
    """POST /admin/orders/<id>/refund 需 Admin 身分。"""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": "random-user"})
    app.config["ADMIN_ALLOWLIST"] = {"admin-id"}

    resp = client.post(
        "/api/v1/admin/orders/00000000-0000-0000-0000-000000000001/refund",
        headers={"Authorization": "Bearer fake.jwt"},
    )
    assert resp.status_code == 403


def test_refund_order_success(client, app, monkeypatch) -> None:
    """Admin 退款成功，回傳 refund_id、status。"""
    admin_id = "admin-user-123"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}

    with patch("app.blueprints.admin.create_refund") as m:
        m.return_value = {"refund_id": "r1", "status": "refunded", "message": "1|OK"}
        resp = client.post(
            "/api/v1/admin/orders/00000000-0000-0000-0000-000000000001/refund",
            headers={"Authorization": f"Bearer {admin_id}"},
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["refund_id"] == "r1"
    assert data["status"] == "refunded"


def test_refund_order_app_error(client, app, monkeypatch) -> None:
    """create_refund 拋出 AppError 時回傳對應 http_status。"""
    admin_id = "admin-user-123"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}

    with patch("app.blueprints.admin.create_refund") as m:
        m.side_effect = AppError(
            code="REFUND_NOT_SUPPORTED",
            message="Non-credit-card",
            http_status=400,
        )
        resp = client.post(
            "/api/v1/admin/orders/00000000-0000-0000-0000-000000000001/refund",
            headers={"Authorization": f"Bearer {admin_id}"},
        )

    assert resp.status_code == 400
