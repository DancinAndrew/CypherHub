import axios from "axios";

import { pinia } from "../stores";
import { useAuthStore } from "../stores/auth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

client.interceptors.request.use((config) => {
  const authStore = useAuthStore(pinia);
  const token = authStore.accessToken;

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const authStore = useAuthStore(pinia);
      authStore.clearSession();
      const path = window.location.pathname + window.location.search;
      const redirect = path && path !== "/login" ? path : "/";
      window.location.href = `/login?redirect=${encodeURIComponent(redirect)}`;
    }
    return Promise.reject(err);
  },
);

export type EventItem = {
  id: string;
  org_id: string;
  title: string;
  description: string | null;
  short_desc?: string | null;
  start_at: string;
  end_at: string;
  timezone?: string | null;
  location_name?: string | null;
  location_address?: string | null;
  rules?: string | null;
  refund_policy?: string | null;
  map_url?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  registration_start_at?: string | null;
  registration_end_at?: string | null;
  socials?: Record<string, string>;
  eligibility?: string | null;
  event_language?: string | null;
  checkin_open_at?: string | null;
  checkin_note?: string | null;
  schedule?: Array<Record<string, string>>;
  status: string;
  published_at?: string | null;
  dance_styles: string[];
  event_types: string[];
};

export type TicketType = {
  id: string;
  event_id: string;
  name: string;
  description: string | null;
  price_cents: number;
  currency: string;
  capacity: number;
  sold_count: number;
  per_user_limit: number;
  sale_start_at: string | null;
  sale_end_at: string | null;
  is_active: boolean;
};

export type EventDetail = {
  event: EventItem;
  event_media: Array<{ id: string; path: string; sort_order: number }>;
  ticket_types: TicketType[];
};

export type FormFieldType =
  | "text"
  | "number"
  | "email"
  | "phone"
  | "url"
  | "single_select"
  | "multi_select"
  | "dropdown"
  | "date"
  | "checkbox";

export type FormField = {
  key: string;
  label: string;
  type: FormFieldType;
  required: boolean;
  help_text?: string | null;
  placeholder?: string | null;
  options?: string[];
  validation?: Record<string, unknown> | null;
};

export type FormSchemaDefinition = {
  version: number;
  fields: FormField[];
};

export type EventForm = {
  id: string;
  event_id: string;
  ticket_type_id: string | null;
  schema: FormSchemaDefinition;
  version: number;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type OrganizerEventDetail = {
  event: EventItem;
  internal_note: string;
};

export type TicketItem = {
  ticket_id: string;
  event_id: string;
  ticket_type_id: string;
  user_id: string;
  status: string;
  issued_at: string | null;
  checked_in_at: string | null;
  qr_secret: string;
};

export async function fetchEvents(params?: {
  q?: string;
  from?: string;
  to?: string;
  org_id?: string;
  styles?: string;
  types?: string;
}): Promise<EventItem[]> {
  const response = await client.get<{ items: EventItem[] }>("/api/v1/events", { params });
  return response.data.items;
}

export async function fetchEventDetail(eventId: string): Promise<EventDetail> {
  const response = await client.get<EventDetail>(`/api/v1/events/${eventId}`);
  return response.data;
}

export async function fetchEventForm(eventId: string, ticketTypeId?: string): Promise<EventForm | null> {
  const response = await client.get<{ form: EventForm | null }>(`/api/v1/events/${eventId}/forms`, {
    params: ticketTypeId ? { ticket_type_id: ticketTypeId } : undefined,
  });
  return response.data.form;
}

export async function registerFree(
  eventId: string,
  payload: { ticket_type_id: string; quantity: number; answers?: Record<string, unknown> },
): Promise<TicketItem[]> {
  const response = await client.post<{ tickets: TicketItem[] }>(`/api/v1/events/${eventId}/register`, payload);
  return response.data.tickets;
}

export async function fetchMyTickets(): Promise<TicketItem[]> {
  const response = await client.get<{ items: TicketItem[] }>("/api/v1/me/tickets");
  return response.data.items;
}

export async function resendTicket(ticketId: string): Promise<void> {
  await client.post(`/api/v1/me/tickets/${ticketId}/resend`);
}

export async function cancelTicket(ticketId: string): Promise<void> {
  await client.delete(`/api/v1/me/tickets/${ticketId}`);
}

export type OrganizerApplyPayload = {
  name: string;
  description?: string;
  contact_email?: string;
  logo_url?: string;
};

export type OrganizerApplyResponse = {
  organization: { id: string };
};

export async function organizerApply(payload: OrganizerApplyPayload): Promise<OrganizerApplyResponse> {
  const response = await client.post<OrganizerApplyResponse>("/api/v1/organizer/apply", payload);
  return response.data;
}

export type OrganizerCreateEventPayload = {
  org_id: string;
  title: string;
  description?: string;
  short_desc?: string;
  start_at: string;
  end_at: string;
  timezone?: string;
  location_name?: string;
  location_address?: string;
  map_url?: string;
  contact_email?: string;
  contact_phone?: string;
  registration_start_at?: string;
  registration_end_at?: string;
  socials?: Record<string, string>;
  eligibility?: string;
  event_language?: string;
  checkin_open_at?: string;
  checkin_note?: string;
  schedule?: Array<Record<string, string>>;
  rules?: string;
  refund_policy?: string;
  status?: "draft" | "published";
  dance_styles?: string[];
  event_types?: string[];
};

export type OrganizerEventMutationResponse = {
  event: EventItem;
};

export async function organizerCreateEvent(payload: OrganizerCreateEventPayload): Promise<OrganizerEventMutationResponse> {
  const response = await client.post<OrganizerEventMutationResponse>("/api/v1/organizer/events", payload);
  return response.data;
}

export async function organizerUpdateEvent(eventId: string, payload: Partial<OrganizerCreateEventPayload>): Promise<OrganizerEventMutationResponse> {
  const response = await client.patch<OrganizerEventMutationResponse>(`/api/v1/organizer/events/${eventId}`, payload);
  return response.data;
}

export async function organizerGetEventDetail(eventId: string): Promise<OrganizerEventDetail> {
  const response = await client.get<OrganizerEventDetail>(`/api/v1/organizer/events/${eventId}`);
  return response.data;
}

export async function organizerFetchForms(eventId: string): Promise<EventForm[]> {
  const response = await client.get<{ items: EventForm[] }>(`/api/v1/organizer/events/${eventId}/forms`);
  return response.data.items;
}

export async function organizerUpsertForm(
  eventId: string,
  payload: { ticket_type_id?: string | null; schema: FormSchemaDefinition; is_active?: boolean },
): Promise<EventForm> {
  const response = await client.post<{ form: EventForm }>(`/api/v1/organizer/events/${eventId}/forms`, payload);
  return response.data.form;
}

export type EventInternalNoteResponse = {
  event_id: string;
  note: string;
  updated_at?: string | null;
  updated_by?: string | null;
};

export async function organizerUpsertInternalNote(eventId: string, note: string): Promise<EventInternalNoteResponse> {
  const response = await client.patch<EventInternalNoteResponse>(`/api/v1/organizer/events/${eventId}/internal-note`, { note });
  return response.data;
}

export type OrganizerCreateTicketTypePayload = {
  name: string;
  description?: string;
  capacity: number;
  per_user_limit: number;
  sale_start_at?: string;
  sale_end_at?: string;
  is_active?: boolean;
};

export type OrganizerCreateTicketTypeResponse = {
  ticket_type: TicketType;
};

export async function organizerCreateTicketType(
  eventId: string,
  payload: OrganizerCreateTicketTypePayload,
): Promise<OrganizerCreateTicketTypeResponse> {
  const response = await client.post<OrganizerCreateTicketTypeResponse>(`/api/v1/organizer/events/${eventId}/ticket-types`, payload);
  return response.data;
}

export type AttendeeItem = {
  ticket_id: string;
  user_id: string;
  status: string;
  checked_in_at: string | null;
  ticket_type_id: string;
  answers?: Record<string, unknown> | null;
};

export async function organizerFetchAttendees(eventId: string, query?: string): Promise<AttendeeItem[]> {
  const response = await client.get<{ items: AttendeeItem[] }>(`/api/v1/organizer/events/${eventId}/attendees`, {
    params: query ? { query } : undefined,
  });
  return response.data.items;
}

export type CheckinPayload = {
  ticket_id?: string;
  qr_secret?: string;
  qr_payload?: string;
};

export type CheckinVerifyResult = {
  valid?: boolean;
  can_checkin?: boolean;
  status?: string;
  user_id?: string;
  ticket_type_id?: string;
  reason?: string;
};

export type CheckinCommitResult = {
  ok?: boolean;
  already_checked_in?: boolean;
  status?: string;
  reason?: string;
};

export async function organizerVerifyCheckin(eventId: string, payload: CheckinPayload): Promise<CheckinVerifyResult> {
  const response = await client.post<CheckinVerifyResult>(`/api/v1/organizer/events/${eventId}/checkin/verify`, payload);
  return response.data;
}

export async function organizerCommitCheckin(eventId: string, payload: CheckinPayload): Promise<CheckinCommitResult> {
  const response = await client.post<CheckinCommitResult>(`/api/v1/organizer/events/${eventId}/checkin/commit`, payload);
  return response.data;
}

export default client;
