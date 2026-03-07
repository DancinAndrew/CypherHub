from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify

from app.domain.errors import AppError
from app.services.auth_service import require_auth
from app.services.events_service import events_service

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


def _ensure_admin() -> None:
    allowlist = current_app.config.get("ADMIN_ALLOWLIST", set())
    if not allowlist or g.user_id not in allowlist:
        raise AppError(
            code="FORBIDDEN",
            message="Admin allowlist required",
            http_status=403,
        )


@bp.get("/events")
@require_auth
def list_admin_events() -> tuple[dict, int]:
    _ensure_admin()
    events = events_service.list_public_events()
    return jsonify({"items": events}), 200


@bp.patch("/events/<event_id>")
@require_auth
def patch_admin_event(event_id: str) -> tuple[dict, int]:
    _ensure_admin()
    # MVP-1 keeps admin mutation minimal; organizer update endpoint remains the primary path.
    raise AppError(
        code="NOT_IMPLEMENTED",
        message="Admin event patch is not enabled in MVP-1",
        http_status=501,
    )
