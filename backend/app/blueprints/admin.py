from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from app.domain.errors import AppError
from app.domain.schemas import AdminPatchEventRequest
from app.services.auth_service import require_auth
from app.services.events_service import events_service

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
