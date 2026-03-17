<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  fetchMyOrganizerSummary,
  organizerCreateEvent,
  organizerCreateTicketType,
  organizerDeleteTicketType,
  organizerGetEventDetail,
  organizerUpdateEvent,
  organizerUploadEventMedia,
  organizerUpsertInternalNote,
  organizerUpdateTicketType,
  type EventMediaItem,
  type MyOrganizerEvent,
  type MyOrganizerOrg,
  type OrganizerCreateEventPayload,
  type TicketType,
} from "../../api/client";
import {
  DANCE_STYLES,
  EVENT_TYPES,
  type DanceStyleKey,
  type EventTypeKey,
} from "../../constants/taxonomy";
import { useOrganizerStore } from "../../stores/organizer";
import { toApiErrorMessage } from "../../utils/errorMessages";

const route = useRoute();
const router = useRouter();
const organizerStore = useOrganizerStore();

const isCreatePage = computed(() => (route.meta.eventMode as string) === "create");
const isEditPage = computed(() => (route.meta.eventMode as string) === "edit");

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const myOrgs = ref<MyOrganizerOrg[]>([]);
const myEvents = ref<MyOrganizerEvent[]>([]);
const summaryLoading = ref(true);

const mode = ref<"create" | "edit">("create");
const editEventId = ref("");
const eventForm = ref<OrganizerCreateEventPayload>({
  org_id: organizerStore.orgId || "",
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
const socialForm = ref({ ig: "", fb: "", youtube: "", line: "", website: "" });
const scheduleJson = ref("[]");
const internalNote = ref("");

const ticketTypeForm = ref({
  name: "",
  description: "",
  capacity: 100,
  per_user_limit: 1,
  sale_start_at: "",
  sale_end_at: "",
  is_active: true,
});

const message = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const submitting = ref<"event" | "load" | "ticket" | "ticket-edit" | "ticket-delete" | null>(null);
const originalStartAt = ref("");
const originalEndAt = ref("");

const eventMediaList = ref<EventMediaItem[]>([]);
const ticketTypesList = ref<TicketType[]>([]);
const editingTicketTypeId = ref<string | null>(null);
const editTicketTypeForm = ref({
  name: "",
  description: "",
  capacity: 100,
  per_user_limit: 1,
  sale_start_at: "",
  sale_end_at: "",
  is_active: true,
});
const eventMediaUploading = ref(false);
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? "";
function eventMediaUrl(path: string): string {
  if (!path) return "";
  const base = supabaseUrl.replace(/\/$/, "");
  return `${base}/storage/v1/object/public/event-media/${path}`;
}

eventForm.value.org_id = organizerStore.orgId || "";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  published: "已上架",
  ended: "已結束",
  cancelled: "已取消",
  disabled: "已下架",
};
function formatEventOption(ev: MyOrganizerEvent): string {
  const date = ev.start_at ? new Date(ev.start_at).toLocaleDateString(undefined, { dateStyle: "short" }) : "";
  const status = STATUS_LABELS[ev.status ?? ""] ?? ev.status ?? "草稿";
  return `${ev.title}（${date}・${status}）`;
}

onMounted(async () => {
  summaryLoading.value = true;
  try {
    const data = await fetchMyOrganizerSummary();
    myOrgs.value = data.organizations ?? [];
    myEvents.value = data.events ?? [];
    const firstOrg = myOrgs.value[0];
    if (firstOrg && !eventForm.value.org_id) eventForm.value.org_id = firstOrg.id;
  } catch {
    myOrgs.value = [];
    myEvents.value = [];
  } finally {
    summaryLoading.value = false;
    if (!isCreatePage.value) {
      const paramId = route.params.eventId && typeof route.params.eventId === "string" ? route.params.eventId : "";
      if (paramId && isValidUuid(paramId) && myEvents.value.some((e) => e.id === paramId)) {
        editEventId.value = paramId;
        loadEvent();
      }
    }
  }
});

function optionalText(v: string | undefined): string | undefined {
  if (!v) return undefined;
  const t = v.trim();
  return t.length > 0 ? t : undefined;
}
function toDatetimeLocal(v?: string | null): string {
  if (!v) return "";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return "";
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}
function parseDate(input: string, fieldName: string): Date | null {
  if (!input) {
    errorMessage.value = `${fieldName} 為必填。`;
    return null;
  }
  const d = new Date(input);
  if (Number.isNaN(d.getTime())) {
    errorMessage.value = `${fieldName} 格式不正確。`;
    return null;
  }
  return d;
}
function parseOptionalDate(input: string): string | undefined {
  if (!input) return undefined;
  const d = new Date(input);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
}
function parseSchedule(): Array<Record<string, string>> | null {
  const raw = scheduleJson.value.trim();
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      errorMessage.value = "schedule 必須是 JSON array。";
      return null;
    }
    return parsed as Array<Record<string, string>>;
  } catch {
    errorMessage.value = "schedule JSON 無法解析。";
    return null;
  }
}
function getSocials(): Record<string, string> {
  const p: Record<string, string> = {};
  for (const [k, v] of Object.entries(socialForm.value)) {
    const t = (v as string).trim();
    if (t) p[k] = t;
  }
  return p;
}
function toggleDanceStyle(s: DanceStyleKey) {
  const arr = eventForm.value.dance_styles || [];
  eventForm.value.dance_styles = arr.includes(s) ? arr.filter((x) => x !== s) : [...arr, s];
}
function toggleEventType(t: EventTypeKey) {
  const arr = eventForm.value.event_types || [];
  eventForm.value.event_types = arr.includes(t) ? arr.filter((x) => x !== t) : [...arr, t];
}
function isValidUuid(s: string) {
  return uuidRegex.test(s.trim());
}
function isValidEmail(s: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s.trim());
}

function buildPayload(requireOrgId: boolean): OrganizerCreateEventPayload | null {
  const title = eventForm.value.title.trim();
  if (!title) {
    errorMessage.value = "活動名稱為必填。";
    return null;
  }
  const startAt = parseDate(eventForm.value.start_at, "活動開始時間");
  const endAt = parseDate(eventForm.value.end_at, "活動結束時間");
  if (!startAt || !endAt) return null;
  if (endAt <= startAt) {
    errorMessage.value = "結束時間必須晚於開始時間。";
    return null;
  }
  if (eventForm.value.contact_email && !isValidEmail(eventForm.value.contact_email)) {
    errorMessage.value = "聯絡信箱格式不正確。";
    return null;
  }
  const schedule = parseSchedule();
  if (schedule === null) return null;
  const socials = getSocials();
  const payload: OrganizerCreateEventPayload = {
    org_id: eventForm.value.org_id,
    title,
    description: optionalText(eventForm.value.description),
    short_desc: optionalText(eventForm.value.short_desc),
    start_at: startAt.toISOString(),
    end_at: endAt.toISOString(),
    registration_start_at: parseOptionalDate(eventForm.value.registration_start_at || ""),
    registration_end_at: parseOptionalDate(eventForm.value.registration_end_at || ""),
    timezone: optionalText(eventForm.value.timezone),
    location_name: optionalText(eventForm.value.location_name),
    location_address: optionalText(eventForm.value.location_address),
    map_url: optionalText(eventForm.value.map_url),
    contact_email: optionalText(eventForm.value.contact_email),
    contact_phone: optionalText(eventForm.value.contact_phone),
    socials,
    eligibility: optionalText(eventForm.value.eligibility),
    event_language: optionalText(eventForm.value.event_language),
    checkin_open_at: parseOptionalDate(eventForm.value.checkin_open_at || ""),
    checkin_note: optionalText(eventForm.value.checkin_note),
    schedule,
    rules: optionalText(eventForm.value.rules),
    refund_policy: optionalText(eventForm.value.refund_policy),
    status: eventForm.value.status ?? "published",
    dance_styles: eventForm.value.dance_styles || [],
    event_types: eventForm.value.event_types || [],
  };
  if (requireOrgId && !payload.org_id?.trim()) {
    errorMessage.value = "請選擇主辦方。";
    return null;
  }
  return payload;
}

async function loadEvent() {
  message.value = null;
  errorMessage.value = null;
  const id = editEventId.value.trim();
  if (!id) return;
  submitting.value = "load";
  try {
    const detail = await organizerGetEventDetail(id);
    const e = detail.event;
    eventForm.value.org_id = e.org_id;
    eventForm.value.title = e.title || "";
    eventForm.value.description = e.description || "";
    eventForm.value.short_desc = e.short_desc || "";
    eventForm.value.start_at = toDatetimeLocal(e.start_at);
    eventForm.value.end_at = toDatetimeLocal(e.end_at);
    eventForm.value.registration_start_at = toDatetimeLocal(e.registration_start_at);
    eventForm.value.registration_end_at = toDatetimeLocal(e.registration_end_at);
    eventForm.value.timezone = e.timezone || "";
    eventForm.value.location_name = e.location_name || "";
    eventForm.value.location_address = e.location_address || "";
    eventForm.value.map_url = e.map_url || "";
    eventForm.value.contact_email = e.contact_email || "";
    eventForm.value.contact_phone = e.contact_phone || "";
    eventForm.value.eligibility = e.eligibility || "";
    eventForm.value.event_language = e.event_language || "";
    eventForm.value.checkin_open_at = toDatetimeLocal(e.checkin_open_at);
    eventForm.value.checkin_note = e.checkin_note || "";
    eventForm.value.rules = e.rules || "";
    eventForm.value.refund_policy = e.refund_policy || "";
    const validStatuses = ["draft", "published", "ended", "cancelled", "disabled"] as const;
    eventForm.value.status = validStatuses.includes(e.status as (typeof validStatuses)[number]) ? (e.status as (typeof validStatuses)[number]) : "draft";
    eventForm.value.dance_styles = e.dance_styles || [];
    eventForm.value.event_types = e.event_types || [];
    const so = e.socials || {};
    socialForm.value = {
      ig: so.ig || "",
      fb: so.fb || "",
      youtube: so.youtube || "",
      line: so.line || "",
      website: so.website || "",
    };
    scheduleJson.value = JSON.stringify(e.schedule || [], null, 2);
    internalNote.value = detail.internal_note || "";
    eventMediaList.value = detail.event_media ?? [];
    ticketTypesList.value = detail.ticket_types ?? [];
    mode.value = "edit";
    editEventId.value = id;
    originalStartAt.value = eventForm.value.start_at || "";
    originalEndAt.value = eventForm.value.end_at || "";
    message.value = "已載入活動資料。";
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "載入活動失敗。");
  } finally {
    submitting.value = null;
  }
}

async function submitCreate() {
  message.value = null;
  errorMessage.value = null;
  const payload = buildPayload(true);
  if (!payload) return;
  submitting.value = "event";
  try {
    const result = await organizerCreateEvent(payload);
    const id = result.event.id;
    organizerStore.setLastEventId(id);
    await organizerUpsertInternalNote(id, internalNote.value || "");
    message.value = "活動建立成功！可於下方「活動圖片」區上傳圖片。";
    editEventId.value = id;
    mode.value = "edit";
    eventMediaList.value = [];
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "建立活動失敗。");
  } finally {
    submitting.value = null;
  }
}

async function submitUpdate() {
  message.value = null;
  errorMessage.value = null;
  const id = editEventId.value.trim();
  if (!isValidUuid(id)) {
    errorMessage.value = "請先載入要編輯的活動。";
    return;
  }
  if (["published", "ended", "cancelled"].includes(eventForm.value.status ?? "")) {
    const startChanged = eventForm.value.start_at !== originalStartAt.value;
    const endChanged = eventForm.value.end_at !== originalEndAt.value;
    if (startChanged || endChanged) {
      const ok = window.confirm("此活動已上架，修改活動時間可能影響已報名參加者。確定要儲存嗎？");
      if (!ok) return;
    }
  }
  const payload = buildPayload(false);
  if (!payload) return;
  submitting.value = "event";
  try {
    const { org_id: _o, ...rest } = payload;
    await organizerUpdateEvent(id, rest);
    await organizerUpsertInternalNote(id, internalNote.value || "");
    message.value = "活動已更新。";
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "更新活動失敗。");
  } finally {
    submitting.value = null;
  }
}

async function handleUploadEventMedia(e: Event): Promise<void> {
  const id = editEventId.value.trim();
  if (!isValidUuid(id)) {
    errorMessage.value = "請先載入要編輯的活動。";
    return;
  }
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    errorMessage.value = "請選擇圖片檔（JPEG/PNG/WebP/GIF）。";
    return;
  }
  eventMediaUploading.value = true;
  errorMessage.value = null;
  try {
    const media = await organizerUploadEventMedia(id, file);
    eventMediaList.value = [...eventMediaList.value, media];
    message.value = "已上傳活動圖片。";
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "上傳失敗");
  } finally {
    eventMediaUploading.value = false;
    input.value = "";
  }
}

async function submitTicketType() {
  message.value = null;
  errorMessage.value = null;
  const eventId = editEventId.value.trim();
  const name = ticketTypeForm.value.name.trim();
  if (!isValidUuid(eventId)) {
    errorMessage.value = "請先建立或載入活動。";
    return;
  }
  if (!name) {
    errorMessage.value = "票種名稱為必填。";
    return;
  }
  if (ticketTypeForm.value.capacity <= 0) {
    errorMessage.value = "名額必須大於 0。";
    return;
  }
  if (ticketTypeForm.value.per_user_limit < 1) {
    errorMessage.value = "每人限購至少為 1。";
    return;
  }
  submitting.value = "ticket";
  try {
    await organizerCreateTicketType(eventId, {
      name,
      description: optionalText(ticketTypeForm.value.description),
      capacity: ticketTypeForm.value.capacity,
      per_user_limit: ticketTypeForm.value.per_user_limit,
      sale_start_at: ticketTypeForm.value.sale_start_at ? new Date(ticketTypeForm.value.sale_start_at).toISOString() : undefined,
      sale_end_at: ticketTypeForm.value.sale_end_at ? new Date(ticketTypeForm.value.sale_end_at).toISOString() : undefined,
      is_active: ticketTypeForm.value.is_active,
    });
    message.value = "票種建立成功！";
    ticketTypeForm.value.name = "";
    ticketTypeForm.value.description = "";
    ticketTypeForm.value.capacity = 100;
    ticketTypeForm.value.per_user_limit = 1;
    await loadEvent();
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "建立票種失敗。");
  } finally {
    submitting.value = null;
  }
}

function startEditTicketType(tt: TicketType) {
  editingTicketTypeId.value = tt.id;
  editTicketTypeForm.value = {
    name: tt.name,
    description: tt.description || "",
    capacity: tt.capacity,
    per_user_limit: tt.per_user_limit,
    sale_start_at: toDatetimeLocal(tt.sale_start_at),
    sale_end_at: toDatetimeLocal(tt.sale_end_at),
    is_active: tt.is_active,
  };
}

function cancelEditTicketType() {
  editingTicketTypeId.value = null;
}

async function handleUpdateTicketType() {
  const eventId = editEventId.value.trim();
  const ticketTypeId = editingTicketTypeId.value;
  if (!isValidUuid(eventId) || !ticketTypeId) return;
  const name = editTicketTypeForm.value.name.trim();
  if (!name) {
    errorMessage.value = "票種名稱為必填。";
    return;
  }
  const tt = ticketTypesList.value.find((t) => t.id === ticketTypeId);
  if (tt && editTicketTypeForm.value.capacity < tt.sold_count) {
    errorMessage.value = "名額不可小於已售出數量。";
    return;
  }
  if (editTicketTypeForm.value.per_user_limit < 1) {
    errorMessage.value = "每人限購至少為 1。";
    return;
  }
  message.value = null;
  errorMessage.value = null;
  submitting.value = "ticket";
  try {
    const payload: Record<string, unknown> = {
      name,
      description: optionalText(editTicketTypeForm.value.description),
      capacity: editTicketTypeForm.value.capacity,
      per_user_limit: editTicketTypeForm.value.per_user_limit,
      is_active: editTicketTypeForm.value.is_active,
    };
    if (editTicketTypeForm.value.sale_start_at) {
      payload.sale_start_at = new Date(editTicketTypeForm.value.sale_start_at).toISOString();
    } else {
      payload.sale_start_at = null;
    }
    if (editTicketTypeForm.value.sale_end_at) {
      payload.sale_end_at = new Date(editTicketTypeForm.value.sale_end_at).toISOString();
    } else {
      payload.sale_end_at = null;
    }
    await organizerUpdateTicketType(eventId, ticketTypeId, payload as Parameters<typeof organizerUpdateTicketType>[2]);
    message.value = "票種已更新。";
    editingTicketTypeId.value = null;
    await loadEvent();
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "更新票種失敗。");
  } finally {
    submitting.value = null;
  }
}

async function handleDeleteTicketType(tt: TicketType) {
  if (tt.sold_count > 0) {
    errorMessage.value = "已售出票種不可刪除。";
    return;
  }
  if (!window.confirm(`確定要刪除票種「${tt.name}」嗎？`)) return;
  const eventId = editEventId.value.trim();
  if (!isValidUuid(eventId)) return;
  message.value = null;
  errorMessage.value = null;
  submitting.value = "ticket";
  try {
    await organizerDeleteTicketType(eventId, tt.id);
    message.value = "票種已刪除。";
    await loadEvent();
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "刪除票種失敗。");
  } finally {
    submitting.value = null;
  }
}

</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-10">
    <div class="mb-8">
      <router-link to="/organizer" class="link-back">← 回主辦方主頁</router-link>
    </div>

    <h1 class="font-display text-3xl font-bold tracking-tight text-gray-900">{{ isCreatePage ? "步驟 2：建立活動" : "步驟 3：編輯活動" }}</h1>
    <p class="mt-2 text-gray-600">
      {{ isCreatePage ? "填寫活動資料與票種，建立新活動。" : "從下拉選擇既有活動載入後編輯。" }}
    </p>

    <!-- Load Event (edit only) -->
    <section v-if="isEditPage" class="card mt-6 p-6">
      <h2 class="font-display text-lg font-semibold text-gray-800">載入既有活動</h2>
      <div class="mt-3 flex flex-wrap items-center gap-3">
        <select
          v-model="editEventId"
          class="input-field min-w-[280px]"
          :disabled="summaryLoading"
          @change="editEventId && loadEvent()"
        >
          <option value="">— 請選擇活動 —</option>
          <option v-for="ev in myEvents" :key="ev.id" :value="ev.id">
            {{ formatEventOption(ev) }}
          </option>
        </select>
        <button
          class="btn-secondary disabled:opacity-50"
          :disabled="submitting === 'load' || !editEventId"
          @click="loadEvent"
        >
          {{ submitting === "load" ? "載入中..." : "載入活動" }}
        </button>
      </div>
      <p v-if="summaryLoading" class="mt-2 text-sm text-gray-500">載入活動列表中…</p>
      <p v-else-if="myEvents.length === 0" class="mt-2 text-sm text-gray-500">尚無活動，請先至「建立活動」建立。</p>
    </section>

    <!-- Event Form -->
    <section class="card mt-6 p-6">
      <div
        v-if="mode === 'edit' && ['published', 'ended', 'cancelled'].includes(eventForm.status ?? '')"
        class="mb-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-300"
      >
        此活動已上架或已結束。修改活動時間、報名時間等欄位時請特別留意，可能影響已報名參加者。
      </div>
      <h2 class="font-display text-lg font-semibold text-gray-800">活動資料</h2>
      <div class="mt-4 space-y-4">
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-600">主辦方 *</label>
          <select
            v-model="eventForm.org_id"
            class="input-field w-full"
            :disabled="summaryLoading || mode === 'edit'"
          >
            <option value="">— 請選擇主辦方 —</option>
            <option v-for="org in myOrgs" :key="org.id" :value="org.id">
              {{ org.name }}（{{ org.role }}）
            </option>
          </select>
          <p v-if="summaryLoading" class="mt-1 text-xs text-gray-500">載入主辦方列表中…</p>
          <p v-else-if="myOrgs.length === 0" class="mt-1 text-xs text-amber-600">尚無主辦方，請先完成步驟 1 申請主辦方。</p>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-600">活動名稱 *</label>
            <input v-model="eventForm.title" placeholder="活動標題" class="input-field w-full" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-600">狀態</label>
            <select v-model="eventForm.status" class="input-field w-full">
              <option value="draft">草稿</option>
              <option value="published">已上架</option>
              <option value="ended">已結束</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">開始時間 *</label>
            <input v-model="eventForm.start_at" type="datetime-local" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">結束時間 *</label>
            <input v-model="eventForm.end_at" type="datetime-local" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">報名開始</label>
            <input v-model="eventForm.registration_start_at" type="datetime-local" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">報名結束</label>
            <input v-model="eventForm.registration_end_at" type="datetime-local" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">地點名稱</label>
            <input v-model="eventForm.location_name" placeholder="場地名稱" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">地址</label>
            <input v-model="eventForm.location_address" placeholder="詳細地址" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">地圖連結</label>
          <input v-model="eventForm.map_url" placeholder="https://maps.google.com/..." class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">聯絡信箱</label>
            <input v-model="eventForm.contact_email" type="email" placeholder="contact@example.com" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">聯絡電話</label>
            <input v-model="eventForm.contact_phone" placeholder="0900-000-000" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">活動描述</label>
          <textarea v-model="eventForm.description" rows="4" placeholder="活動介紹..." class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">舞風</label>
          <div class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="s in DANCE_STYLES"
              :key="s.key"
              type="button"
              class="rounded-full border px-3 py-1 text-xs font-semibold"
              :class="(eventForm.dance_styles || []).includes(s.key) ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'"
              @click="toggleDanceStyle(s.key)"
            >
              {{ s.label }}
            </button>
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">活動類型</label>
          <div class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="t in EVENT_TYPES"
              :key="t.key"
              type="button"
              class="rounded-full border px-3 py-1 text-xs font-semibold"
              :class="(eventForm.event_types || []).includes(t.key) ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'"
              @click="toggleEventType(t.key)"
            >
              {{ t.label }}
            </button>
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">社群連結 (IG, FB, YouTube, LINE, Website)</label>
          <div class="mt-2 grid gap-2 sm:grid-cols-2">
            <input v-model="socialForm.ig" placeholder="Instagram" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input v-model="socialForm.fb" placeholder="Facebook" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input v-model="socialForm.youtube" placeholder="YouTube" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input v-model="socialForm.line" placeholder="LINE" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input v-model="socialForm.website" placeholder="Website" class="rounded-lg border border-gray-300 px-3 py-2 text-sm sm:col-span-2" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">流程 (JSON)</label>
          <textarea v-model="scheduleJson" rows="3" placeholder='[{"time":"13:00","title":"Check-in","desc":"報到"}]' class="w-full rounded-lg border border-gray-300 px-4 py-2 font-mono text-xs" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">主辦方私密備註</label>
          <textarea v-model="internalNote" rows="3" placeholder="僅主辦方可見" class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm" />
        </div>
      </div>

      <p v-if="message" class="mt-4 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{{ message }}</p>
      <p v-if="errorMessage" class="mt-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{{ errorMessage }}</p>

      <div class="mt-4 flex flex-wrap gap-3">
        <button
          class="rounded-lg bg-brand-600 px-4 py-2 font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          :disabled="submitting === 'event'"
          @click="submitCreate"
        >
          {{ submitting === "event" ? "建立中..." : "建立活動" }}
        </button>
        <button
          v-if="mode === 'edit'"
          class="rounded-lg border border-brand-600 px-4 py-2 font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"
          :disabled="submitting === 'event'"
          @click="submitUpdate"
        >
          {{ submitting === "event" ? "更新中..." : "更新活動" }}
        </button>
        <router-link
          v-if="mode === 'edit' && editEventId"
          :to="{ name: 'organizer-forms-with-event', params: { eventId: editEventId } }"
          class="rounded-lg border border-gray-500 px-4 py-2 font-semibold text-gray-700 hover:bg-gray-50"
        >
          前往表單設定 →
        </router-link>
      </div>
    </section>

    <!-- 活動圖片獨立區塊（有活動 ID 時顯示，與表單同層級較醒目） -->
    <section v-if="editEventId" class="card mt-6 p-6">
      <h2 class="font-display text-lg font-semibold text-gray-800">活動圖片</h2>
      <p class="mt-1 text-sm text-gray-400">上傳後會顯示於活動詳情頁輪播。限 JPEG/PNG/WebP/GIF，單檔 5MB。</p>
      <div class="mt-4 flex flex-wrap items-center gap-4">
        <label class="inline-block cursor-pointer rounded-xl border-2 border-brand-500 px-4 py-2 text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-500/20">
          <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" class="hidden" :disabled="eventMediaUploading" @change="handleUploadEventMedia" />
          {{ eventMediaUploading ? "上傳中…" : "選擇圖片上傳" }}
        </label>
      </div>
      <div v-if="eventMediaList.length > 0" class="mt-4 flex flex-wrap gap-3">
        <div v-for="item in eventMediaList" :key="item.id" class="overflow-hidden rounded-xl border border-gray-200 bg-gray-100">
          <img :src="eventMediaUrl(item.path)" :alt="item.path" class="h-28 w-36 object-cover" />
          <p class="truncate px-2 py-1 text-xs text-gray-400">{{ item.path }}</p>
        </div>
      </div>
    </section>

    <!-- Ticket Type (when in edit mode) -->
    <section v-if="mode === 'edit' && editEventId" class="card mt-6 p-6">
      <h2 class="font-display text-lg font-semibold text-gray-800">既有票種</h2>
      <div v-if="ticketTypesList.length > 0" class="mt-4 space-y-4">
        <div
          v-for="tt in ticketTypesList"
          :key="tt.id"
          class="rounded-lg border border-gray-200 bg-gray-50/50 p-4"
        >
          <div v-if="editingTicketTypeId !== tt.id" class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <span class="font-medium text-gray-800">{{ tt.name }}</span>
              <span class="ml-2 text-sm text-gray-600">名額 {{ tt.capacity }} / 已售 {{ tt.sold_count }} · 每人限購 {{ tt.per_user_limit }}</span>
            </div>
            <div class="flex gap-2">
              <button
                type="button"
                class="rounded border border-gray-400 px-3 py-1 text-sm text-gray-700 hover:bg-gray-100"
                @click="startEditTicketType(tt)"
              >
                編輯
              </button>
              <button
                type="button"
                class="rounded border border-rose-300 px-3 py-1 text-sm text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="tt.sold_count > 0"
                :title="tt.sold_count > 0 ? '已售出不可刪除' : ''"
                @click="handleDeleteTicketType(tt)"
              >
                刪除
              </button>
            </div>
          </div>
          <div v-else class="space-y-3">
            <div class="grid gap-3 sm:grid-cols-2">
              <input v-model="editTicketTypeForm.name" placeholder="票種名稱 *" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <input v-model.number="editTicketTypeForm.capacity" type="number" min="0" placeholder="名額" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <input v-model.number="editTicketTypeForm.per_user_limit" type="number" min="1" placeholder="每人限購" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <input v-model="editTicketTypeForm.sale_start_at" type="datetime-local" placeholder="開賣時間" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <input v-model="editTicketTypeForm.sale_end_at" type="datetime-local" placeholder="結束販售" class="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <label class="flex items-center gap-2 text-sm">
              <input v-model="editTicketTypeForm.is_active" type="checkbox" />
              開放販售
            </label>
            <div class="flex gap-2">
              <button
                type="button"
                class="rounded bg-gray-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-50"
                :disabled="submitting === 'ticket'"
                @click="handleUpdateTicketType"
              >
                {{ submitting === "ticket" ? "儲存中..." : "儲存" }}
              </button>
              <button
                type="button"
                class="rounded border border-gray-400 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100"
                :disabled="submitting === 'ticket'"
                @click="cancelEditTicketType"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      </div>
      <p v-else class="mt-2 text-sm text-gray-500">尚無票種，請於下方建立。</p>

      <h2 class="mt-6 text-lg font-semibold text-gray-800">建立票種</h2>
      <div class="mt-4 grid gap-4 sm:grid-cols-2">
        <input v-model="ticketTypeForm.name" placeholder="票種名稱 *" class="rounded-lg border border-gray-300 px-4 py-2 text-sm" />
        <input v-model.number="ticketTypeForm.capacity" type="number" min="1" placeholder="名額" class="rounded-lg border border-gray-300 px-4 py-2 text-sm" />
        <input v-model.number="ticketTypeForm.per_user_limit" type="number" min="1" placeholder="每人限購" class="rounded-lg border border-gray-300 px-4 py-2 text-sm" />
      </div>
      <button
        class="mt-4 rounded-lg bg-gray-700 px-4 py-2 font-semibold text-white hover:bg-gray-800 disabled:opacity-50"
        :disabled="submitting === 'ticket'"
        @click="submitTicketType"
      >
        {{ submitting === "ticket" ? "建立中..." : "建立票種" }}
      </button>
    </section>
  </main>
</template>
