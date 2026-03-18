"""MVP-2 orders API. develop.md 2.1.1, 2.1.2."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.domain.schemas import (
    CreateHoldOrderRequest,
    OrderDetailResponse,
    OrderItemResponse,
    OrderResponse,
    OrdersListResponse,
    PaymentResponse,
)
from app.services.auth_service import require_auth
from app.services.orders_service import orders_service

from ._utils import parse_uuid

bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


@bp.post("/")
@require_auth
def create_hold_order() -> tuple[dict, int]:
    """選票種 → 建立 holding 訂單，原子扣 hold_count。逾時 15 分鐘釋放。"""
    body = CreateHoldOrderRequest(**request.get_json(silent=True) or {})
    items = [{"ticket_type_id": i.ticket_type_id, "quantity": i.quantity} for i in body.items]
    order_id = orders_service.create_hold_order(
        g.jwt, items, hold_minutes=body.hold_minutes
    )
    data = orders_service.get_order_detail(g.jwt, order_id)
    payload = OrderDetailResponse(
        order=OrderResponse(**data["order"]),
        items=[OrderItemResponse(**i) for i in data["items"]],
        payments=[PaymentResponse(**p) for p in data["payments"]],
    )
    return jsonify(payload.model_dump(mode="json")), 201


@bp.get("/")
@require_auth
def list_orders() -> tuple[dict, int]:
    orders = orders_service.list_orders_for_user(g.jwt)
    items = [OrderResponse(**r) for r in orders]
    payload = OrdersListResponse(items=items)
    return jsonify(payload.model_dump(mode="json")), 200


@bp.delete("/<order_id>")
@require_auth
def cancel_order(order_id: str) -> tuple[dict, int]:
    """取消自己的 holding 訂單，釋放名額。"""
    order_uuid = parse_uuid(order_id, "order_id")
    orders_service.cancel_holding_order(g.jwt, order_uuid)
    return jsonify({"ok": True}), 200


@bp.get("/<order_id>")
@require_auth
def get_order(order_id: str) -> tuple[dict, int]:
    order_uuid = parse_uuid(order_id, "order_id")
    data = orders_service.get_order_detail(g.jwt, order_uuid)
    payload = OrderDetailResponse(
        order=OrderResponse(**data["order"]),
        items=[OrderItemResponse(**i) for i in data["items"]],
        payments=[PaymentResponse(**p) for p in data["payments"]],
    )
    return jsonify(payload.model_dump(mode="json")), 200
