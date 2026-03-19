"""MVP-3.3: 結算與提款。 settlements、payout-requests API 單元測試。"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.domain.errors import AppError
from app.services.supabase_client import supabase_client


def test_admin_settlements_generate_requires_admin(client, app, monkeypatch) -> None:
    """POST /admin/settlements/generate 需 Admin。"""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": "random-user"})
    app.config["ADMIN_ALLOWLIST"] = {"admin-123"}

    resp = client.post(
        "/api/v1/admin/settlements/generate",
        headers={"Authorization": "Bearer fake.jwt"},
        json={
            "period_start": "2025-01-01T00:00:00Z",
            "period_end": "2025-01-31T23:59:59Z",
        },
    )
    assert resp.status_code == 403


def test_admin_settlements_generate_success(client, app, monkeypatch) -> None:
    """Admin 產生結算批次回傳 settlements。"""
    admin_id = "admin-456"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}
    app.config["PLATFORM_FEE_RATE"] = 0.05

    with patch(
        "app.services.settlement_service.settlement_service.generate_settlements",
        return_value=[
            {
                "id": "s1-uuid",
                "org_id": "org-uuid",
                "period_start": "2025-01-01T00:00:00",
                "period_end": "2025-01-31T23:59:59",
                "gross_cents": 10000,
                "platform_fee_cents": 500,
                "net_cents": 9500,
                "status": "finalized",
            }
        ],
    ):
        resp = client.post(
            "/api/v1/admin/settlements/generate",
            headers={"Authorization": f"Bearer {admin_id}"},
            json={
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-31T23:59:59Z",
            },
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "settlements" in data
    assert data["count"] == 1
    assert data["settlements"][0]["gross_cents"] == 10000
    assert data["settlements"][0]["platform_fee_cents"] == 500


def test_organizer_settlements_requires_auth(client) -> None:
    """GET /organizer/settlements 需登入。"""
    resp = client.get("/api/v1/organizer/settlements")
    assert resp.status_code == 401


def test_organizer_settlements_success(client, monkeypatch) -> None:
    """主辦方可取得自己結算列表。"""
    user_id = "org-user-1"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": user_id})

    with patch(
        "app.services.settlement_service.settlement_service.list_settlements_for_org",
        return_value=[
            {
                "id": "s1",
                "org_id": "org1",
                "period_start": "2025-01-01",
                "period_end": "2025-01-31",
                "gross_cents": 5000,
                "platform_fee_cents": 250,
                "net_cents": 4750,
                "status": "finalized",
            }
        ],
    ):
        resp = client.get(
            "/api/v1/organizer/settlements",
            headers={"Authorization": f"Bearer {user_id}"},
        )

    assert resp.status_code == 200
    assert resp.get_json()["items"][0]["net_cents"] == 4750


def test_organizer_payout_requires_auth(client) -> None:
    """POST /organizer/payout-requests 需登入。"""
    resp = client.post(
        "/api/v1/organizer/payout-requests",
        json={"org_id": "00000000-0000-0000-0000-000000000001", "amount_cents": 1000},
    )
    assert resp.status_code == 401


def test_organizer_payout_amount_validation(client, monkeypatch) -> None:
    """amount_cents 必須大於 0。"""
    user_id = "org-user-2"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": user_id})

    with patch(
        "app.services.settlement_service.settlement_service.create_payout_request"
    ) as m:
        m.side_effect = AppError(
            code="VALIDATION_ERROR",
            message="amount_cents must be positive",
            http_status=400,
        )
        resp = client.post(
            "/api/v1/organizer/payout-requests",
            headers={"Authorization": f"Bearer {user_id}"},
            json={
                "org_id": "00000000-0000-0000-0000-000000000001",
                "amount_cents": 0,
            },
        )

    assert resp.status_code == 400


def test_organizer_payout_insufficient_balance(client, monkeypatch) -> None:
    """餘額不足應得 400 INSUFFICIENT_BALANCE。"""
    user_id = "org-user-3"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": user_id})

    with patch(
        "app.services.settlement_service.settlement_service.create_payout_request"
    ) as m:
        m.side_effect = AppError(
            code="INSUFFICIENT_BALANCE",
            message="Available balance is insufficient",
            details={"amount_cents": 10000, "balance_cents": 500},
            http_status=400,
        )
        resp = client.post(
            "/api/v1/organizer/payout-requests",
            headers={"Authorization": f"Bearer {user_id}"},
            json={
                "org_id": "00000000-0000-0000-0000-000000000001",
                "amount_cents": 10000,
            },
        )

    assert resp.status_code == 400
    assert resp.get_json().get("error", {}).get("code") == "INSUFFICIENT_BALANCE"


def test_organizer_payout_success(client, monkeypatch) -> None:
    """提款申請成功回傳 201。"""
    user_id = "org-user-4"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": user_id})

    with patch(
        "app.services.settlement_service.settlement_service.create_payout_request"
    ) as m:
        m.return_value = {
                "id": "00000000-0000-0000-0000-000000000099",
                "org_id": "00000000-0000-0000-0000-000000000001",
            "amount_cents": 5000,
            "status": "requested",
        }
        resp = client.post(
            "/api/v1/organizer/payout-requests",
            headers={"Authorization": f"Bearer {user_id}"},
            json={
                "org_id": "00000000-0000-0000-0000-000000000001",
                "amount_cents": 5000,
            },
        )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["payout_request"]["status"] == "requested"
    assert data["payout_request"]["amount_cents"] == 5000


def test_admin_payout_list_requires_admin(client, monkeypatch) -> None:
    """GET /admin/payout-requests 需 Admin。"""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": "random"})
    resp = client.get(
        "/api/v1/admin/payout-requests",
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 403


def test_admin_payout_list_success(client, app, monkeypatch) -> None:
    """Admin 可取得提款列表。"""
    admin_id = "admin-789"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}

    with patch(
        "app.services.settlement_service.settlement_service.list_payout_requests_admin",
        return_value=[
            {
                "id": "pr1",
                "org_id": "org1",
                "amount_cents": 3000,
                "status": "requested",
            }
        ],
    ):
        resp = client.get(
            "/api/v1/admin/payout-requests",
            headers={"Authorization": f"Bearer {admin_id}"},
        )

    assert resp.status_code == 200
    assert len(resp.get_json()["items"]) == 1


def test_admin_payout_approve_requires_admin(client, monkeypatch) -> None:
    """PATCH /admin/payout-requests/:id approve 需 Admin。"""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": "random"})
    resp = client.patch(
        "/api/v1/admin/payout-requests/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": "Bearer fake"},
        json={"action": "approve"},
    )
    assert resp.status_code == 403


def test_admin_payout_approve_success(client, app, monkeypatch) -> None:
    """Admin 核准提款。"""
    admin_id = "admin-999"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}

    with patch(
        "app.services.settlement_service.settlement_service.approve_payout_request"
    ) as m:
        m.return_value = {
            "id": "pr-uuid",
            "org_id": "org1",
            "amount_cents": 2000,
            "status": "paid",
            "processed_at": "2025-01-15T10:00:00Z",
        }
        resp = client.patch(
            "/api/v1/admin/payout-requests/00000000-0000-0000-0000-000000000001",
            headers={"Authorization": f"Bearer {admin_id}"},
            json={"action": "approve"},
        )

    assert resp.status_code == 200
    assert resp.get_json()["payout_request"]["status"] == "paid"


def test_admin_payout_reject_success(client, app, monkeypatch) -> None:
    """Admin 退件提款。"""
    admin_id = "admin-reject"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}

    with patch(
        "app.services.settlement_service.settlement_service.reject_payout_request"
    ) as m:
        m.return_value = {
            "id": "pr-uuid",
            "status": "failed",
            "failure_reason": "資料不符",
        }
        resp = client.patch(
            "/api/v1/admin/payout-requests/00000000-0000-0000-0000-000000000001",
            headers={"Authorization": f"Bearer {admin_id}"},
            json={"action": "reject", "failure_reason": "資料不符"},
        )

    assert resp.status_code == 200
    assert resp.get_json()["payout_request"]["status"] == "failed"
    assert resp.get_json()["payout_request"]["failure_reason"] == "資料不符"


def test_admin_payout_not_found(client, app, monkeypatch) -> None:
    """不存在的 payout_id 應得 404。"""
    admin_id = "admin-404"
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": admin_id})
    app.config["ADMIN_ALLOWLIST"] = {admin_id}

    with patch(
        "app.services.settlement_service.settlement_service.approve_payout_request"
    ) as m:
        m.side_effect = AppError(
            code="PAYOUT_NOT_FOUND",
            message="Payout request not found",
            http_status=404,
        )
        resp = client.patch(
            "/api/v1/admin/payout-requests/00000000-0000-0000-0000-000000000999",
            headers={"Authorization": f"Bearer {admin_id}"},
            json={"action": "approve"},
        )

    assert resp.status_code == 404


# --- Integration: 需 Supabase ---


def _settlement_integration_env() -> bool:
    import os

    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def _settlement_integration_user_configured() -> bool:
    import os

    return bool(os.getenv("TEST_USER_EMAIL") and os.getenv("TEST_USER_PASSWORD"))


@pytest.mark.integration
@pytest.mark.skipif(
    not _settlement_integration_env(),
    reason="SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required",
)
@pytest.mark.skipif(
    not _settlement_integration_user_configured(),
    reason="TEST_USER_EMAIL + TEST_USER_PASSWORD required (owner_user_id must exist in auth.users)",
)
def test_generate_settlements_integration(app) -> None:
    """
    真實 Supabase：seed paid order + order_items，產生結算，驗證 settlements + ledger。
    需 TEST_USER_* 以取得存在於 auth.users 的 user_id（organizations trigger 會寫入 organizer_members）。
    """
    import os
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from app.services.settlement_service import settlement_service

    with app.app_context():
        sr = supabase_client.service_role_client()
        anon = supabase_client.public_client()
        sign_in = anon.auth.sign_in_with_password({
            "email": os.environ["TEST_USER_EMAIL"],
            "password": os.environ["TEST_USER_PASSWORD"],
        })
        user_id = None
        if hasattr(sign_in, "user") and sign_in.user:
            u = sign_in.user
            user_id = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
        if not user_id:
            pytest.skip("Could not obtain user_id from TEST_USER_*")

        user_id = str(user_id)
        org_id = str(uuid4())
        event_id = str(uuid4())
        ticket_type_id = str(uuid4())
        order_id = str(uuid4())
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=1)
        period_end = now + timedelta(days=1)

        try:
            sr.table("organizations").insert({
                "id": org_id,
                "name": "Settlement Integration Org",
                "owner_user_id": user_id,
                "approval_status": "approved",
            }).execute()

            sr.table("events").insert({
                "id": event_id,
                "org_id": org_id,
                "title": "Settlement Test Event",
                "start_at": now.isoformat(),
                "end_at": (now + timedelta(hours=2)).isoformat(),
                "status": "published",
                "published_at": now.isoformat(),
                "created_by": user_id,
            }).execute()

            sr.table("ticket_types").insert({
                "id": ticket_type_id,
                "event_id": event_id,
                "name": "Paid",
                "price_cents": 500,
                "capacity": 10,
                "sold_count": 1,
                "per_user_limit": 2,
                "is_active": True,
            }).execute()

            sr.table("orders").insert({
                "id": order_id,
                "user_id": user_id,
                "status": "issued",
                "total_cents": 500,
                "updated_at": now.isoformat(),
            }).execute()

            sr.table("order_items").insert({
                "order_id": order_id,
                "ticket_type_id": ticket_type_id,
                "quantity": 1,
                "price_cents": 500,
            }).execute()

            app.config["PLATFORM_FEE_RATE"] = 0.05
            results = settlement_service.generate_settlements(
                period_start, period_end, admin_user_id=None
            )

            assert len(results) >= 1
            s = next((r for r in results if r.get("org_id") == org_id), None)
            assert s is not None
            assert s["gross_cents"] == 500
            assert s["platform_fee_cents"] == 25
            assert s["net_cents"] == 475
            assert s["status"] == "finalized"

            ledger = sr.table("ledger_entries").select("type,amount_cents").eq("org_id", org_id).execute()
            rows = getattr(ledger, "data", None) or []
            types = {r["type"] for r in rows}
            assert "sale" in types
            assert "platform_fee" in types
        finally:
            sr.table("ledger_entries").delete().eq("org_id", org_id).execute()
            sr.table("settlements").delete().eq("org_id", org_id).execute()
            sr.table("order_items").delete().eq("order_id", order_id).execute()
            sr.table("orders").delete().eq("id", order_id).execute()
            sr.table("ticket_types").delete().eq("id", ticket_type_id).execute()
            sr.table("events").delete().eq("id", event_id).execute()
            sr.table("organizations").delete().eq("id", org_id).execute()
