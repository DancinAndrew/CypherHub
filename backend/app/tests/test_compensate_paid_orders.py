"""補償出票 API 測試。develop.md 2.3。"""

from __future__ import annotations

from unittest.mock import patch

from app.services.supabase_client import supabase_client


def test_compensate_paid_orders_requires_admin(client, app, monkeypatch) -> None:
    """POST /admin/compensate-paid-orders 需 Admin 身分。"""
    monkeypatch.setattr(
        supabase_client,
        "get_user",
        lambda _: {"id": "random-user"},
    )
    app.config["ADMIN_ALLOWLIST"] = {"admin-id"}

    resp = client.post(
        "/api/v1/admin/compensate-paid-orders",
        headers={"Authorization": "Bearer fake.jwt"},
    )
    assert resp.status_code == 403


def test_compensate_paid_orders_returns_count(client, app, monkeypatch) -> None:
    """Admin 觸發補償，回傳 orders_compensated。"""
    admin_id = "admin-user-123"
    monkeypatch.setattr(
        supabase_client,
        "get_user",
        lambda _: {"id": admin_id},
    )
    app.config["ADMIN_ALLOWLIST"] = {admin_id}

    with patch("app.blueprints.admin.run_compensate_paid_orders", return_value=3):
        resp = client.post(
            "/api/v1/admin/compensate-paid-orders",
            headers={"Authorization": f"Bearer {admin_id}"},
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["orders_compensated"] == 3
