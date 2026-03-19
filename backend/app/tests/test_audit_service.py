"""MVP-3.4: audit_service 寫入 audit_logs。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.audit_service import audit_service


@pytest.fixture
def mock_sr():
    """Mock service_role_client 與 table().insert().execute()。"""
    mock_execute = MagicMock()
    mock_insert = MagicMock(return_value=MagicMock(execute=mock_execute))
    mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))
    mock_sr = MagicMock(table=mock_table)
    return mock_sr, mock_insert


def test_log_inserts_correct_row(app, mock_sr) -> None:
    """log() 寫入正確結構至 audit_logs。"""
    mock_sr_client, mock_insert = mock_sr

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr_client,
        ):
            audit_service.log(
                actor_type="admin",
                actor_id="admin-1",
                action="refund",
                resource_type="order",
                resource_id="00000000-0000-0000-0000-000000000001",
                details={"amount_cents": 100},
            )

    mock_insert.assert_called_once()
    row = mock_insert.call_args[0][0]
    assert row["actor_type"] == "admin"
    assert row["actor_id"] == "admin-1"
    assert row["action"] == "refund"
    assert row["resource_type"] == "order"
    assert row["resource_id"] == "00000000-0000-0000-0000-000000000001"
    assert row["details"] == {"amount_cents": 100}


def test_log_resource_id_none(app, mock_sr) -> None:
    """log() 可接受 resource_id=None（如 settlement_generate）。"""
    mock_sr_client, mock_insert = mock_sr

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr_client,
        ):
            audit_service.log(
                actor_type="admin",
                actor_id="admin-1",
                action="settlement_generate",
                resource_type="settlement",
                resource_id=None,
                details={"period_start": "2025-01-01", "period_end": "2025-01-31", "count": 2},
            )

    row = mock_insert.call_args[0][0]
    assert row["resource_id"] is None
    assert row["details"]["count"] == 2


def test_log_refund(app, mock_sr) -> None:
    """log_refund 傳遞正確參數。"""
    mock_sr_client, mock_insert = mock_sr
    order_id = uuid4()

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr_client,
        ):
            audit_service.log_refund(order_id, "admin-2", 5000)

    row = mock_insert.call_args[0][0]
    assert row["action"] == "refund"
    assert row["resource_type"] == "order"
    assert row["resource_id"] == str(order_id)
    assert row["details"]["amount_cents"] == 5000


def test_log_comp_ticket(app, mock_sr) -> None:
    """log_comp_ticket 傳遞 event_id、ticket_type_id、recipient。"""
    mock_sr_client, mock_insert = mock_sr
    ticket_id = uuid4()
    event_id = uuid4()
    tt_id = uuid4()

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr_client,
        ):
            audit_service.log_comp_ticket(
                ticket_id=ticket_id,
                event_id=event_id,
                ticket_type_id=tt_id,
                recipient_user_id="user-xyz",
                actor_type="organizer",
                actor_id="org-1",
                note="VIP 嘉賓",
            )

    row = mock_insert.call_args[0][0]
    assert row["action"] == "comp_ticket"
    assert row["resource_type"] == "ticket"
    assert row["details"]["event_id"] == str(event_id)
    assert row["details"]["ticket_type_id"] == str(tt_id)
    assert row["details"]["recipient_user_id"] == "user-xyz"
    assert row["details"]["note"] == "VIP 嘉賓"


def test_log_unpublish(app, mock_sr) -> None:
    """log_unpublish 傳遞 event_id、status。"""
    mock_sr_client, mock_insert = mock_sr
    event_id = uuid4()

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr_client,
        ):
            audit_service.log_unpublish(event_id, "admin-3", "disabled")

    row = mock_insert.call_args[0][0]
    assert row["action"] == "unpublish"
    assert row["resource_type"] == "event"
    assert row["details"]["status"] == "disabled"


def test_log_payout_approve(app, mock_sr) -> None:
    """log_payout_approve 傳遞 payout_id、org_id、amount_cents。"""
    mock_sr_client, mock_insert = mock_sr
    payout_id = uuid4()

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr_client,
        ):
            audit_service.log_payout_approve(
                payout_id, "admin-4", "00000000-0000-0000-0000-000000000001", 8000
            )

    row = mock_insert.call_args[0][0]
    assert row["action"] == "payout_approve"
    assert row["resource_type"] == "payout_request"
    assert row["resource_id"] == str(payout_id)
    assert row["details"]["org_id"] == "00000000-0000-0000-0000-000000000001"
    assert row["details"]["amount_cents"] == 8000


def test_log_payout_reject(app, mock_sr) -> None:
    """log_payout_reject 傳遞 failure_reason。"""
    mock_sr_client, mock_insert = mock_sr
    payout_id = uuid4()

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr_client,
        ):
            audit_service.log_payout_reject(payout_id, "admin-5", "帳戶資訊不符")

    row = mock_insert.call_args[0][0]
    assert row["action"] == "payout_reject"
    assert row["details"]["failure_reason"] == "帳戶資訊不符"


def test_log_settlement_generate(app, mock_sr) -> None:
    """log_settlement_generate 傳遞 period、count，resource_id 為 None。"""
    mock_sr_client, mock_insert = mock_sr

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr_client,
        ):
            audit_service.log_settlement_generate(
                "admin-6", "2025-01-01T00:00:00", "2025-01-31T23:59:59", 3
            )

    row = mock_insert.call_args[0][0]
    assert row["action"] == "settlement_generate"
    assert row["resource_type"] == "settlement"
    assert row["resource_id"] is None
    assert row["details"]["period_start"] == "2025-01-01T00:00:00"
    assert row["details"]["period_end"] == "2025-01-31T23:59:59"
    assert row["details"]["count"] == 3


def test_log_failure_does_not_raise(app) -> None:
    """log() 失敗時不拋錯，僅 log warning。"""
    mock_sr = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock(return_value=MagicMock())
    mock_insert.return_value.execute.side_effect = Exception("DB error")
    mock_table.return_value.insert = mock_insert
    mock_sr.table = MagicMock(return_value=mock_table)

    with app.app_context():
        with patch(
            "app.services.audit_service.supabase_client.service_role_client",
            return_value=mock_sr,
        ):
            audit_service.log(
                actor_type="system",
                actor_id=None,
                action="test",
                resource_type="test",
                resource_id=None,
                details={},
            )
    # 不應 raise，執行到這裡即通過
