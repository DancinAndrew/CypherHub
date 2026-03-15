<script setup lang="ts">
import { ref } from "vue";

import {
  organizerApply,
  organizerCreateEvent,
  organizerCreateTicketType,
  organizerFetchAttendees,
  organizerFetchForms,
  organizerGetEventDetail,
  organizerResendAttendeeTicket,
  organizerUpdateEvent,
  organizerUploadEventMedia,
  organizerUpsertForm,
  organizerUpsertInternalNote,
  type AttendeeItem,
  type EventForm,
  type EventMediaItem,
  type FormSchemaDefinition,
  type OrganizerCreateEventPayload,
} from "../../api/client";
import {
  DANCE_STYLES,
  EVENT_TYPES,
  type DanceStyleKey,
  type EventTypeKey,
} from "../../constants/taxonomy";
import { toApiErrorMessage } from "../../utils/errorMessages";

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const applyForm = ref({
  name: "",
  description: "",
  contact_email: "",
  logo_url: "",
});

const eventForm = ref<OrganizerCreateEventPayload>({
  org_id: "",
  title: "",
  description: "",
  short_desc: "",
  start_at: "",
  end_at: "",
  registration_start_at: "",
  registration_end_at: "",
  timezone: "",
  location_name: "",
  location_address: "",
  map_url: "",
  contact_email: "",
  contact_phone: "",
  eligibility: "",
  event_language: "",
  checkin_open_at: "",
  checkin_note: "",
  rules: "",
  refund_policy: "",
  status: "published",
  dance_styles: [],
  event_types: [],
  socials: {},
  schedule: [],
});

const socialForm = ref({
  ig: "",
  fb: "",
  youtube: "",
  line: "",
  website: "",
});

const scheduleJson = ref("[]");
const internalNote = ref("");

const editEventId = ref("");
const ticketTypeEventId = ref("");
const ticketTypeForm = ref({
  name: "",
  description: "",
  capacity: 100,
  per_user_limit: 1,
  sale_start_at: "",
  sale_end_at: "",
  is_active: true,
});

const formEventId = ref("");
const formTicketTypeId = ref("");
const formSchemaText = ref("");
const forms = ref<EventForm[]>([]);

const attendeesEventId = ref("");
const attendeesQuery = ref("");
const attendees = ref<AttendeeItem[]>([]);
const resendAttendeeTicketId = ref<string | null>(null);
const resendAttendeeMessage = ref<string | null>(null);

const eventMediaList = ref<EventMediaItem[]>([]);
const eventMediaUploading = ref(false);
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? "";
function eventMediaUrl(path: string): string {
  if (!path) return "";
  const base = supabaseUrl.replace(/\/$/, "");
  return `${base}/storage/v1/object/public/event-media/${path}`;
}

const message = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const submitting = ref<
  "apply" | "event" | "load-event" | "internal-note" | "ticket" | "form" | "forms-load" | "attendees" | null
>(null);

function defaultFormTemplate(): FormSchemaDefinition {
  return {
    version: 1,
    fields: [
      {
        key: "full_name",
        label: "姓名",
        type: "text",
        required: true,
        placeholder: "請輸入姓名",
        help_text: "請填寫真實姓名",
        options: [],
      },
      {
        key: "phone",
        label: "聯絡電話",
        type: "phone",
        required: true,
        placeholder: "0900-000-000",
        help_text: "活動聯絡使用",
        options: [],
      },
      {
        key: "ig_account",
        label: "Instagram",
        type: "text",
        required: false,
        placeholder: "@your_handle",
        help_text: "選填",
        options: [],
      },
      {
        key: "agree_media",
        label: "同意活動影像紀錄",
        type: "checkbox",
        required: true,
        placeholder: "我同意主辦方於活動現場拍攝與使用活動紀錄",
        help_text: "必填同意條款",
        options: [],
      },
    ],
  };
}

function resetNotices(): void {
  message.value = null;
  errorMessage.value = null;
}

function isValidUuid(value: string): boolean {
  return uuidRegex.test(value.trim());
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function optionalText(value: string | undefined): string | undefined {
  if (!value) {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function toDatetimeLocal(value?: string | null): string {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  const offsetMs = parsed.getTimezoneOffset() * 60_000;
  return new Date(parsed.getTime() - offsetMs).toISOString().slice(0, 16);
}

function parseRequiredDateInput(input: string, fieldName: string): Date | null {
  if (!input) {
    errorMessage.value = `${fieldName} 為必填。`;
    return null;
  }

  const value = new Date(input);
  if (Number.isNaN(value.getTime())) {
    errorMessage.value = `${fieldName} 格式不正確，請使用日期時間選擇器。`;
    return null;
  }
  return value;
}

function parseOptionalDateInput(input: string, fieldName: string): string | undefined {
  if (!input) {
    return undefined;
  }

  const value = new Date(input);
  if (Number.isNaN(value.getTime())) {
    errorMessage.value = `${fieldName} 格式不正確，請使用日期時間選擇器。`;
    return undefined;
  }

  return value.toISOString();
}

function parseSchedule(): Array<Record<string, string>> | null {
  const raw = scheduleJson.value.trim();
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      errorMessage.value = "schedule 必須是 JSON array。";
      return null;
    }

    for (const item of parsed) {
      if (!item || typeof item !== "object") {
        errorMessage.value = "schedule 每個 item 都必須是 object（例如 {time,title,desc}）。";
        return null;
      }
    }

    return parsed as Array<Record<string, string>>;
  } catch {
    errorMessage.value = "schedule JSON 無法解析，請確認格式。";
    return null;
  }
}

function parseFormSchema(): FormSchemaDefinition | null {
  const raw = formSchemaText.value.trim();
  if (!raw) {
    errorMessage.value = "表單 schema JSON 不可為空。";
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as FormSchemaDefinition;
    if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.fields)) {
      errorMessage.value = "表單 schema 必須包含 version 與 fields array。";
      return null;
    }
    return parsed;
  } catch {
    errorMessage.value = "表單 schema JSON 無法解析，請確認格式。";
    return null;
  }
}

function getSocialsPayload(): Record<string, string> {
  const payload: Record<string, string> = {};

  for (const [key, value] of Object.entries(socialForm.value)) {
    const trimmed = value.trim();
    if (trimmed) {
      payload[key] = trimmed;
    }
  }

  return payload;
}

function toggleDanceStyle(style: DanceStyleKey): void {
  const current = eventForm.value.dance_styles || [];
  if (current.includes(style)) {
    eventForm.value.dance_styles = current.filter((item) => item !== style);
  } else {
    eventForm.value.dance_styles = [...current, style];
  }
}

function toggleEventType(type: EventTypeKey): void {
  const current = eventForm.value.event_types || [];
  if (current.includes(type)) {
    eventForm.value.event_types = current.filter((item) => item !== type);
  } else {
    eventForm.value.event_types = [...current, type];
  }
}

function formatAnswers(answers?: Record<string, unknown> | null): string {
  if (!answers || Object.keys(answers).length === 0) {
    return "-";
  }
  return JSON.stringify(answers, null, 2);
}

function useFormTemplate(): void {
  formSchemaText.value = JSON.stringify(defaultFormTemplate(), null, 2);
  message.value = "已填入報名表單模板。";
}

function buildEventPayload(requireOrgId: boolean): OrganizerCreateEventPayload | null {
  const title = eventForm.value.title.trim();
  if (!title) {
    errorMessage.value = "title 為必填。";
    return null;
  }

  const startAt = parseRequiredDateInput(eventForm.value.start_at, "start_at");
  if (!startAt) {
    return null;
  }
  const endAt = parseRequiredDateInput(eventForm.value.end_at, "end_at");
  if (!endAt) {
    return null;
  }
  if (endAt <= startAt) {
    errorMessage.value = "end_at 必須晚於 start_at。";
    return null;
  }

  const registrationStart = parseOptionalDateInput(eventForm.value.registration_start_at || "", "registration_start_at");
  if (eventForm.value.registration_start_at && !registrationStart) {
    return null;
  }
  const registrationEnd = parseOptionalDateInput(eventForm.value.registration_end_at || "", "registration_end_at");
  if (eventForm.value.registration_end_at && !registrationEnd) {
    return null;
  }
  if (registrationStart && registrationEnd && new Date(registrationEnd) <= new Date(registrationStart)) {
    errorMessage.value = "registration_end_at 必須晚於 registration_start_at。";
    return null;
  }

  const checkinOpenAt = parseOptionalDateInput(eventForm.value.checkin_open_at || "", "checkin_open_at");
  if (eventForm.value.checkin_open_at && !checkinOpenAt) {
    return null;
  }

  if (eventForm.value.contact_email && !isValidEmail(eventForm.value.contact_email)) {
    errorMessage.value = "contact_email 格式不正確。";
    return null;
  }

  const schedule = parseSchedule();
  if (!schedule) {
    return null;
  }

  const socials = getSocialsPayload();
  const payload: OrganizerCreateEventPayload = {
    org_id: requireOrgId ? eventForm.value.org_id.trim() : eventForm.value.org_id,
    title,
    description: optionalText(eventForm.value.description),
    short_desc: optionalText(eventForm.value.short_desc),
    start_at: startAt.toISOString(),
    end_at: endAt.toISOString(),
    registration_start_at: registrationStart,
    registration_end_at: registrationEnd,
    timezone: optionalText(eventForm.value.timezone),
    location_name: optionalText(eventForm.value.location_name),
    location_address: optionalText(eventForm.value.location_address),
    map_url: optionalText(eventForm.value.map_url),
    contact_email: optionalText(eventForm.value.contact_email),
    contact_phone: optionalText(eventForm.value.contact_phone),
    socials,
    eligibility: optionalText(eventForm.value.eligibility),
    event_language: optionalText(eventForm.value.event_language),
    checkin_open_at: checkinOpenAt,
    checkin_note: optionalText(eventForm.value.checkin_note),
    schedule,
    rules: optionalText(eventForm.value.rules),
    refund_policy: optionalText(eventForm.value.refund_policy),
    status: eventForm.value.status ?? "published",
    dance_styles: eventForm.value.dance_styles || [],
    event_types: eventForm.value.event_types || [],
  };

  if (Object.keys(socials).length === 0) {
    payload.socials = {};
  }

  if (requireOrgId && !isValidUuid(payload.org_id)) {
    errorMessage.value = "org_id 必須是有效 UUID。";
    return null;
  }

  return payload;
}

function syncEventIdTargets(targetEventId: string): void {
  editEventId.value = targetEventId;
  ticketTypeEventId.value = targetEventId;
  attendeesEventId.value = targetEventId;
  formEventId.value = targetEventId;
}

async function loadForms(): Promise<void> {
  resetNotices();
  const eventId = formEventId.value.trim();
  if (!isValidUuid(eventId)) {
    errorMessage.value = "讀取 forms 需要有效的 event_id（UUID）。";
    return;
  }

  submitting.value = "forms-load";
  try {
    forms.value = await organizerFetchForms(eventId);
    message.value = `Loaded ${forms.value.length} form version(s)。`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Load forms 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function submitApply(): Promise<void> {
  resetNotices();

  const orgName = applyForm.value.name.trim();
  const contactEmail = applyForm.value.contact_email.trim();

  if (!orgName) {
    errorMessage.value = "Organization name 為必填。";
    return;
  }
  if (contactEmail && !isValidEmail(contactEmail)) {
    errorMessage.value = "Contact email 格式不正確。";
    return;
  }

  submitting.value = "apply";
  try {
    const result = await organizerApply({
      name: orgName,
      description: optionalText(applyForm.value.description),
      contact_email: contactEmail || undefined,
      logo_url: optionalText(applyForm.value.logo_url),
    });
    eventForm.value.org_id = result.organization.id;
    message.value = `Organizer 建立成功。org_id=${result.organization.id}`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Apply organizer 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function loadEventForEdit(): Promise<void> {
  resetNotices();

  const targetEventId = editEventId.value.trim();
  if (!isValidUuid(targetEventId)) {
    errorMessage.value = "讀取活動需要有效的 event_id（UUID）。";
    return;
  }

  submitting.value = "load-event";
  try {
    const detail = await organizerGetEventDetail(targetEventId);
    const event = detail.event;

    eventForm.value.org_id = event.org_id;
    eventForm.value.title = event.title || "";
    eventForm.value.description = event.description || "";
    eventForm.value.short_desc = event.short_desc || "";
    eventForm.value.start_at = toDatetimeLocal(event.start_at);
    eventForm.value.end_at = toDatetimeLocal(event.end_at);
    eventForm.value.registration_start_at = toDatetimeLocal(event.registration_start_at);
    eventForm.value.registration_end_at = toDatetimeLocal(event.registration_end_at);
    eventForm.value.timezone = event.timezone || "";
    eventForm.value.location_name = event.location_name || "";
    eventForm.value.location_address = event.location_address || "";
    eventForm.value.map_url = event.map_url || "";
    eventForm.value.contact_email = event.contact_email || "";
    eventForm.value.contact_phone = event.contact_phone || "";
    eventForm.value.eligibility = event.eligibility || "";
    eventForm.value.event_language = event.event_language || "";
    eventForm.value.checkin_open_at = toDatetimeLocal(event.checkin_open_at);
    eventForm.value.checkin_note = event.checkin_note || "";
    eventForm.value.rules = event.rules || "";
    eventForm.value.refund_policy = event.refund_policy || "";
    eventForm.value.status = event.status === "draft" ? "draft" : "published";
    eventForm.value.dance_styles = event.dance_styles || [];
    eventForm.value.event_types = event.event_types || [];

    const socials = event.socials || {};
    socialForm.value = {
      ig: socials.ig || "",
      fb: socials.fb || "",
      youtube: socials.youtube || "",
      line: socials.line || "",
      website: socials.website || "",
    };

    scheduleJson.value = JSON.stringify(event.schedule || [], null, 2);
    internalNote.value = detail.internal_note || "";
    eventMediaList.value = detail.event_media ?? [];
    syncEventIdTargets(targetEventId);
    await loadForms();
    message.value = `已載入活動資料。event_id=${targetEventId}`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Load event 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function submitEvent(): Promise<void> {
  resetNotices();
  const payload = buildEventPayload(true);
  if (!payload) {
    return;
  }

  submitting.value = "event";
  try {
    const result = await organizerCreateEvent(payload);
    const createdEventId = result.event.id;
    syncEventIdTargets(createdEventId);
    await organizerUpsertInternalNote(createdEventId, internalNote.value || "");
    message.value = `Event 建立成功。event_id=${createdEventId}`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Create event 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function submitEventUpdate(): Promise<void> {
  resetNotices();
  const targetEventId = editEventId.value.trim();
  if (!isValidUuid(targetEventId)) {
    errorMessage.value = "更新活動需要有效的 event_id（UUID）。";
    return;
  }

  const payload = buildEventPayload(false);
  if (!payload) {
    return;
  }

  submitting.value = "event";
  try {
    const { org_id: _unused, ...updatePayload } = payload;
    const result = await organizerUpdateEvent(targetEventId, updatePayload);
    await organizerUpsertInternalNote(targetEventId, internalNote.value || "");
    syncEventIdTargets(targetEventId);
    message.value = `Event 更新成功。event_id=${result.event.id}`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Update event 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function saveInternalNoteOnly(): Promise<void> {
  resetNotices();
  const targetEventId = editEventId.value.trim();
  if (!isValidUuid(targetEventId)) {
    errorMessage.value = "儲存 internal note 前，請先填有效 event_id（UUID）。";
    return;
  }

  submitting.value = "internal-note";
  try {
    await organizerUpsertInternalNote(targetEventId, internalNote.value || "");
    message.value = `Internal note 已更新。event_id=${targetEventId}`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "更新 internal note 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function submitEventForm(): Promise<void> {
  resetNotices();
  const eventId = formEventId.value.trim();
  if (!isValidUuid(eventId)) {
    errorMessage.value = "建立 form 需要有效的 event_id（UUID）。";
    return;
  }
  if (formTicketTypeId.value.trim() && !isValidUuid(formTicketTypeId.value)) {
    errorMessage.value = "ticket_type_id 若填寫，必須是有效 UUID。";
    return;
  }

  const schema = parseFormSchema();
  if (!schema) {
    return;
  }

  submitting.value = "form";
  try {
    const savedForm = await organizerUpsertForm(eventId, {
      ticket_type_id: formTicketTypeId.value.trim() || null,
      schema,
      is_active: true,
    });
    await loadForms();
    message.value = `Form schema 已儲存。form_id=${savedForm.id}`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Save form schema 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function submitTicketType(): Promise<void> {
  resetNotices();
  const eventId = ticketTypeEventId.value.trim();
  const ticketTypeName = ticketTypeForm.value.name.trim();

  if (!isValidUuid(eventId)) {
    errorMessage.value = "event_id 必須是有效 UUID。";
    return;
  }
  if (!ticketTypeName) {
    errorMessage.value = "ticket type name 為必填。";
    return;
  }
  if (ticketTypeForm.value.capacity <= 0) {
    errorMessage.value = "capacity 必須大於 0。";
    return;
  }
  if (ticketTypeForm.value.per_user_limit < 1) {
    errorMessage.value = "per_user_limit 至少為 1。";
    return;
  }

  submitting.value = "ticket";
  try {
    const result = await organizerCreateTicketType(eventId, {
      name: ticketTypeName,
      description: optionalText(ticketTypeForm.value.description),
      capacity: ticketTypeForm.value.capacity,
      per_user_limit: ticketTypeForm.value.per_user_limit,
      sale_start_at: ticketTypeForm.value.sale_start_at
        ? new Date(ticketTypeForm.value.sale_start_at).toISOString()
        : undefined,
      sale_end_at: ticketTypeForm.value.sale_end_at
        ? new Date(ticketTypeForm.value.sale_end_at).toISOString()
        : undefined,
      is_active: ticketTypeForm.value.is_active,
    });
    message.value = `Ticket type 建立成功。ticket_type_id=${result.ticket_type.id}`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Create ticket type 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function loadAttendees(): Promise<void> {
  resetNotices();
  const eventId = attendeesEventId.value.trim();
  if (!isValidUuid(eventId)) {
    errorMessage.value = "Attendees 查詢需要有效的 event_id（UUID）。";
    return;
  }

  submitting.value = "attendees";
  try {
    attendees.value = await organizerFetchAttendees(eventId, attendeesQuery.value || undefined);
    message.value = `Loaded ${attendees.value.length} attendee record(s)。`;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Load attendees 失敗。");
  } finally {
    submitting.value = null;
  }
}

async function handleResendAttendeeTicket(ticketId: string): Promise<void> {
  const eventId = attendeesEventId.value.trim();
  if (!eventId || !isValidUuid(eventId)) {
    resendAttendeeMessage.value = "請先輸入並載入活動的 event_id。";
    return;
  }
  resendAttendeeMessage.value = null;
  resendAttendeeTicketId.value = ticketId;
  try {
    await organizerResendAttendeeTicket(eventId, ticketId);
    resendAttendeeMessage.value = "已重寄票券信至參加者信箱。";
  } catch (error: unknown) {
    resendAttendeeMessage.value = toApiErrorMessage(error, "重寄失敗");
  } finally {
    resendAttendeeTicketId.value = null;
  }
}

async function handleUploadEventMedia(event: Event): Promise<void> {
  const targetEventId = editEventId.value.trim();
  if (!targetEventId || !isValidUuid(targetEventId)) {
    message.value = "請先載入要編輯的活動。";
    return;
  }
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    errorMessage.value = "請選擇圖片檔（JPEG/PNG/WebP/GIF）。";
    return;
  }
  eventMediaUploading.value = true;
  errorMessage.value = null;
  try {
    const media = await organizerUploadEventMedia(targetEventId, file);
    eventMediaList.value = [...eventMediaList.value, media];
    message.value = "已上傳活動圖片。";
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "上傳失敗");
  } finally {
    eventMediaUploading.value = false;
    input.value = "";
  }
}

formSchemaText.value = JSON.stringify(defaultFormTemplate(), null, 2);
</script>

<template>
  <main class="mx-auto w-full max-w-6xl space-y-6 px-4 py-10">
    <h1 class="text-3xl font-bold text-slate-900">Organizer Management</h1>

    <section class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
      <p class="font-semibold">MVP-1.5-B 使用順序</p>
      <p>1) 先 Apply Organizer，建立活動與免費票種。</p>
      <p>2) 在 Form Builder 區塊設定 event-level 或 ticket-type-level schema。</p>
      <p>3) User 報名後，attendees 名單會看到 answers。</p>
      <p>4) Internal note 仍獨立儲存，不會出現在 public event detail。</p>
    </section>

    <p v-if="message" class="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{{ message }}</p>
    <p v-if="errorMessage" class="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{{ errorMessage }}</p>

    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900">1) Apply Organizer</h2>
      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <input v-model="applyForm.name" placeholder="Organization name" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="applyForm.contact_email" type="email" placeholder="Contact email" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="applyForm.logo_url" placeholder="Logo URL" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="applyForm.description" placeholder="Description" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <button class="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white" :disabled="submitting === 'apply'" @click="submitApply">
        {{ submitting === "apply" ? "Submitting..." : "Submit Organizer Apply" }}
      </button>
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900">2) Create / Update Event</h2>
      <div class="mt-4 flex flex-wrap items-center gap-3">
        <input v-model="editEventId" placeholder="event_id for update (UUID)" class="w-full rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm md:w-96" />
        <button class="rounded-lg border border-amber-500 px-4 py-2 text-sm font-semibold text-amber-700" :disabled="submitting === 'load-event'" @click="loadEventForEdit">
          {{ submitting === "load-event" ? "Loading..." : "Load Event" }}
        </button>
      </div>

      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <input v-model="eventForm.org_id" placeholder="org_id (UUID)" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.title" placeholder="title" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.short_desc" placeholder="short_desc" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.event_language" placeholder="event_language" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.start_at" type="datetime-local" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.end_at" type="datetime-local" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.registration_start_at" type="datetime-local" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.registration_end_at" type="datetime-local" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.checkin_open_at" type="datetime-local" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.timezone" placeholder="timezone" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.location_name" placeholder="location_name" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.location_address" placeholder="location_address" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.map_url" placeholder="map_url" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.contact_email" type="email" placeholder="contact_email" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="eventForm.contact_phone" placeholder="contact_phone" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <select v-model="eventForm.status" class="rounded-lg border border-slate-300 px-3 py-2 text-sm">
          <option value="published">published</option>
          <option value="draft">draft</option>
        </select>
      </div>

      <div class="mt-3 grid gap-3 md:grid-cols-2">
        <textarea v-model="eventForm.description" rows="3" placeholder="description" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <textarea v-model="eventForm.eligibility" rows="3" placeholder="eligibility" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <textarea v-model="eventForm.checkin_note" rows="3" placeholder="checkin_note" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <textarea v-model="eventForm.rules" rows="3" placeholder="rules" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <textarea v-model="eventForm.refund_policy" rows="3" placeholder="refund_policy" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <textarea v-model="scheduleJson" rows="3" placeholder='schedule JSON，例如 [{"time":"13:00","title":"Check-in","desc":"Open gate"}]' class="rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs" />
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold text-slate-500">Social Links</p>
        <div class="mt-2 grid gap-3 md:grid-cols-2">
          <input v-model="socialForm.ig" placeholder="IG URL" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input v-model="socialForm.fb" placeholder="Facebook URL" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input v-model="socialForm.youtube" placeholder="YouTube URL" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input v-model="socialForm.line" placeholder="LINE URL" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input v-model="socialForm.website" placeholder="Website URL" class="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2" />
        </div>
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold text-slate-500">Dance Styles</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <button v-for="style in DANCE_STYLES" :key="style.key" type="button" class="rounded-full border px-3 py-1 text-xs font-semibold" :class="(eventForm.dance_styles || []).includes(style.key) ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-slate-300 text-slate-600'" @click="toggleDanceStyle(style.key)">
            {{ style.label }}
          </button>
        </div>
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold text-slate-500">Event Types</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <button v-for="type in EVENT_TYPES" :key="type.key" type="button" class="rounded-full border px-3 py-1 text-xs font-semibold" :class="(eventForm.event_types || []).includes(type.key) ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-slate-300 text-slate-600'" @click="toggleEventType(type.key)">
            {{ type.label }}
          </button>
        </div>
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold text-slate-500">Internal Note</p>
        <textarea v-model="internalNote" rows="4" placeholder="internal note" class="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
      </div>

      <div class="mt-4 flex flex-wrap gap-3">
        <button class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white" :disabled="submitting === 'event'" @click="submitEvent">
          {{ submitting === "event" ? "Creating..." : "Create Event" }}
        </button>
        <button class="rounded-lg border border-brand-600 px-4 py-2 text-sm font-semibold text-brand-700" :disabled="submitting === 'event'" @click="submitEventUpdate">
          {{ submitting === "event" ? "Updating..." : "Update Event" }}
        </button>
        <button class="rounded-lg border border-slate-500 px-4 py-2 text-sm font-semibold text-slate-700" :disabled="submitting === 'internal-note'" @click="saveInternalNoteOnly">
          {{ submitting === "internal-note" ? "Saving Note..." : "Save Internal Note Only" }}
        </button>
      </div>
    </section>

    <section v-if="editEventId.trim()" class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900">活動圖片</h2>
      <p class="mt-1 text-xs text-slate-500">上傳後會顯示於活動詳情頁輪播。限 JPEG/PNG/WebP/GIF，單檔 5MB。</p>
      <div class="mt-3 flex flex-wrap items-center gap-3">
        <label class="cursor-pointer rounded-lg border border-brand-600 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50">
          <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" class="hidden" :disabled="eventMediaUploading" @change="handleUploadEventMedia" />
          {{ eventMediaUploading ? "上傳中…" : "選擇圖片上傳" }}
        </label>
      </div>
      <div v-if="eventMediaList.length > 0" class="mt-4 flex flex-wrap gap-3">
        <div v-for="item in eventMediaList" :key="item.id" class="overflow-hidden rounded-lg border border-slate-200">
          <img :src="eventMediaUrl(item.path)" :alt="item.path" class="h-24 w-32 object-cover" />
          <p class="truncate px-2 py-1 text-xs text-slate-500">{{ item.path }}</p>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900">3) Form Builder (JSON Schema)</h2>
      <p class="mt-1 text-xs text-slate-500">
        可設定 event-level form（ticket_type_id 留空）或 ticket-type-level form。先用 JSON editor，不做拖拉 UI。
      </p>
      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <input v-model="formEventId" placeholder="event_id (UUID)" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="formTicketTypeId" placeholder="ticket_type_id (optional UUID)" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div class="mt-3 flex flex-wrap gap-3">
        <button class="rounded-lg border border-slate-400 px-4 py-2 text-sm font-semibold text-slate-700" @click="useFormTemplate">Use Template</button>
        <button class="rounded-lg border border-slate-400 px-4 py-2 text-sm font-semibold text-slate-700" :disabled="submitting === 'forms-load'" @click="loadForms">
          {{ submitting === "forms-load" ? "Loading..." : "Load Forms" }}
        </button>
        <button class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white" :disabled="submitting === 'form'" @click="submitEventForm">
          {{ submitting === "form" ? "Saving..." : "Save Form Schema" }}
        </button>
      </div>
      <textarea v-model="formSchemaText" rows="14" class="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs" />

      <div class="mt-4 rounded-lg border border-slate-200">
        <table class="min-w-full text-sm">
          <thead class="bg-slate-100 text-left text-slate-600">
            <tr>
              <th class="px-3 py-2">form_id</th>
              <th class="px-3 py-2">ticket_type_id</th>
              <th class="px-3 py-2">version</th>
              <th class="px-3 py-2">active</th>
              <th class="px-3 py-2">fields</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="form in forms" :key="form.id" class="border-t border-slate-200">
              <td class="px-3 py-2 font-mono text-xs">{{ form.id }}</td>
              <td class="px-3 py-2 font-mono text-xs">{{ form.ticket_type_id || 'event-level' }}</td>
              <td class="px-3 py-2">{{ form.version }}</td>
              <td class="px-3 py-2">{{ form.is_active ? 'true' : 'false' }}</td>
              <td class="px-3 py-2">{{ form.schema.fields.length }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900">4) Create Ticket Type (free)</h2>
      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <input v-model="ticketTypeEventId" placeholder="event_id (UUID)" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model="ticketTypeForm.name" placeholder="ticket type name" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model.number="ticketTypeForm.capacity" type="number" min="1" placeholder="capacity" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input v-model.number="ticketTypeForm.per_user_limit" type="number" min="1" placeholder="per_user_limit" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <button class="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white" :disabled="submitting === 'ticket'" @click="submitTicketType">
        {{ submitting === "ticket" ? "Creating..." : "Create Ticket Type" }}
      </button>
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900">5) Attendees List</h2>
      <div class="mt-4 flex flex-wrap gap-3">
        <input v-model="attendeesEventId" placeholder="event_id (UUID)" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm md:w-72" />
        <input v-model="attendeesQuery" placeholder="query (optional)" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm md:w-72" />
        <button class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white" :disabled="submitting === 'attendees'" @click="loadAttendees">
          {{ submitting === "attendees" ? "Loading..." : "Load Attendees" }}
        </button>
      </div>

      <div class="mt-4 overflow-auto rounded-lg border border-slate-200">
        <p v-if="resendAttendeeMessage" class="mt-2 text-sm" :class="resendAttendeeMessage.startsWith('已') ? 'text-emerald-600' : 'text-rose-600'">
          {{ resendAttendeeMessage }}
        </p>
        <table class="min-w-full text-sm">
          <thead class="bg-slate-100 text-left text-slate-600">
            <tr>
              <th class="px-3 py-2">ticket_id</th>
              <th class="px-3 py-2">user_id</th>
              <th class="px-3 py-2">status</th>
              <th class="px-3 py-2">checked_in_at</th>
              <th class="px-3 py-2">answers</th>
              <th class="px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in attendees" :key="row.ticket_id" class="border-t border-slate-200 align-top">
              <td class="px-3 py-2 font-mono text-xs">{{ row.ticket_id }}</td>
              <td class="px-3 py-2 font-mono text-xs">{{ row.user_id }}</td>
              <td class="px-3 py-2">{{ row.status }}</td>
              <td class="px-3 py-2">{{ row.checked_in_at || '-' }}</td>
              <td class="px-3 py-2">
                <pre class="whitespace-pre-wrap break-all text-xs text-slate-600">{{ formatAnswers(row.answers) }}</pre>
              </td>
              <td class="px-3 py-2">
                <button
                  v-if="row.status !== 'cancelled'"
                  type="button"
                  class="rounded border border-brand-600 px-2 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-50"
                  :disabled="resendAttendeeTicketId === row.ticket_id"
                  @click="handleResendAttendeeTicket(row.ticket_id)"
                >
                  {{ resendAttendeeTicketId === row.ticket_id ? "寄送中…" : "重寄票券" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>
