from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.domain.schemas import (
    CreateEventRequest,
    CreateTicketTypeRequest,
    EventFormResponse,
    EventFormsListResponse,
    EventInternalNoteRequest,
    EventInternalNoteResponse,
    EventResponse,
    OrganizerApplyRequest,
    OrganizerAttendeesResponse,
    OrganizerEventDetailResponse,
    TicketTypeResponse,
    UpdateEventRequest,
    UpsertEventFormRequest,
)
from app.services.auth_service import require_auth
from app.services.events_service import events_service
from app.services.forms_service import forms_service

from ._utils import parse_json, parse_uuid

bp = Blueprint("ticket_types", __name__, url_prefix="/api/v1/organizer")


@bp.post("/apply")
@require_auth
def apply_organizer() -> tuple[dict, int]:
    request_model = parse_json(OrganizerApplyRequest)
    organization = events_service.apply_organizer(
        jwt=g.jwt,
        user_id=g.user_id,
        payload=request_model.model_dump(exclude_none=True),
    )
    return jsonify({"organization": organization}), 201


@bp.post("/events")
@require_auth
def create_event() -> tuple[dict, int]:
    request_model = parse_json(CreateEventRequest)
    event = events_service.create_event(
        jwt=g.jwt,
        user_id=g.user_id,
        payload=request_model.model_dump(mode="json", exclude_none=True),
    )
    payload = EventResponse(**event)
    return jsonify({"event": payload.model_dump(mode="json")}), 201


@bp.patch("/events/<event_id>")
@require_auth
def patch_event(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    request_model = parse_json(UpdateEventRequest)

    event = events_service.update_event(
        jwt=g.jwt,
        event_id=event_uuid,
        payload=request_model.model_dump(mode="json", exclude_none=True),
    )
    payload = EventResponse(**event)
    return jsonify({"event": payload.model_dump(mode="json")}), 200


@bp.get("/events/<event_id>")
@require_auth
def get_organizer_event(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    detail = events_service.get_organizer_event_detail(g.jwt, event_uuid, g.user_id)
    payload = OrganizerEventDetailResponse(**detail)
    return jsonify(payload.model_dump(mode="json")), 200


@bp.patch("/events/<event_id>/internal-note")
@bp.put("/events/<event_id>/internal-note")
@require_auth
def upsert_internal_note(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    request_model = parse_json(EventInternalNoteRequest)

    row = events_service.upsert_event_internal_note(
        jwt=g.jwt,
        event_id=event_uuid,
        user_id=g.user_id,
        note=request_model.note,
    )
    payload = EventInternalNoteResponse(
        event_id=row.get("event_id", str(event_uuid)),
        note=row.get("note", request_model.note),
        updated_at=row.get("updated_at"),
        updated_by=row.get("updated_by"),
    )
    return jsonify(payload.model_dump(mode="json")), 200


@bp.get("/events/<event_id>/forms")
@require_auth
def list_event_forms(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    rows = forms_service.list_organizer_forms(g.jwt, event_uuid)
    payload = EventFormsListResponse(items=rows)
    return jsonify(payload.model_dump(mode="json", by_alias=True)), 200


@bp.post("/events/<event_id>/forms")
@require_auth
def upsert_event_form(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    request_model = parse_json(UpsertEventFormRequest)

    row = forms_service.upsert_form(
        g.jwt,
        event_uuid,
        request_model.model_dump(mode="json", by_alias=True, exclude_none=True),
    )
    payload = EventFormResponse(**row)
    return jsonify({"form": payload.model_dump(mode="json", by_alias=True)}), 201


@bp.post("/events/<event_id>/ticket-types")
@require_auth
def create_ticket_type(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    request_model = parse_json(CreateTicketTypeRequest)

    ticket_type = events_service.create_ticket_type(
        jwt=g.jwt,
        event_id=event_uuid,
        payload=request_model.model_dump(mode="json", exclude_none=True),
    )
    payload = TicketTypeResponse(**ticket_type)
    return jsonify({"ticket_type": payload.model_dump(mode="json")}), 201


@bp.get("/events/<event_id>/attendees")
@require_auth
def list_attendees(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    keyword = request.args.get("query")

    rows = events_service.list_attendees(g.jwt, event_uuid, keyword)
    normalized = [
        {
            "ticket_id": row.get("id"),
            "user_id": row.get("user_id"),
            "status": row.get("status"),
            "checked_in_at": row.get("checked_in_at"),
            "ticket_type_id": row.get("ticket_type_id"),
            "answers": row.get("answers"),
        }
        for row in rows
    ]

    payload = OrganizerAttendeesResponse(items=normalized)
    return jsonify(payload.model_dump(mode="json")), 200
