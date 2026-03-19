from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from app.domain.errors import AppError
from app.domain.schemas import AdminPatchEventRequest
from app.services.auth_service import require_auth
from app.services.compensation_service import run_compensate_paid_orders
from app.services.events_service import events_service
from app.services.hold_expiry_service import run_release_expired_holds
from app.services.refund_service import create_refund

from ._utils import parse_json, parse_uuid

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


def _ensure_admin() -> None:
    allowlist = current_app.config.get("ADMIN_ALLOWLIST", set())
    if not allowlist:
        raise AppError(
            code="FORBIDDEN",
            message="Admin allowlist required",
            http_status=403,
        )
    user_id = str(g.user_id) if g.user_id else ""
    user_email = (g.user or {}).get("email", "") if hasattr(g, "user") else ""
    if user_id not in allowlist and user_email not in allowlist:
        raise AppError(
            code="FORBIDDEN",
            message="Admin allowlist required",
            http_status=403,
        )


@bp.get("/events")
@require_auth
def list_admin_events_route() -> tuple[dict, int]:
    _ensure_admin()
    q = request.args.get("q")
    from_at = request.args.get("from")
    to_at = request.args.get("to")
    org_id = request.args.get("org_id")
    events = events_service.list_admin_events(q=q, from_at=from_at, to_at=to_at, org_id=org_id)
    return jsonify({"items": events}), 200


@bp.patch("/events/<event_id>")
@require_auth
def patch_admin_event(event_id: str) -> tuple[dict, int]:
    _ensure_admin()
    event_uuid = parse_uuid(event_id, "event_id")
    body = parse_json(AdminPatchEventRequest)
    event = events_service.admin_update_event_status(event_uuid, body.status)
    return jsonify({"event": event}), 200


@bp.post("/compensate-paid-orders")
@require_auth
def compensate_paid_orders_route() -> tuple[dict, int]:
    """手動觸發 paid → issued 補償。develop.md 2.3。"""
    _ensure_admin()
    count = run_compensate_paid_orders()
    return jsonify({"orders_compensated": count}), 200


@bp.post("/release-expired-holds")
@require_auth
def release_expired_holds_route() -> tuple[dict, int]:
    """手動觸發 hold 逾時釋放。develop.md 2.1.2。"""
    _ensure_admin()
    count = run_release_expired_holds()
    return jsonify({"orders_released": count}), 200


@bp.post("/orders/<order_id>/refund")
@require_auth
def refund_order_route(order_id: str) -> tuple[dict, int]:
    """發起訂單全額退款。develop.md MVP-2.6。"""
    _ensure_admin()
    order_uuid = parse_uuid(order_id, "order_id")
    result = create_refund(order_uuid)
    return jsonify(result), 200
