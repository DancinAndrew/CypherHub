from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorContent(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


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
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    validation: Optional[dict[str, Any]] = None


class FormSchemaDefinition(BaseModel):
    version: int = 1
    fields: list[FormField] = Field(default_factory=list)


class EventResponse(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    description: Optional[str] = None
    short_desc: Optional[str] = None
    start_at: datetime
    end_at: datetime
    timezone: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    map_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    registration_start_at: Optional[datetime] = None
    registration_end_at: Optional[datetime] = None
    socials: dict[str, str] = Field(default_factory=dict)
    eligibility: Optional[str] = None
    event_language: Optional[str] = None
    checkin_open_at: Optional[datetime] = None
    checkin_note: Optional[str] = None
    schedule: list[dict[str, Any]] = Field(default_factory=list)
    rules: Optional[str] = None
    refund_policy: Optional[str] = None
    status: str
    published_at: Optional[datetime] = None
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
    description: Optional[str] = None
    price_cents: int
    currency: str
    capacity: int
    sold_count: int
    per_user_limit: int
    sale_start_at: Optional[datetime] = None
    sale_end_at: Optional[datetime] = None
    is_active: bool


class EventListResponse(BaseModel):
    items: list[EventResponse]


class OrganizerSummaryResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    contact_email: Optional[str] = None
    logo_url: Optional[str] = None


class EventDetailResponse(BaseModel):
    event: EventResponse
    event_media: list[EventMediaResponse]
    ticket_types: list[TicketTypeResponse]
    organizer: Optional[OrganizerSummaryResponse] = None
    other_events: list[EventResponse] = Field(default_factory=list)


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
    issued_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None


class TicketsListResponse(BaseModel):
    items: list[TicketResponse]


class RegisterResponse(BaseModel):
    tickets: list[TicketResponse]


class OrganizerApplyRequest(BaseModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    contact_email: Optional[str] = None
    logo_url: Optional[str] = None


class CreateEventRequest(BaseModel):
    org_id: UUID
    title: str = Field(min_length=1)
    description: Optional[str] = None
    short_desc: Optional[str] = None
    start_at: datetime
    end_at: datetime
    timezone: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    map_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    registration_start_at: Optional[datetime] = None
    registration_end_at: Optional[datetime] = None
    socials: dict[str, str] = Field(default_factory=dict)
    eligibility: Optional[str] = None
    event_language: Optional[str] = None
    checkin_open_at: Optional[datetime] = None
    checkin_note: Optional[str] = None
    schedule: list[dict[str, Any]] = Field(default_factory=list)
    rules: Optional[str] = None
    refund_policy: Optional[str] = None
    status: str = Field(default="draft")
    dance_styles: list[DanceStyle] = Field(default_factory=list)
    event_types: list[EventType] = Field(default_factory=list)


class UpdateEventRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_desc: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    timezone: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    map_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    registration_start_at: Optional[datetime] = None
    registration_end_at: Optional[datetime] = None
    socials: Optional[dict[str, str]] = None
    eligibility: Optional[str] = None
    event_language: Optional[str] = None
    checkin_open_at: Optional[datetime] = None
    checkin_note: Optional[str] = None
    schedule: Optional[list[dict[str, Any]]] = None
    rules: Optional[str] = None
    refund_policy: Optional[str] = None
    status: Optional[str] = None
    published_at: Optional[datetime] = None
    dance_styles: Optional[list[DanceStyle]] = None
    event_types: Optional[list[EventType]] = None


class EventFormResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    id: UUID
    event_id: UUID
    ticket_type_id: Optional[UUID] = None
    form_schema: FormSchemaDefinition = Field(alias="schema", serialization_alias="schema")
    version: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EventFormEnvelopeResponse(BaseModel):
    form: Optional[EventFormResponse] = None


class EventFormsListResponse(BaseModel):
    items: list[EventFormResponse]


class UpsertEventFormRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticket_type_id: Optional[UUID] = None
    form_schema: FormSchemaDefinition = Field(alias="schema", serialization_alias="schema")
    is_active: bool = True


class OrganizerEventDetailResponse(BaseModel):
    event: EventResponse
    internal_note: str = ""
    event_media: list[EventMediaResponse] = Field(default_factory=list)


class EventInternalNoteRequest(BaseModel):
    note: str = ""


class EventInternalNoteResponse(BaseModel):
    event_id: UUID
    note: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[UUID] = None


class CreateTicketTypeRequest(BaseModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    capacity: int = Field(ge=0)
    per_user_limit: int = Field(default=1, ge=1)
    sale_start_at: Optional[datetime] = None
    sale_end_at: Optional[datetime] = None
    is_active: bool = True


class AttendeeResponse(BaseModel):
    ticket_id: UUID
    user_id: UUID
    status: str
    checked_in_at: Optional[datetime] = None
    ticket_type_id: UUID
    answers: Optional[dict[str, Any]] = None


class OrganizerAttendeesResponse(BaseModel):
    items: list[AttendeeResponse]


class CheckinRequest(BaseModel):
    ticket_id: Optional[UUID] = None
    qr_secret: Optional[str] = None
    qr_payload: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CheckinResponse(BaseModel):
    payload: dict[str, Any]


class GenericOKResponse(BaseModel):
    ok: bool
