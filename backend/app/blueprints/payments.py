"""MVP-2 付款 API. develop.md 2.2.1."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.domain.errors import AppError
from app.extensions import rate_limiter
from app.services.auth_service import require_auth
from app.services.payment_service import payment_service

from ._utils import parse_uuid

bp = Blueprint("payments", __name__, url_prefix="/api/v1/payments")


@bp.post("/checkout")
@rate_limiter.limit("30 per minute")
@require_auth
def create_checkout() -> tuple[dict, int]:
    """
    為 holding 訂單建立 ECPay 付款。
    Body: { "order_id": "uuid" }
    回傳 form_params、cashier_url 供前端 POST 導向綠界金流頁。
    """
    body = request.get_json(silent=True) or {}
    order_id_str = body.get("order_id")
    if not order_id_str:
        raise AppError(code="ORDER_ID_REQUIRED", message="order_id is required", http_status=400)
    order_id = parse_uuid(str(order_id_str), "order_id")
    data = payment_service.create_checkout(g.jwt, order_id)
    return jsonify(data), 200
