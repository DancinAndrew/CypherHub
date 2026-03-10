<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  organizerCreateEvent,
  organizerCreateTicketType,
  organizerGetEventDetail,
  organizerUpdateEvent,
  organizerUpsertInternalNote,
  type OrganizerCreateEventPayload,
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

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

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
const submitting = ref<"event" | "load" | "ticket" | null>(null);

eventForm.value.org_id = organizerStore.orgId || "";

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
  if (requireOrgId && !isValidUuid(payload.org_id)) {
    errorMessage.value = "請先完成步驟 1 申請主辦方，或填入有效的 org_id。";
    return null;
  }
  return payload;
}

async function loadEvent() {
  message.value = null;
  errorMessage.value = null;
  const id = editEventId.value.trim();
  if (!isValidUuid(id)) {
    errorMessage.value = "請輸入有效的活動 ID（UUID）。";
    return;
  }
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
    eventForm.value.status = e.status === "draft" ? "draft" : "published";
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
    mode.value = "edit";
    editEventId.value = id;
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
    message.value = `活動建立成功！`;
    editEventId.value = id;
    mode.value = "edit";
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
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "建立票種失敗。");
  } finally {
    submitting.value = null;
  }
}

if (route.params.eventId && typeof route.params.eventId === "string" && isValidUuid(route.params.eventId)) {
  editEventId.value = route.params.eventId;
  loadEvent();
}
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-10">
    <div class="mb-8">
      <router-link to="/organizer" class="text-sm text-slate-600 hover:text-brand-600">← 回主辦方主頁</router-link>
    </div>

    <h1 class="text-2xl font-bold text-slate-900">步驟 2：建立 / 編輯活動</h1>
    <p class="mt-2 text-sm text-slate-600">建立新活動，或輸入活動 ID 載入後編輯。</p>

    <!-- Load Event -->
    <section class="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-800">載入既有活動</h2>
      <div class="mt-3 flex flex-wrap gap-3">
        <input
          v-model="editEventId"
          placeholder="活動 ID (UUID)"
          class="flex-1 min-w-[200px] rounded-lg border border-slate-300 px-4 py-2 text-sm"
        />
        <button
          class="rounded-lg border border-slate-400 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          :disabled="submitting === 'load'"
          @click="loadEvent"
        >
          {{ submitting === "load" ? "載入中..." : "載入活動" }}
        </button>
      </div>
    </section>

    <!-- Event Form -->
    <section class="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-800">活動資料</h2>
      <div class="mt-4 space-y-4">
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">主辦方 ID (org_id) *</label>
          <input v-model="eventForm.org_id" placeholder="完成步驟 1 後自動帶入" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">活動名稱 *</label>
            <input v-model="eventForm.title" placeholder="活動標題" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">狀態</label>
            <select v-model="eventForm.status" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm">
              <option value="published">已上架</option>
              <option value="draft">草稿</option>
            </select>
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">開始時間 *</label>
            <input v-model="eventForm.start_at" type="datetime-local" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">結束時間 *</label>
            <input v-model="eventForm.end_at" type="datetime-local" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">報名開始</label>
            <input v-model="eventForm.registration_start_at" type="datetime-local" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">報名結束</label>
            <input v-model="eventForm.registration_end_at" type="datetime-local" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">地點名稱</label>
            <input v-model="eventForm.location_name" placeholder="場地名稱" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">地址</label>
            <input v-model="eventForm.location_address" placeholder="詳細地址" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">地圖連結</label>
          <input v-model="eventForm.map_url" placeholder="https://maps.google.com/..." class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">聯絡信箱</label>
            <input v-model="eventForm.contact_email" type="email" placeholder="contact@example.com" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">聯絡電話</label>
            <input v-model="eventForm.contact_phone" placeholder="0900-000-000" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">活動描述</label>
          <textarea v-model="eventForm.description" rows="4" placeholder="活動介紹..." class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">舞風</label>
          <div class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="s in DANCE_STYLES"
              :key="s.key"
              type="button"
              class="rounded-full border px-3 py-1 text-xs font-semibold"
              :class="(eventForm.dance_styles || []).includes(s.key) ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-slate-300 text-slate-600 hover:bg-slate-50'"
              @click="toggleDanceStyle(s.key)"
            >
              {{ s.label }}
            </button>
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">活動類型</label>
          <div class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="t in EVENT_TYPES"
              :key="t.key"
              type="button"
              class="rounded-full border px-3 py-1 text-xs font-semibold"
              :class="(eventForm.event_types || []).includes(t.key) ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-slate-300 text-slate-600 hover:bg-slate-50'"
              @click="toggleEventType(t.key)"
            >
              {{ t.label }}
            </button>
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">社群連結 (IG, FB, YouTube, LINE, Website)</label>
          <div class="mt-2 grid gap-2 sm:grid-cols-2">
            <input v-model="socialForm.ig" placeholder="Instagram" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input v-model="socialForm.fb" placeholder="Facebook" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input v-model="socialForm.youtube" placeholder="YouTube" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input v-model="socialForm.line" placeholder="LINE" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input v-model="socialForm.website" placeholder="Website" class="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">流程 (JSON)</label>
          <textarea v-model="scheduleJson" rows="3" placeholder='[{"time":"13:00","title":"Check-in","desc":"報到"}]' class="w-full rounded-lg border border-slate-300 px-4 py-2 font-mono text-xs" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">主辦方私密備註</label>
          <textarea v-model="internalNote" rows="3" placeholder="僅主辦方可見" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm" />
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
          class="rounded-lg border border-slate-500 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
        >
          前往表單設定 →
        </router-link>
      </div>
    </section>

    <!-- Ticket Type (when in edit mode) -->
    <section v-if="mode === 'edit' && editEventId" class="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-800">建立票種</h2>
      <div class="mt-4 grid gap-4 sm:grid-cols-2">
        <input v-model="ticketTypeForm.name" placeholder="票種名稱 *" class="rounded-lg border border-slate-300 px-4 py-2 text-sm" />
        <input v-model.number="ticketTypeForm.capacity" type="number" min="1" placeholder="名額" class="rounded-lg border border-slate-300 px-4 py-2 text-sm" />
        <input v-model.number="ticketTypeForm.per_user_limit" type="number" min="1" placeholder="每人限購" class="rounded-lg border border-slate-300 px-4 py-2 text-sm" />
      </div>
      <button
        class="mt-4 rounded-lg bg-slate-700 px-4 py-2 font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
        :disabled="submitting === 'ticket'"
        @click="submitTicketType"
      >
        {{ submitting === "ticket" ? "建立中..." : "建立票種" }}
      </button>
    </section>
  </main>
</template>
