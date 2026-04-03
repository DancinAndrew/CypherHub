<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import DynamicForm from "../components/DynamicForm.vue";
import LiveProgressBar from "../components/LiveProgressBar.vue";
import {
  createCheckout,
  createHoldOrder,
  fetchEventDetail,
  fetchEventForm,
  registerFree,
  redirectToEcpay,
  type EventDetail,
  type EventForm,
  type TicketType,
} from "../api/client";
import { useEventProgress } from "../composables/useEventProgress";
import { eventTypeLabelFromKey, styleLabelFromKey } from "../constants/taxonomy";
import { useAuthStore } from "../stores/auth";
import { toApiErrorMessage } from "../utils/errorMessages";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const eventId = computed(() => String(route.params.eventId ?? ""));
const detail = ref<EventDetail | null>(null);
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const registerMessage = ref<string | null>(null);
const registerLoading = ref(false);
const formLoading = ref(false);
const formError = ref<string | null>(null);

const selectedTicketTypeId = ref<string | null>(null);
const selectedForm = ref<EventForm | null>(null);
const formAnswers = ref<Record<string, unknown>>({});
const carouselIndex = ref(0);
const shareMessage = ref<string | null>(null);

const { progress: liveProgress, stages: liveStages } = useEventProgress(
  String(route.params.eventId ?? ""),
);

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? "";

async function copyShareUrl(): Promise<void> {
  shareMessage.value = null;
  const url = typeof window !== "undefined" ? window.location.href : "";
  if (!url) return;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
      shareMessage.value = "已複製連結";
      setTimeout(() => { shareMessage.value = null; }, 2000);
    } else {
      shareMessage.value = "請手動複製網址列連結";
    }
  } catch {
    shareMessage.value = "複製失敗，請手動複製網址列";
  }
}
function eventMediaUrl(path: string): string {
  if (!path) return "";
  const base = supabaseUrl.replace(/\/$/, "");
  return `${base}/storage/v1/object/public/event-media/${path}`;
}

const selectedTicketType = computed<TicketType | null>(() => {
  if (!detail.value || !selectedTicketTypeId.value) {
    return null;
  }
  return detail.value.ticket_types.find((item) => item.id === selectedTicketTypeId.value) ?? null;
});

const isPaidTicket = computed(() => (selectedTicketType.value?.price_cents ?? 0) > 0);

const checkoutQuantity = ref(1);

function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-TW", { dateStyle: "medium", timeStyle: "short" });
}

function formatDateShort(value?: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("zh-TW", { month: "short", day: "numeric", weekday: "short" });
}

function asSocialEntries(raw: Record<string, string> | undefined): Array<{ key: string; value: string }> {
  if (!raw || typeof raw !== "object") return [];
  return Object.entries(raw)
    .filter(([, value]) => Boolean(value))
    .map(([key, value]) => ({ key, value }));
}

const SOCIAL_LABELS: Record<string, string> = {
  ig: "Instagram",
  fb: "Facebook",
  youtube: "YouTube",
  line: "LINE",
  website: "官網",
};

const SOCIAL_STYLES: Record<string, string> = {
  ig: "border-l-pink-500/50 bg-pink-500/5 hover:bg-pink-500/10 hover:border-pink-500/60",
  fb: "border-l-blue-500/50 bg-blue-500/5 hover:bg-blue-500/10 hover:border-blue-500/60",
  youtube: "border-l-red-500/50 bg-red-500/5 hover:bg-red-500/10 hover:border-red-500/60",
  line: "border-l-emerald-500/50 bg-emerald-500/5 hover:bg-emerald-500/10 hover:border-emerald-500/60",
  website: "border-l-cyan-500/50 bg-cyan-500/5 hover:bg-cyan-500/10 hover:border-cyan-500/60",
};

function asScheduleItems(raw: Array<Record<string, string>> | undefined): Array<Record<string, string>> {
  if (!Array.isArray(raw)) return [];
  return raw.filter((item) => item && typeof item === "object");
}

/** 導航 URL：有 lat/lng 則用 Google Maps 導航，否則用 map_url（為 note 待辦鋪路） */
const navigateUrl = computed<string | null>(() => {
  if (!detail.value?.event) return null;
  const e = detail.value.event;
  const lat = e.latitude;
  const lng = e.longitude;
  if (typeof lat === "number" && typeof lng === "number" && !Number.isNaN(lat) && !Number.isNaN(lng)) {
    return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
  }
  const url = e.map_url?.trim();
  return url || null;
});

function validateClientAnswers(): string | null {
  if (!selectedForm.value) return null;
  for (const field of selectedForm.value.schema.fields) {
    const value = formAnswers.value[field.key];
    if (!field.required) continue;
    if (field.type === "checkbox") {
      if (value !== true) return `${field.label} 為必填，且必須勾選。`;
      continue;
    }
    if (field.type === "multi_select") {
      if (!Array.isArray(value) || value.length === 0) return `${field.label} 為必填。`;
      continue;
    }
    if (value === undefined || value === null || String(value).trim() === "") {
      return `${field.label} 為必填。`;
    }
  }
  return null;
}

async function loadDetail(): Promise<void> {
  if (!eventId.value) {
    errorMessage.value = "Missing event id";
    loading.value = false;
    return;
  }
  loading.value = true;
  errorMessage.value = null;
  try {
    detail.value = await fetchEventDetail(eventId.value);
    carouselIndex.value = 0;
    if (detail.value.ticket_types.length === 1) {
      await selectTicketType(detail.value.ticket_types[0]);
    }
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Failed to load event");
  } finally {
    loading.value = false;
  }
}

async function selectTicketType(ticketType: TicketType): Promise<void> {
  selectedTicketTypeId.value = ticketType.id;
  formLoading.value = true;
  formError.value = null;
  registerMessage.value = null;
  formAnswers.value = {};
  try {
    selectedForm.value = await fetchEventForm(eventId.value, ticketType.id);
  } catch (error: unknown) {
    selectedForm.value = null;
    formError.value = toApiErrorMessage(error, "Failed to load registration form");
  } finally {
    formLoading.value = false;
  }
}

async function handleRegister(): Promise<void> {
  registerMessage.value = null;
  if (!selectedTicketType.value) {
    registerMessage.value = "請先選擇票種。";
    return;
  }
  if (!authStore.isAuthenticated) {
    await router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  const validationMessage = validateClientAnswers();
  if (validationMessage) {
    registerMessage.value = validationMessage;
    return;
  }
  registerLoading.value = true;
  try {
    const tickets = await registerFree(eventId.value, {
      ticket_type_id: selectedTicketType.value.id,
      quantity: 1,
      answers: formAnswers.value,
    });
    registerMessage.value = `報名成功！已發放 ${tickets.length} 張票券。`;
    formAnswers.value = {};
  } catch (error: unknown) {
    registerMessage.value = toApiErrorMessage(error, "Registration failed");
  } finally {
    registerLoading.value = false;
  }
}

async function handleCheckout(): Promise<void> {
  registerMessage.value = null;
  if (!selectedTicketType.value) {
    registerMessage.value = "請先選擇票種。";
    return;
  }
  if (!authStore.isAuthenticated) {
    await router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  const qty = Math.max(1, Math.min(20, checkoutQuantity.value));
  registerLoading.value = true;
  try {
    const orderDetail = await createHoldOrder({
      items: [{ ticket_type_id: selectedTicketType.value.id, quantity: qty }],
      hold_minutes: 15,
    });
    const { form_params, cashier_url } = await createCheckout(orderDetail.order.id);
    redirectToEcpay(form_params, cashier_url);
  } catch (error: unknown) {
    registerMessage.value = toApiErrorMessage(error, "結帳失敗");
  } finally {
    registerLoading.value = false;
  }
}

onMounted(() => {
  loadDetail().catch(() => {});
});
</script>

<template>
  <main class="mx-auto w-full max-w-6xl px-4 pb-24 pt-4 sm:pt-6">

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-32">
      <div class="relative h-12 w-12">
        <div class="absolute inset-0 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" />
        <div class="absolute inset-2 animate-spin rounded-full border-2 border-cypher-accent-cyan border-b-transparent" style="animation-direction: reverse; animation-duration: 0.8s" />
      </div>
      <p class="mt-5 text-sm font-medium text-cypher-muted">載入活動中...</p>
    </div>

    <!-- Error -->
    <div v-else-if="errorMessage" class="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-8 text-rose-300 backdrop-blur-sm">
      {{ errorMessage }}
    </div>

    <template v-else-if="detail">
      <!-- ── Hero Media ── -->
      <section class="-mx-4 sm:-mx-0">
        <div
          v-if="detail.event_media?.length"
          class="relative overflow-hidden rounded-none sm:rounded-2xl"
        >
          <div class="relative aspect-[21/9] w-full overflow-hidden bg-gradient-to-br from-cypher-accent/30 via-cypher-accent-pink/20 to-cypher-accent-cyan/20">
            <img
              v-for="(item, idx) in detail.event_media"
              :key="item.id"
              :src="eventMediaUrl(item.path)"
              :alt="`${detail.event.title} ${idx + 1}`"
              class="absolute inset-0 h-full w-full object-cover transition-opacity duration-700"
              :class="carouselIndex === idx ? 'opacity-100' : 'opacity-0'"
              @error="(e) => ((e.target as HTMLImageElement).style.opacity = '0')"
            />
            <!-- Bottom fade -->
            <div class="absolute inset-0 bg-gradient-to-t from-cypher-bg via-cypher-bg/30 to-transparent" />
            <!-- Carousel controls -->
            <div v-if="detail.event_media.length > 1" class="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-3 rounded-full border border-white/10 bg-black/60 px-4 py-2 text-sm text-white backdrop-blur-md">
              <button type="button" aria-label="上一張" class="cursor-pointer transition-colors hover:text-cypher-accent" @click="carouselIndex = (carouselIndex - 1 + detail.event_media!.length) % detail.event_media!.length">
                <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" /></svg>
              </button>
              <span class="text-xs font-medium">{{ carouselIndex + 1 }} / {{ detail.event_media!.length }}</span>
              <button type="button" aria-label="下一張" class="cursor-pointer transition-colors hover:text-cypher-accent" @click="carouselIndex = (carouselIndex + 1) % detail.event_media!.length">
                <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
              </button>
            </div>
          </div>
        </div>
        <!-- No media placeholder -->
        <div
          v-else
          class="relative aspect-[21/9] w-full overflow-hidden rounded-none sm:rounded-2xl bg-gradient-to-br from-cypher-accent/20 via-cypher-accent-pink/10 to-cypher-accent-cyan/15"
        >
          <div class="absolute inset-0 flex items-center justify-center">
            <svg class="h-20 w-20 text-white/5" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z" />
            </svg>
          </div>
          <div class="absolute inset-0 bg-gradient-to-t from-cypher-bg via-transparent to-transparent" />
        </div>
      </section>

      <!-- ── Two-column layout ── -->
      <div class="mt-8 flex flex-col gap-8 lg:flex-row lg:items-start">

        <!-- Left: Main content -->
        <div class="min-w-0 flex-1 space-y-6">

          <!-- Event header -->
          <header class="animate-fade-in">
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0 flex-1">
                <p v-if="detail.organizer" class="section-label mb-3">{{ detail.organizer.name }}</p>
                <h1 class="font-street text-3xl leading-tight tracking-widest text-white sm:text-4xl lg:text-5xl">
                  {{ detail.event.title }}
                </h1>
              </div>
            </div>
            <div class="mt-4 flex flex-wrap gap-2">
              <span v-for="style in detail.event.dance_styles || []" :key="style" class="badge-dance">
                {{ styleLabelFromKey(style) }}
              </span>
              <span v-for="type in detail.event.event_types || []" :key="type" class="badge-type">
                {{ eventTypeLabelFromKey(type) }}
              </span>
            </div>
            <p class="mt-5 text-base leading-relaxed text-gray-400 sm:text-lg">
              {{ detail.event.description || detail.event.short_desc || "無描述" }}
            </p>
          </header>

          <!-- Live Progress -->
          <LiveProgressBar
            v-if="liveStages.length > 0"
            :progress="liveProgress"
            :stages="liveStages"
          />

          <!-- Organizer card -->
          <section v-if="detail.organizer" class="card animate-slide-up p-6">
            <div class="flex items-center gap-2">
              <span class="h-4 w-0.5 rounded-full bg-cypher-accent" aria-hidden="true" />
              <h2 class="font-street text-base tracking-wider text-white">主辦方</h2>
            </div>
            <div class="mt-4 flex items-start gap-4">
              <img
                v-if="detail.organizer.logo_url"
                :src="detail.organizer.logo_url"
                :alt="detail.organizer.name"
                class="h-14 w-14 shrink-0 rounded-xl border border-cypher-border object-cover"
              />
              <div class="min-w-0 flex-1">
                <p class="font-semibold text-white">{{ detail.organizer.name }}</p>
                <p v-if="detail.organizer.description" class="mt-1 text-sm leading-relaxed text-gray-400">{{ detail.organizer.description }}</p>
                <a
                  v-if="detail.organizer.contact_email"
                  :href="`mailto:${detail.organizer.contact_email}`"
                  class="mt-2 inline-flex items-center gap-1.5 text-sm text-cypher-accent transition-colors hover:text-cypher-accent-bright"
                >
                  {{ detail.organizer.contact_email }}
                </a>
              </div>
            </div>
            <div v-if="detail.other_events?.length" class="mt-5 border-t border-cypher-border pt-5">
              <p class="mb-3 text-xs font-semibold uppercase tracking-widest text-cypher-muted">同主辦方其他活動</p>
              <ul class="space-y-2">
                <li v-for="ev in detail.other_events" :key="ev.id">
                  <RouterLink
                    :to="{ name: 'event-detail', params: { eventId: ev.id } }"
                    class="flex cursor-pointer items-center justify-between rounded-xl border border-cypher-border p-3 transition-all duration-200 hover:border-cypher-accent/40 hover:bg-cypher-accent/5"
                  >
                    <span class="text-sm font-medium text-white">{{ ev.title }}</span>
                    <span class="shrink-0 text-xs text-cypher-muted">{{ formatDateShort(ev.start_at) }}</span>
                  </RouterLink>
                </li>
              </ul>
            </div>
          </section>

          <!-- Event details card -->
          <section
            v-if="detail.event.eligibility || detail.event.event_language || detail.event.checkin_open_at || asScheduleItems(detail.event.schedule).length || asSocialEntries(detail.event.socials).length"
            class="card animate-slide-up p-6"
            style="animation-delay: 0.1s"
          >
            <div class="flex items-center gap-2">
              <span class="h-4 w-0.5 rounded-full bg-cypher-accent-cyan" aria-hidden="true" />
              <h2 class="font-street text-base tracking-wider text-white">活動詳情</h2>
            </div>

            <!-- Social links -->
            <div v-if="asSocialEntries(detail.event.socials).length" class="mt-5">
              <p class="mb-3 text-xs font-semibold uppercase tracking-widest text-cypher-muted">社群連結</p>
              <div class="flex flex-wrap gap-2">
                <a
                  v-for="entry in asSocialEntries(detail.event.socials)"
                  :key="entry.key"
                  :href="entry.value.startsWith('http') ? entry.value : `https://${entry.value}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-l-4 border-cypher-border px-4 py-2.5 text-sm font-medium text-gray-200 transition-all duration-200"
                  :class="SOCIAL_STYLES[entry.key] ?? 'border-l-cypher-accent/50 bg-cypher-accent/5 hover:bg-cypher-accent/10'"
                >
                  {{ SOCIAL_LABELS[entry.key] ?? entry.key }}
                  <svg class="h-3 w-3 text-cypher-muted" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25" />
                  </svg>
                </a>
              </div>
            </div>

            <!-- Info rows -->
            <dl class="mt-5 grid gap-3 text-sm sm:grid-cols-2">
              <div v-if="detail.event.eligibility" class="rounded-xl border border-cypher-border/50 bg-cypher-surface-alt/30 px-4 py-3">
                <dt class="text-xs font-semibold uppercase tracking-widest text-cypher-muted">參加資格</dt>
                <dd class="mt-1 text-gray-300">{{ detail.event.eligibility }}</dd>
              </div>
              <div v-if="detail.event.event_language" class="rounded-xl border border-cypher-border/50 bg-cypher-surface-alt/30 px-4 py-3">
                <dt class="text-xs font-semibold uppercase tracking-widest text-cypher-muted">活動語言</dt>
                <dd class="mt-1 text-gray-300">{{ detail.event.event_language }}</dd>
              </div>
              <div v-if="detail.event.checkin_open_at" class="rounded-xl border border-cypher-border/50 bg-cypher-surface-alt/30 px-4 py-3">
                <dt class="text-xs font-semibold uppercase tracking-widest text-cypher-muted">報到開放</dt>
                <dd class="mt-1 text-gray-300">{{ formatDateTime(detail.event.checkin_open_at) }}</dd>
              </div>
              <div v-if="detail.event.checkin_note" class="rounded-xl border border-cypher-border/50 bg-cypher-surface-alt/30 px-4 py-3">
                <dt class="text-xs font-semibold uppercase tracking-widest text-cypher-muted">報到注意</dt>
                <dd class="mt-1 text-gray-300">{{ detail.event.checkin_note }}</dd>
              </div>
            </dl>

            <!-- Schedule timeline -->
            <div v-if="asScheduleItems(detail.event.schedule).length" class="mt-6">
              <p class="mb-4 text-xs font-semibold uppercase tracking-widest text-cypher-muted">活動流程</p>
              <ol class="relative space-y-0 border-l border-cypher-border pl-6">
                <li
                  v-for="(item, index) in asScheduleItems(detail.event.schedule)"
                  :key="index"
                  class="relative pb-6 last:pb-0"
                >
                  <!-- Timeline dot -->
                  <span class="absolute -left-[25px] flex h-4 w-4 items-center justify-center rounded-full border border-cypher-accent/50 bg-cypher-bg">
                    <span class="h-1.5 w-1.5 rounded-full bg-cypher-accent" />
                  </span>
                  <p class="text-xs font-bold text-cypher-accent">{{ item.time || "--" }}</p>
                  <p class="mt-0.5 font-semibold text-white">{{ item.title || "Untitled" }}</p>
                  <p v-if="item.desc" class="mt-0.5 text-sm text-gray-500">{{ item.desc }}</p>
                </li>
              </ol>
            </div>
          </section>

          <!-- Tickets card -->
          <section class="card animate-slide-up p-6" style="animation-delay: 0.15s">
            <div class="flex items-center gap-2">
              <span class="h-4 w-0.5 rounded-full bg-cypher-accent-pink" aria-hidden="true" />
              <h2 class="font-street text-base tracking-wider text-white">票種與報名</h2>
            </div>
            <div v-if="!detail.ticket_types.length" class="mt-4 text-sm text-cypher-muted">暫無可選票種</div>
            <div v-else class="mt-4 space-y-3">
              <button
                v-for="tt in detail.ticket_types"
                :key="tt.id"
                type="button"
                class="flex w-full cursor-pointer items-center justify-between rounded-xl border p-4 text-left transition-all duration-200"
                :class="selectedTicketTypeId === tt.id
                  ? 'border-cypher-accent bg-cypher-accent/10 shadow-glow-sm'
                  : 'border-cypher-border hover:border-cypher-accent/40 hover:bg-cypher-surface-alt/50'"
                @click="selectTicketType(tt)"
              >
                <div class="min-w-0 flex-1">
                  <p class="font-semibold text-white">{{ tt.name }}</p>
                  <p class="mt-1 text-xs text-cypher-muted">
                    名額 {{ tt.capacity }} · 已報 {{ tt.sold_count }} · 每人限 {{ tt.per_user_limit }}
                    <span v-if="tt.price_cents > 0" class="font-semibold text-cypher-accent-cyan"> · NT$ {{ (tt.price_cents / 100).toLocaleString() }}</span>
                    <span v-else class="font-semibold text-emerald-400"> · 免費</span>
                  </p>
                </div>
                <div class="ml-3 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-all duration-200"
                  :class="selectedTicketTypeId === tt.id ? 'border-cypher-accent bg-cypher-accent' : 'border-cypher-border'">
                  <svg v-if="selectedTicketTypeId === tt.id" class="h-3.5 w-3.5 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                </div>
              </button>
            </div>

            <!-- Free ticket form -->
            <div v-if="selectedTicketType && !isPaidTicket" class="mt-6 border-t border-cypher-border pt-6">
              <p class="mb-4 text-sm font-semibold text-gray-300">報名表單 · {{ selectedTicketType.name }}</p>
              <div v-if="formLoading" class="rounded-xl border border-cypher-border bg-cypher-surface-alt/40 p-4 text-sm text-cypher-muted">載入表單中...</div>
              <div v-else-if="formError" class="rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-300">{{ formError }}</div>
              <div v-else-if="selectedForm?.schema.fields.length">
                <DynamicForm v-model="formAnswers" :schema="selectedForm!.schema" :disabled="registerLoading" />
              </div>
              <div v-else class="rounded-xl border border-cypher-border/50 bg-cypher-surface-alt/30 p-4 text-sm text-cypher-muted">此票種無需填寫額外資料，可直接報名。</div>
              <p v-if="registerMessage" class="mt-3 text-sm font-medium" :class="registerMessage.startsWith('報名成功') ? 'text-emerald-400' : 'text-rose-400'">{{ registerMessage }}</p>
            </div>

            <!-- Paid ticket qty -->
            <div v-else-if="selectedTicketType && isPaidTicket" class="mt-6 border-t border-cypher-border pt-6">
              <p class="mb-4 text-sm font-semibold text-gray-300">結帳 · {{ selectedTicketType.name }}</p>
              <div class="flex items-center gap-4">
                <label for="checkout-qty" class="text-sm text-gray-400">數量</label>
                <input
                  id="checkout-qty"
                  v-model.number="checkoutQuantity"
                  type="number"
                  min="1"
                  max="20"
                  class="w-24 rounded-xl border border-cypher-border bg-cypher-surface px-3 py-2 text-center text-white focus:border-cypher-accent focus:outline-none focus:ring-2 focus:ring-cypher-accent/30"
                />
                <span class="text-sm font-semibold text-cypher-accent-cyan">
                  NT$ {{ ((selectedTicketType.price_cents * checkoutQuantity) / 100).toLocaleString() }}
                </span>
              </div>
              <p class="mt-2 text-xs text-cypher-muted">點擊「前往結帳」將導向綠界金流頁完成付款</p>
              <p v-if="registerMessage" class="mt-3 text-sm font-medium text-rose-400">{{ registerMessage }}</p>
            </div>
          </section>
        </div>

        <!-- ── Right: Sticky sidebar ── -->
        <aside class="w-full shrink-0 lg:sticky lg:top-24 lg:w-80">
          <div class="card-glass animate-slide-up rounded-2xl p-6" style="animation-delay: 0.2s">

            <!-- Time & Location -->
            <p class="section-label mb-4">時間與地點</p>
            <dl class="space-y-4">
              <div class="flex gap-3">
                <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cypher-accent/10">
                  <svg class="h-4 w-4 text-cypher-accent" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-widest text-cypher-muted">開始</dt>
                  <dd class="mt-0.5 text-sm font-medium text-white">{{ formatDateTime(detail.event.start_at) }}</dd>
                  <dt class="mt-2 text-xs font-semibold uppercase tracking-widest text-cypher-muted">結束</dt>
                  <dd class="mt-0.5 text-sm font-medium text-white">{{ formatDateTime(detail.event.end_at) }}</dd>
                </div>
              </div>
              <div class="flex gap-3">
                <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cypher-accent-cyan/10">
                  <svg class="h-4 w-4 text-cypher-accent-cyan" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                  </svg>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-widest text-cypher-muted">地點</dt>
                  <dd class="mt-0.5 text-sm font-medium text-white">{{ detail.event.location_name || "待公佈" }}</dd>
                  <dd v-if="detail.event.location_address" class="mt-0.5 text-xs leading-relaxed text-gray-400">{{ detail.event.location_address }}</dd>
                  <a
                    v-if="navigateUrl"
                    :href="navigateUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="mt-2 inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-cypher-border bg-cypher-surface-alt/50 px-3 py-1.5 text-xs font-medium text-gray-300 transition-all duration-200 hover:border-cypher-accent-cyan/50 hover:text-cypher-accent-cyan"
                  >
                    <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
                    </svg>
                    導航
                  </a>
                </div>
              </div>
              <div v-if="detail.event.registration_end_at" class="flex gap-3">
                <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cypher-accent-pink/10">
                  <svg class="h-4 w-4 text-cypher-accent-pink" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                  </svg>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-widest text-cypher-muted">報名截止</dt>
                  <dd class="mt-0.5 text-sm font-medium text-gray-300">{{ formatDateTime(detail.event.registration_end_at) }}</dd>
                </div>
              </div>
            </dl>

            <!-- Divider -->
            <div class="glow-line my-6" />

            <!-- CTA -->
            <div class="space-y-3">
              <button
                v-if="!isPaidTicket"
                type="button"
                class="btn-primary w-full py-4 text-base"
                :disabled="registerLoading || formLoading"
                @click="handleRegister"
              >
                <span v-if="registerLoading" class="flex items-center justify-center gap-2">
                  <span class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  報名中...
                </span>
                <span v-else>立即報名</span>
              </button>
              <button
                v-else
                type="button"
                class="btn-primary w-full py-4 text-base"
                :disabled="registerLoading"
                @click="handleCheckout"
              >
                <span v-if="registerLoading" class="flex items-center justify-center gap-2">
                  <span class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  導向付款中...
                </span>
                <span v-else>前往結帳</span>
              </button>
              <button type="button" class="btn-secondary w-full" @click="copyShareUrl">
                <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
                </svg>
                分享活動
              </button>
            </div>
            <p v-if="shareMessage" class="mt-3 text-center text-sm font-medium text-emerald-400">{{ shareMessage }}</p>
          </div>
        </aside>
      </div>
    </template>
  </main>
</template>
