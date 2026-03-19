"""訂單狀態機測試。develop.md 2.2.2。"""

from __future__ import annotations

import pytest

from app.domain.errors import AppError
from app.domain.order_state_machine import (
    ALLOWED_TRANSITIONS,
    ORDER_STATE_MACHINE,
    ORDER_STATUSES,
)


def test_order_statuses_matches_spec() -> None:
    """狀態集合符合 develop.md 2.2.2 規格。"""
    expected = {
        "created",
        "holding",
        "pending_payment",
        "paid",
        "issued",
        "cancelled",
        "refunded",
    }
    assert ORDER_STATUSES == expected


def test_only_paid_can_transition_to_issued() -> None:
    """Done 條件：僅 paid 可轉 issued。"""
    assert ORDER_STATE_MACHINE.can_transition("paid", "issued") is True
    assert ORDER_STATE_MACHINE.can_transition("holding", "issued") is False
    assert ORDER_STATE_MACHINE.can_transition("pending_payment", "issued") is False
    assert ORDER_STATE_MACHINE.can_transition("issued", "issued") is False  # 同狀態不算
    assert ORDER_STATE_MACHINE.can_transition("cancelled", "issued") is False


def test_allowed_transitions() -> None:
    """規格內允許的轉換均可通過。"""
    for from_s, to_s in ALLOWED_TRANSITIONS:
        assert ORDER_STATE_MACHINE.can_transition(from_s, to_s), f"{from_s}→{to_s}"


def test_validate_same_status_no_raise() -> None:
    """同狀態不 raise。"""
    ORDER_STATE_MACHINE.validate_transition("holding", "holding")


def test_validate_invalid_transition_raises_app_error() -> None:
    """不允許的轉換 raise AppError。"""
    with pytest.raises(AppError) as exc_info:
        ORDER_STATE_MACHINE.validate_transition("holding", "issued")
    assert exc_info.value.code == "INVALID_ORDER_STATUS_TRANSITION"
    assert "holding" in exc_info.value.message and "issued" in exc_info.value.message
