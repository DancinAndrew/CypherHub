from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorContent(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorContent


class HealthResponse(BaseModel):
    status: str


class DanceStyle(str, Enum):
    hiphop = "hiphop"
    popping = "popping"
    locking = "locking"
    house = "house"
    waacking = "waacking"
    breaking = "breaking"
    krump = "krump"
    voguing = "voguing"
    freestyle = "freestyle"
    choreo = "choreo"
    allstyle = "allstyle"


class EventType(str, Enum):
    cypher = "cypher"
    battle = "battle"
    group_battle = "group_battle"
    workshop = "workshop"
    jam = "jam"
    showcase = "showcase"
    audition = "audition"
    party = "party"


class FormFieldType(str, Enum):
    text = "text"
    number = "number"
    email = "email"
    phone = "phone"
    url = "url"
    single_select = "single_select"
    multi_select = "multi_select"
    dropdown = "dropdown"
    date = "date"
    checkbox = "checkbox"


class FormField(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type: FormFieldType
    required: bool = False
    help_text: str | None = None
    placeholder: str | None = None
    options: list[str] = Field(default_factory=list)
    validation: dict[str, Any] | None = None


class FormSchemaDefinition(BaseModel):
    version: int = 1
    fields: list[FormField] = Field(default_factory=list)


class EventResponse(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    description: str | None = None
    short_desc: str | None = None
    start_at: datetime
    end_at: datetime
    timezone: str | None = None
    location_name: str | None = None
    location_address: str | None = None
    map_url: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    registration_start_at: datetime | None = None
    registration_end_at: datetime | None = None
    socials: dict[str, str] = Field(default_factory=dict)
    eligibility: str | None = None
    event_language: str | None = None
    checkin_open_at: datetime | None = None
    checkin_note: str | None = None
    schedule: list[dict[str, Any]] = Field(default_factory=list)
    rules: str | None = None
    refund_policy: str | None = None
    status: str
    published_at: datetime | None = None
    dance_styles: list[DanceStyle] = Field(default_factory=list)
    event_types: list[EventType] = Field(default_factory=list)


class EventMediaResponse(BaseModel):
    id: UUID
    event_id: UUID
    path: str
    sort_order: int


class TicketTypeResponse(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    description: str | None = None
    price_cents: int
    currency: str
    capacity: int
    sold_count: int
    per_user_limit: int
    sale_start_at: datetime | None = None
    sale_end_at: datetime | None = None
    is_active: bool


class EventListResponse(BaseModel):
    items: list[EventResponse]


class EventDetailResponse(BaseModel):
    event: EventResponse
    event_media: list[EventMediaResponse]
    ticket_types: list[TicketTypeResponse]


class RegisterRequest(BaseModel):
    ticket_type_id: UUID
    quantity: int = Field(default=1, ge=1, le=10)
    answers: dict[str, Any] = Field(default_factory=dict)


class TicketResponse(BaseModel):
    ticket_id: UUID
    event_id: UUID
    ticket_type_id: UUID
    user_id: UUID
    status: str
    qr_secret: str
    issued_at: datetime | None = None
    checked_in_at: datetime | None = None


class TicketsListResponse(BaseModel):
    items: list[TicketResponse]


class RegisterResponse(BaseModel):
    tickets: list[TicketResponse]


class OrganizerApplyRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    contact_email: str | None = None
    logo_url: str | None = None


class CreateEventRequest(BaseModel):
    org_id: UUID
    title: str = Field(min_length=1)
    description: str | None = None
    short_desc: str | None = None
    start_at: datetime
    end_at: datetime
    timezone: str | None = None
    location_name: str | None = None
    location_address: str | None = None
    map_url: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    registration_start_at: datetime | None = None
    registration_end_at: datetime | None = None
    socials: dict[str, str] = Field(default_factory=dict)
    eligibility: str | None = None
    event_language: str | None = None
    checkin_open_at: datetime | None = None
    checkin_note: str | None = None
    schedule: list[dict[str, Any]] = Field(default_factory=list)
    rules: str | None = None
    refund_policy: str | None = None
    status: str = Field(default="draft")
    dance_styles: list[DanceStyle] = Field(default_factory=list)
    event_types: list[EventType] = Field(default_factory=list)


class UpdateEventRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    short_desc: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str | None = None
    location_name: str | None = None
    location_address: str | None = None
    map_url: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    registration_start_at: datetime | None = None
    registration_end_at: datetime | None = None
    socials: dict[str, str] | None = None
    eligibility: str | None = None
    event_language: str | None = None
    checkin_open_at: datetime | None = None
    checkin_note: str | None = None
    schedule: list[dict[str, Any]] | None = None
    rules: str | None = None
    refund_policy: str | None = None
    status: str | None = None
    published_at: datetime | None = None
    dance_styles: list[DanceStyle] | None = None
    event_types: list[EventType] | None = None


class EventFormResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    id: UUID
    event_id: UUID
    ticket_type_id: UUID | None = None
    form_schema: FormSchemaDefinition = Field(alias="schema", serialization_alias="schema")
    version: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EventFormEnvelopeResponse(BaseModel):
    form: EventFormResponse | None = None


class EventFormsListResponse(BaseModel):
    items: list[EventFormResponse]


class UpsertEventFormRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticket_type_id: UUID | None = None
    form_schema: FormSchemaDefinition = Field(alias="schema", serialization_alias="schema")
    is_active: bool = True


class OrganizerEventDetailResponse(BaseModel):
    event: EventResponse
    internal_note: str = ""


class EventInternalNoteRequest(BaseModel):
    note: str = ""


class EventInternalNoteResponse(BaseModel):
    event_id: UUID
    note: str
    updated_at: datetime | None = None
    updated_by: UUID | None = None


class CreateTicketTypeRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    capacity: int = Field(ge=0)
    per_user_limit: int = Field(default=1, ge=1)
    sale_start_at: datetime | None = None
    sale_end_at: datetime | None = None
    is_active: bool = True


class AttendeeResponse(BaseModel):
    ticket_id: UUID
    user_id: UUID
    status: str
    checked_in_at: datetime | None = None
    ticket_type_id: UUID
    answers: dict[str, Any] | None = None


class OrganizerAttendeesResponse(BaseModel):
    items: list[AttendeeResponse]


class CheckinRequest(BaseModel):
    ticket_id: UUID | None = None
    qr_secret: str | None = None
    qr_payload: str | None = None

    model_config = ConfigDict(extra="forbid")


class CheckinResponse(BaseModel):
    payload: dict[str, Any]


class GenericOKResponse(BaseModel):
    ok: bool
