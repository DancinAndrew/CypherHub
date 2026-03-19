"""訂單狀態機。develop.md 2.2.2。

允許轉換：
- created → holding
- holding → pending_payment | cancelled
- pending_payment → paid | cancelled
- paid → issued | refunded（僅 paid 可轉 issued）
- issued → refunded（未來）
- cancelled, refunded 為終態
"""

from __future__ import annotations

from types import SimpleNamespace

from .errors import AppError

# develop.md 2.2.2 定義的狀態
ORDER_STATUSES = frozenset(
    {
        "created",
        "holding",
        "pending_payment",
        "paid",
        "issued",
        "cancelled",
        "refunded",
    }
)

# (from_status, to_status) 允許的轉換
ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("created", "holding"),
        ("holding", "pending_payment"),
        ("holding", "cancelled"),
        ("pending_payment", "paid"),
        ("pending_payment", "cancelled"),
        ("paid", "issued"),  # 僅 paid 可轉 issued（Done 條件）
        ("paid", "refunded"),
        ("issued", "refunded"),
    }
)


def can_transition(from_status: str, to_status: str) -> bool:
    """檢查是否允許從 from_status 轉至 to_status。"""
    return (from_status, to_status) in ALLOWED_TRANSITIONS


def validate_transition(from_status: str, to_status: str) -> None:
    """若轉換不允許則 raise AppError。"""
    if from_status == to_status:
        return
    if not can_transition(from_status, to_status):
        raise AppError(
            code="INVALID_ORDER_STATUS_TRANSITION",
            message=f"Invalid order status transition: {from_status} → {to_status}",
            http_status=409,
        )


ORDER_STATE_MACHINE = SimpleNamespace(
    can_transition=can_transition,
    validate_transition=validate_transition,
)
