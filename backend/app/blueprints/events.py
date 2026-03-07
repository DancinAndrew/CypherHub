from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.domain.errors import AppError
from app.domain.schemas import (
    DanceStyle,
    EventDetailResponse,
    EventFormEnvelopeResponse,
    EventListResponse,
    EventType,
    RegisterRequest,
    RegisterResponse,
)
from app.services.auth_service import require_auth
from app.services.events_service import events_service
from app.services.forms_service import forms_service
from app.services.registration_service import registration_service

from ._utils import parse_json, parse_uuid

bp = Blueprint("events", __name__, url_prefix="/api/v1/events")


def _parse_multi_values(
    raw: str | None,
    allowed_values: set[str],
    field_name: str,
) -> list[str]:
    if not raw:
        return []

    normalized: list[str] = []
    for item in raw.split(","):
        value = item.strip().lower()
        if not value:
            continue
        if value not in allowed_values:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Invalid {field_name} value",
                details={field_name: value, "allowed": sorted(allowed_values)},
                http_status=400,
            )
        if value not in normalized:
            normalized.append(value)
    return normalized


@bp.get("")
def list_events() -> tuple[dict, int]:
    styles = _parse_multi_values(
        request.args.get("styles"),
        {member.value for member in DanceStyle},
        "styles",
    )
    types = _parse_multi_values(
        request.args.get("types"),
        {member.value for member in EventType},
        "types",
    )

    items = events_service.list_public_events(
        q=request.args.get("q"),
        from_at=request.args.get("from"),
        to_at=request.args.get("to"),
        org_id=request.args.get("org_id"),
        styles=styles,
        types=types,
    )
    payload = EventListResponse(items=items)
    return jsonify(payload.model_dump(mode="json")), 200


@bp.get("/<event_id>")
def get_event(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    detail = events_service.get_public_event_detail(event_uuid)
    payload = EventDetailResponse(**detail)
    return jsonify(payload.model_dump(mode="json")), 200


@bp.get("/<event_id>/forms")
def get_event_form(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    ticket_type_id_raw = request.args.get("ticket_type_id")
    ticket_type_uuid = (
        parse_uuid(ticket_type_id_raw, "ticket_type_id")
        if ticket_type_id_raw
        else None
    )

    form = forms_service.get_public_form(event_uuid, ticket_type_uuid)
    payload = EventFormEnvelopeResponse(form=form)
    return jsonify(payload.model_dump(mode="json", by_alias=True)), 200


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
