from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.domain.schemas import GenericOKResponse, TicketsListResponse
from app.services.auth_service import require_auth
from app.services.ticket_service import ticket_service

from ._utils import parse_uuid

bp = Blueprint("tickets", __name__, url_prefix="/api/v1/me/tickets")


@bp.get("")
@require_auth
def list_my_tickets() -> tuple[dict, int]:
    rows = ticket_service.list_my_tickets(g.jwt, g.user_id)
    normalized_rows = [
        {
            "ticket_id": row.get("id"),
            "event_id": row.get("event_id"),
            "ticket_type_id": row.get("ticket_type_id"),
            "user_id": row.get("user_id"),
            "status": row.get("status"),
            "issued_at": row.get("issued_at"),
            "checked_in_at": row.get("checked_in_at"),
            "qr_secret": row.get("qr_secret"),
        }
        for row in rows
    ]
    payload = TicketsListResponse(items=normalized_rows)
    return jsonify(payload.model_dump(mode="json")), 200


@bp.delete("/<ticket_id>")
@require_auth
def cancel_ticket(ticket_id: str) -> tuple[dict, int]:
    ticket_uuid = parse_uuid(ticket_id, "ticket_id")
    ticket_service.cancel_ticket(g.jwt, ticket_uuid, g.user_id)
    payload = GenericOKResponse(ok=True)
    return jsonify(payload.model_dump(mode="json")), 200


@bp.post("/<ticket_id>/resend")
@require_auth
def resend_ticket(ticket_id: str) -> tuple[dict, int]:
    ticket_uuid = parse_uuid(ticket_id, "ticket_id")
    ticket_service.resend_ticket_email(g.jwt, ticket_uuid, g.user_id)
    payload = GenericOKResponse(ok=True)
    return jsonify(payload.model_dump(mode="json")), 200
