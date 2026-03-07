from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.domain.schemas import CheckinRequest
from app.services.auth_service import require_auth
from app.services.checkin_service import checkin_service

from ._utils import parse_json, parse_uuid

bp = Blueprint("checkin", __name__, url_prefix="/api/v1/organizer/events")


@bp.post("/<event_id>/checkin/verify")
@require_auth
def verify_checkin(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    request_model = parse_json(CheckinRequest)
    ticket_id, qr_secret = checkin_service.parse_checkin_input(request_model)

    result = checkin_service.verify_ticket_qr(
        jwt=g.jwt,
        event_id=event_uuid,
        ticket_id=ticket_id,
        qr_secret=qr_secret,
    )
    return jsonify(result), 200


@bp.post("/<event_id>/checkin/commit")
@require_auth
def commit_checkin(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    request_model = parse_json(CheckinRequest)
    ticket_id, qr_secret = checkin_service.parse_checkin_input(request_model)

    result = checkin_service.commit_checkin(
        jwt=g.jwt,
        event_id=event_uuid,
        ticket_id=ticket_id,
        qr_secret=qr_secret,
    )
    return jsonify(result), 200
