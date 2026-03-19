from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.domain.errors import AppError
from app.domain.schemas import (
    AddOrgMemberRequest,
    CompTicketRequest,
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
    OrganizerMembersListResponse,
    TicketTypeResponse,
    UpdateEventRequest,
    UpdateOrgMemberRoleRequest,
    UpdateTicketTypeRequest,
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
        user_id=g.user_id,
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
    events_service.require_event_admin(g.jwt, event_uuid, g.user_id)
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
    events_service.require_event_admin(g.jwt, event_uuid, g.user_id)
    rows = forms_service.list_organizer_forms(g.jwt, event_uuid)
    payload = EventFormsListResponse(items=rows)
    return jsonify(payload.model_dump(mode="json", by_alias=True)), 200


@bp.post("/events/<event_id>/forms")
@require_auth
def upsert_event_form(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    events_service.require_event_admin(g.jwt, event_uuid, g.user_id)
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
        user_id=g.user_id,
    )
    payload = TicketTypeResponse(**ticket_type)
    return jsonify({"ticket_type": payload.model_dump(mode="json")}), 201


@bp.patch("/events/<event_id>/ticket-types/<ticket_type_id>")
@require_auth
def patch_ticket_type(event_id: str, ticket_type_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    ticket_type_uuid = parse_uuid(ticket_type_id, "ticket_type_id")
    request_model = parse_json(UpdateTicketTypeRequest)

    ticket_type = events_service.update_ticket_type(
        jwt=g.jwt,
        event_id=event_uuid,
        ticket_type_id=ticket_type_uuid,
        payload=request_model.model_dump(mode="json", exclude_none=True),
        user_id=g.user_id,
    )
    payload = TicketTypeResponse(**ticket_type)
    return jsonify({"ticket_type": payload.model_dump(mode="json")}), 200


@bp.delete("/events/<event_id>/ticket-types/<ticket_type_id>")
@require_auth
def delete_ticket_type(event_id: str, ticket_type_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    ticket_type_uuid = parse_uuid(ticket_type_id, "ticket_type_id")
    events_service.delete_ticket_type(
        jwt=g.jwt,
        event_id=event_uuid,
        ticket_type_id=ticket_type_uuid,
        user_id=g.user_id,
    )
    return jsonify({"ok": True}), 204


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


@bp.post("/events/<event_id>/attendees/<ticket_id>/resend")
@require_auth
def resend_attendee_ticket(event_id: str, ticket_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    ticket_uuid = parse_uuid(ticket_id, "ticket_id")
    events_service.resend_attendee_ticket(g.jwt, event_uuid, ticket_uuid)
    return jsonify({"ok": True}), 200


@bp.post("/events/<event_id>/comp-ticket")
@require_auth
def create_comp_ticket_route(event_id: str) -> tuple[dict, int]:
    """手動補票（公關票）。MVP-3.4。需 event admin。"""
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
    )
    return jsonify({"ticket": ticket}), 201


@bp.post("/events/<event_id>/media")
@require_auth
def upload_event_media(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    events_service.require_event_admin(g.jwt, event_uuid, g.user_id)
    file = request.files.get("file")
    if not file or file.filename == "":
        raise AppError(
            code="VALIDATION_ERROR",
            message="Missing file",
            http_status=400,
        )
    content_type = file.content_type or "image/jpeg"
    file_data = file.read()
    if len(file_data) > 5 * 1024 * 1024:
        raise AppError(
            code="VALIDATION_ERROR",
            message="File too large (max 5MB)",
            http_status=400,
        )
    row = events_service.upload_event_media(
        g.jwt,
        event_uuid,
        file_data,
        content_type,
        g.user_id,
    )
    return jsonify({"media": row}), 201


# --- MVP-3.1: 主辦方成員管理 ---


@bp.get("/organizations/<org_id>/members")
@require_auth
def list_org_members(org_id: str) -> tuple[dict, int]:
    org_uuid = parse_uuid(org_id, "org_id")
    rows = events_service.list_org_members(g.jwt, str(org_uuid), g.user_id)
    payload = OrganizerMembersListResponse(items=rows)
    return jsonify(payload.model_dump(mode="json")), 200


@bp.post("/organizations/<org_id>/members")
@require_auth
def add_org_member(org_id: str) -> tuple[dict, int]:
    org_uuid = parse_uuid(org_id, "org_id")
    request_model = parse_json(AddOrgMemberRequest)
    row = events_service.add_org_member(
        jwt=g.jwt,
        org_id=str(org_uuid),
        target_user_id=str(request_model.user_id),
        role=request_model.role,
        actor_user_id=g.user_id,
    )
    return jsonify({"member": row}), 201


@bp.patch("/organizations/<org_id>/members/<user_id>")
@require_auth
def patch_org_member(org_id: str, user_id: str) -> tuple[dict, int]:
    org_uuid = parse_uuid(org_id, "org_id")
    target_uuid = parse_uuid(user_id, "user_id")
    request_model = parse_json(UpdateOrgMemberRoleRequest)
    row = events_service.update_org_member_role(
        jwt=g.jwt,
        org_id=str(org_uuid),
        target_user_id=str(target_uuid),
        new_role=request_model.role,
        actor_user_id=g.user_id,
    )
    return jsonify({"member": row}), 200


@bp.delete("/organizations/<org_id>/members/<user_id>")
@require_auth
def delete_org_member(org_id: str, user_id: str) -> tuple[dict, int]:
    org_uuid = parse_uuid(org_id, "org_id")
    target_uuid = parse_uuid(user_id, "user_id")
    events_service.remove_org_member(
        jwt=g.jwt,
        org_id=str(org_uuid),
        target_user_id=str(target_uuid),
        actor_user_id=g.user_id,
    )
    return jsonify({"ok": True}), 204
