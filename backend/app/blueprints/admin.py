from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from app.blueprints._utils import require_auth
from app.domain.errors import AppError
from app.domain.schemas import (
    AdminOrganizationApprovalRequest,
    AdminPatchEventRequest,
    AdminPayoutActionRequest,
    CompTicketRequest,
    GenerateSettlementsRequest,
)
from app.extensions import rate_limiter
from app.services.compensation_service import run_compensate_paid_orders
from app.services.events_service import events_service
from app.services.hold_expiry_service import run_release_expired_holds
from app.services.orders_service import orders_service
from app.services.refund_service import create_refund
from app.services.settlement_service import settlement_service

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
    event = events_service.admin_update_event_status(
        event_uuid, body.status, admin_user_id=str(g.user_id)
    )
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


@bp.get("/orders")
@require_auth
def list_admin_orders_route() -> tuple[dict, int]:
    """Admin 全站訂單查詢。MVP-3.4。"""
    _ensure_admin()
    q = request.args.get("q")
    status = request.args.get("status")
    from_at = request.args.get("from")
    to_at = request.args.get("to")
    org_id = request.args.get("org_id")
    event_id = request.args.get("event_id")
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))
    rows = orders_service.list_admin_orders(
        q=q,
        status=status,
        from_at=from_at,
        to_at=to_at,
        org_id=org_id,
        event_id=event_id,
        limit=limit,
        offset=offset,
    )
    return jsonify({"items": rows}), 200


@bp.post("/orders/<order_id>/refund")
@rate_limiter.limit("10 per minute")
@require_auth
def refund_order_route(order_id: str) -> tuple[dict, int]:
    """發起訂單全額退款。develop.md MVP-2.6。"""
    _ensure_admin()
    order_uuid = parse_uuid(order_id, "order_id")
    result = create_refund(order_uuid, admin_user_id=str(g.user_id))
    return jsonify(result), 200


@bp.get("/organizations")
@require_auth
def list_admin_organizations_route() -> tuple[dict, int]:
    """Admin: 主辦方列表，可篩選 approval_status。MVP-3.2。"""
    _ensure_admin()
    status = request.args.get("status")  # pending | approved | rejected
    orgs = events_service.list_admin_organizations(status=status)
    return jsonify({"items": orgs}), 200


@bp.patch("/organizations/<org_id>/approval")
@rate_limiter.limit("10 per minute")
@require_auth
def patch_organization_approval_route(org_id: str) -> tuple[dict, int]:
    """Admin: 審核主辦方入駐。MVP-3.2。"""
    _ensure_admin()
    org_uuid = parse_uuid(org_id, "org_id")
    body = parse_json(AdminOrganizationApprovalRequest)
    org = events_service.admin_approve_organization(
        org_uuid,
        status=body.status,
        admin_user_id=str(g.user_id),
        rejection_reason=body.rejection_reason,
    )
    return jsonify({"organization": org}), 200


@bp.post("/settlements/generate")
@rate_limiter.limit("5 per minute")
@require_auth
def generate_settlements_route() -> tuple[dict, int]:
    """Admin: 產生結算批次。MVP-3.3。"""
    _ensure_admin()
    body = parse_json(GenerateSettlementsRequest)
    results = settlement_service.generate_settlements(
        body.period_start,
        body.period_end,
        admin_user_id=str(g.user_id),
    )
    return jsonify({"settlements": results, "count": len(results)}), 200


@bp.get("/payout-requests")
@require_auth
def list_payout_requests_route() -> tuple[dict, int]:
    """Admin: 提款申請列表。MVP-3.3。"""
    _ensure_admin()
    status = request.args.get("status")
    rows = settlement_service.list_payout_requests_admin(status=status)
    return jsonify({"items": rows}), 200


@bp.patch("/payout-requests/<payout_id>")
@rate_limiter.limit("10 per minute")
@require_auth
def patch_payout_request_route(payout_id: str) -> tuple[dict, int]:
    """Admin: 核准或退件提款。MVP-3.3。"""
    _ensure_admin()
    pid = parse_uuid(payout_id, "payout_id")
    body = parse_json(AdminPayoutActionRequest)
    if body.action == "approve":
        row = settlement_service.approve_payout_request(pid, str(g.user_id))
    elif body.action == "mark_paid":
        row = settlement_service.mark_payout_paid(pid, str(g.user_id))
    else:
        row = settlement_service.reject_payout_request(pid, str(g.user_id), body.failure_reason)
    return jsonify({"payout_request": row}), 200


@bp.post("/events/<event_id>/comp-ticket")
@require_auth
def admin_comp_ticket_route(event_id: str) -> tuple[dict, int]:
    """Admin: 手動補票（公關票）。MVP-3.4。"""
    _ensure_admin()
    event_uuid = parse_uuid(event_id, "event_id")
    body = parse_json(CompTicketRequest)
    ticket = events_service.create_comp_ticket(
        jwt=g.jwt,
        event_id=event_uuid,
        ticket_type_id=body.ticket_type_id,
        email=(body.email or "").strip() or None,
        user_id=str(body.user_id) if body.user_id else None,
        note=body.note,
        actor_user_id=g.user_id,
        skip_permission_check=True,
        actor_type="admin",
    )
    return jsonify({"ticket": ticket}), 201
