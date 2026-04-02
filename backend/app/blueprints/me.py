from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.blueprints._utils import require_auth
from app.domain.schemas import MyOrganizerSummaryResponse
from app.services.events_service import events_service

bp = Blueprint("me", __name__, url_prefix="/api/v1/me")


@bp.get("/organizer-summary")
@require_auth
def get_organizer_summary() -> tuple[dict, int]:
    data = events_service.get_my_organizer_summary(g.jwt, g.user_id)
    payload = MyOrganizerSummaryResponse(**data)
    return jsonify(payload.model_dump(mode="json")), 200
