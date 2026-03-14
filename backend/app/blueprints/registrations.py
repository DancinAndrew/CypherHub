from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify

from app.domain.schemas import RegisterRequest, RegisterResponse
from app.services.auth_service import require_auth
from app.services.email_service import email_service
from app.services.events_service import events_service
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

    user_email = (g.user or {}).get("email") if hasattr(g, "user") else None
    if user_email and tickets:
        current_app.logger.info("[registration] sending success email to %s (event=%s)", user_email, event_uuid)
        try:
            event_title = events_service.get_event_title(event_uuid)
            base_url = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:5173")
            email_service.send_registration_success_email(
                to_email=user_email,
                event_title=event_title,
                tickets=tickets,
                frontend_base_url=base_url,
            )
        except Exception as exc:
            current_app.logger.warning("Registration success email failed: %s", exc)

    payload = RegisterResponse(tickets=normalized_tickets)
    return jsonify(payload.model_dump(mode="json")), 200
