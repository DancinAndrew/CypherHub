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


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


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
    thumbnail_path: str | None = None


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


class OrganizerSummaryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    contact_email: str | None = None
    logo_url: str | None = None


class EventDetailResponse(BaseModel):
    event: EventResponse
    event_media: list[EventMediaResponse]
    ticket_types: list[TicketTypeResponse]
    organizer: OrganizerSummaryResponse | None = None
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
    event_media: list[EventMediaResponse] = Field(default_factory=list)
    ticket_types: list[TicketTypeResponse] = Field(default_factory=list)


class EventInternalNoteRequest(BaseModel):
    note: str = ""


class AdminPatchEventRequest(BaseModel):
    """Admin 下架用，僅支援 status=disabled（或 cancelled）。"""

    status: str = Field(..., pattern="^(disabled|cancelled)$")


class AdminOrganizationApprovalRequest(BaseModel):
    """Admin 主辦方入駐審核。MVP-3.2。"""

    status: str = Field(..., pattern="^(approved|rejected)$")
    rejection_reason: str | None = None


class EventInternalNoteResponse(BaseModel):
    event_id: UUID
    note: str
    updated_at: datetime | None = None
    updated_by: UUID | None = None


class CreateTicketTypeRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    price_cents: int = Field(default=0, ge=0)
    capacity: int = Field(ge=0)
    per_user_limit: int = Field(default=1, ge=1)
    sale_start_at: datetime | None = None
    sale_end_at: datetime | None = None
    is_active: bool = True


class UpdateTicketTypeRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    price_cents: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, ge=0)
    per_user_limit: int | None = Field(default=None, ge=1)
    sale_start_at: datetime | None = None
    sale_end_at: datetime | None = None
    is_active: bool | None = None


class AttendeeResponse(BaseModel):
    ticket_id: UUID
    user_id: UUID
    status: str
    checked_in_at: datetime | None = None
    ticket_type_id: UUID
    answers: dict[str, Any] | None = None


class OrganizerAttendeesResponse(BaseModel):
    items: list[AttendeeResponse]


# --- MVP-3.1: 主辦方成員管理 ---


class OrganizerMemberResponse(BaseModel):
    user_id: UUID
    org_id: UUID
    role: str  # owner | admin | staff
    created_at: datetime | None = None


class OrganizerMembersListResponse(BaseModel):
    items: list[OrganizerMemberResponse]


class AddOrgMemberRequest(BaseModel):
    user_id: UUID
    role: str = Field(..., pattern="^(admin|staff)$")


class UpdateOrgMemberRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(owner|admin|staff)$")


class CheckinRequest(BaseModel):
    ticket_id: UUID | None = None
    qr_secret: str | None = None
    qr_payload: str | None = None

    model_config = ConfigDict(extra="forbid")


class CheckinResponse(BaseModel):
    payload: dict[str, Any]


class GenericOKResponse(BaseModel):
    ok: bool


class MyOrganizerOrgResponse(BaseModel):
    id: UUID
    name: str
    role: str
    approval_status: str = "approved"  # MVP-3.2: pending | approved | rejected


class MyOrganizerEventResponse(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    status: str
    start_at: datetime | None = None


class MyOrganizerSummaryResponse(BaseModel):
    organizations: list[MyOrganizerOrgResponse]
    events: list[MyOrganizerEventResponse]


# --- MVP-3.3: 結算與提款 ---


class SettlementResponse(BaseModel):
    id: UUID
    org_id: UUID
    period_start: datetime
    period_end: datetime
    gross_cents: int
    platform_fee_cents: int
    net_cents: int
    status: str
    created_at: datetime | None = None


class PayoutRequestResponse(BaseModel):
    id: UUID
    org_id: UUID
    settlement_id: UUID | None = None
    amount_cents: int
    status: str
    requested_at: datetime | None = None
    processed_at: datetime | None = None
    failure_reason: str | None = None


class CreatePayoutRequestRequest(BaseModel):
    org_id: UUID
    amount_cents: int = Field(..., gt=0)


class AdminPayoutActionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    failure_reason: str | None = None


class GenerateSettlementsRequest(BaseModel):
    period_start: datetime
    period_end: datetime


# --- MVP-2: Orders / Payments (develop.md 2.1.1) ---


class OrderStatus(str, Enum):
    created = "created"
    holding = "holding"
    pending_payment = "pending_payment"
    paid = "paid"
    issued = "issued"
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class OrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    ticket_type_id: UUID
    quantity: int
    price_cents: int
    created_at: datetime | None = None


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    total_cents: int
    currency: str = "TWD"
    hold_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    provider: str
    external_id: str
    amount_cents: int
    currency: str = "TWD"
    status: str
    created_at: datetime | None = None


class OrderDetailResponse(BaseModel):
    order: OrderResponse
    items: list[OrderItemResponse] = Field(default_factory=list)
    payments: list[PaymentResponse] = Field(default_factory=list)


class OrdersListResponse(BaseModel):
    items: list[OrderResponse]


class CreateHoldOrderItem(BaseModel):
    ticket_type_id: UUID
    quantity: int = Field(ge=1, le=20)


class CreateHoldOrderRequest(BaseModel):
    items: list[CreateHoldOrderItem] = Field(min_length=1)
    hold_minutes: int = Field(default=15, ge=1, le=60)
