from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.domain.schemas import RegisterRequest, RegisterResponse
from app.services.auth_service import require_auth
from app.services.registration_service import registration_service

from ._utils import parse_json, parse_uuid

bp = Blueprint("registrations", __name__, url_prefix="/api/v1/events")


@bp.post("/<event_id>/register")
@require_auth
def register_event(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    request_model = parse_json(RegisterRequest)

    tickets = registration_service.register_free(
        jwt=g.jwt,
        event_id=event_uuid,
        ticket_type_id=request_model.ticket_type_id,
        quantity=request_model.quantity,
        answers=request_model.answers,
    )

    normalized_tickets = [
        {
            "ticket_id": row.get("id"),
            "event_id": row.get("event_id"),
            "ticket_type_id": row.get("ticket_type_id"),
            "user_id": row.get("user_id"),
            "status": row.get("status"),
            "qr_secret": row.get("qr_secret"),
            "issued_at": row.get("issued_at"),
            "checked_in_at": row.get("checked_in_at"),
        }
        for row in tickets
    ]
    payload = RegisterResponse(tickets=normalized_tickets)
    return jsonify(payload.model_dump(mode="json")), 200
