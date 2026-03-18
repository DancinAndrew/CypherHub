<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import DynamicForm from "../components/DynamicForm.vue";
import {
  fetchEventDetail,
  fetchEventForm,
  registerFree,
  type EventDetail,
  type EventForm,
  type TicketType,
} from "../api/client";
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

onMounted(() => {
  loadDetail().catch(() => {});
});
</script>

<template>
  <main class="mx-auto w-full max-w-6xl px-4 pb-20 pt-4 sm:pt-6">
    <div v-if="loading" class="flex flex-col items-center justify-center py-24">
      <span class="h-10 w-10 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" />
      <p class="mt-4 text-cypher-muted">載入活動中...</p>
    </div>
    <div v-else-if="errorMessage" class="rounded-2xl border border-rose-500/40 bg-rose-950/60 p-6 text-rose-300 backdrop-blur-sm">
      {{ errorMessage }}
    </div>

    <template v-else-if="detail">
      <!-- Hero: Full-width image with gradient overlay -->
      <section v-if="detail.event_media?.length" class="-mx-4 overflow-hidden rounded-2xl sm:-mx-6 lg:-mx-8">
        <div class="relative aspect-[16/9] w-full overflow-hidden bg-gradient-to-br from-cypher-accent/30 via-cypher-accent-pink/20 to-cypher-accent-cyan/20">
          <img
            v-for="(item, idx) in detail.event_media"
            :key="item.id"
            :src="eventMediaUrl(item.path)"
            :alt="`${detail.event.title} ${idx + 1}`"
            class="absolute inset-0 h-full w-full object-cover transition-opacity duration-500"
            :class="carouselIndex === idx ? 'opacity-100' : 'opacity-0'"
            @error="(e) => ((e.target as HTMLImageElement).style.opacity = '0')"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-cypher-bg via-transparent to-transparent" />
          <div v-if="detail.event_media.length > 1" class="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-3 rounded-full border border-white/20 bg-black/60 px-4 py-2 text-sm text-white backdrop-blur-sm">
            <button type="button" aria-label="上一張" class="hover:text-cypher-accent transition-colors" @click="carouselIndex = (carouselIndex - 1 + detail.event_media!.length) % detail.event_media!.length">‹</button>
            <span>{{ carouselIndex + 1 }} / {{ detail.event_media!.length }}</span>
            <button type="button" aria-label="下一張" class="hover:text-cypher-accent transition-colors" @click="carouselIndex = (carouselIndex + 1) % detail.event_media!.length">›</button>
          </div>
        </div>
      </section>

      <!-- Placeholder when no media -->
      <section v-else class="-mx-4 aspect-[16/9] w-[calc(100%+2rem)] rounded-2xl bg-gradient-to-br from-cypher-accent/30 via-cypher-accent-pink/20 to-cypher-accent-cyan/20 sm:-mx-6 sm:w-[calc(100%+3rem)] lg:-mx-8 lg:w-[calc(100%+4rem)]" />

      <!-- Two-column: Main content + Sticky sidebar -->
      <div class="mt-8 flex flex-col gap-8 lg:flex-row lg:items-start">
        <!-- Left: Main content -->
        <div class="min-w-0 flex-1 space-y-8">
          <header class="animate-fade-in">
            <h1 class="font-street text-3xl tracking-widest text-white sm:text-4xl">
              {{ detail.event.title }}
            </h1>
            <p v-if="detail.organizer" class="mt-2 text-cypher-muted">
              主辦 · {{ detail.organizer.name }}
            </p>
            <div class="mt-4 flex flex-wrap gap-2">
              <span v-for="style in detail.event.dance_styles || []" :key="style" class="badge-dance">
                {{ styleLabelFromKey(style) }}
              </span>
              <span v-for="type in detail.event.event_types || []" :key="type" class="badge-type">
                {{ eventTypeLabelFromKey(type) }}
              </span>
            </div>
            <p class="mt-6 text-lg leading-relaxed text-gray-300">
              {{ detail.event.description || detail.event.short_desc || "無描述" }}
            </p>
          </header>

          <!-- Organizer -->
          <section v-if="detail.organizer" class="card p-6 animate-slide-up">
            <h2 class="font-street text-lg tracking-wider text-white">主辦方</h2>
            <div class="mt-4 flex items-start gap-4">
              <img
                v-if="detail.organizer.logo_url"
                :src="detail.organizer.logo_url"
                :alt="detail.organizer.name"
                class="h-14 w-14 rounded-xl border border-cypher-border object-cover"
              />
              <div>
                <p class="font-semibold text-white">{{ detail.organizer.name }}</p>
                <p v-if="detail.organizer.description" class="mt-1 text-sm text-gray-400">{{ detail.organizer.description }}</p>
                <a
                  v-if="detail.organizer.contact_email"
                  :href="`mailto:${detail.organizer.contact_email}`"
                  class="mt-1 inline-block text-sm text-cypher-accent transition-colors hover:text-cypher-accent-pink"
                >
                  {{ detail.organizer.contact_email }}
                </a>
              </div>
            </div>
            <div v-if="detail.other_events?.length" class="mt-4 border-t border-cypher-border pt-4">
              <h3 class="text-sm font-medium text-gray-400">同主辦方其他活動</h3>
              <ul class="mt-2 space-y-2">
                <li v-for="ev in detail.other_events" :key="ev.id">
                  <RouterLink
                    :to="{ name: 'event-detail', params: { eventId: ev.id } }"
                    class="block rounded-xl border border-cypher-border p-3 text-sm text-gray-300 transition-all hover:border-cypher-accent/50 hover:bg-cypher-accent/5"
                  >
                    <span class="font-medium text-white">{{ ev.title }}</span>
                    <span class="ml-2 text-cypher-muted">{{ formatDateShort(ev.start_at) }}</span>
                  </RouterLink>
                </li>
              </ul>
            </div>
          </section>

          <!-- Event info, schedule, socials -->
          <section v-if="detail.event.eligibility || detail.event.event_language || asScheduleItems(detail.event.schedule).length || asSocialEntries(detail.event.socials).length" class="card p-6 animate-slide-up" style="animation-delay: 0.1s">
            <h2 class="font-street text-lg tracking-wider text-white">活動詳情</h2>
            <div v-if="asSocialEntries(detail.event.socials).length" class="mt-4">
              <h3 class="text-sm font-medium text-gray-400">社群連結</h3>
              <div class="mt-2 flex flex-wrap gap-2">
                <a
                  v-for="entry in asSocialEntries(detail.event.socials)"
                  :key="entry.key"
                  :href="entry.value.startsWith('http') ? entry.value : `https://${entry.value}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-2 rounded-lg border border-cypher-border border-l-4 px-4 py-2 text-sm text-gray-200 transition-all"
                  :class="SOCIAL_STYLES[entry.key] ?? 'border-l-cypher-accent/50 bg-cypher-accent/5 hover:bg-cypher-accent/10'"
                >
                  {{ SOCIAL_LABELS[entry.key] ?? entry.key }}
                  <span class="text-cypher-muted">→</span>
                </a>
              </div>
            </div>
            <div class="mt-4 space-y-2 text-sm text-gray-400">
              <p v-if="detail.event.eligibility"><span class="font-medium text-gray-300">參加資格：</span>{{ detail.event.eligibility }}</p>
              <p v-if="detail.event.event_language"><span class="font-medium text-gray-300">活動語言：</span>{{ detail.event.event_language }}</p>
              <p v-if="detail.event.checkin_open_at"><span class="font-medium text-gray-300">報到開放：</span>{{ formatDateTime(detail.event.checkin_open_at) }}</p>
              <p v-if="detail.event.checkin_note"><span class="font-medium text-gray-300">報到注意：</span>{{ detail.event.checkin_note }}</p>
            </div>
            <div v-if="asScheduleItems(detail.event.schedule).length" class="mt-4">
              <h3 class="text-sm font-medium text-gray-400">流程</h3>
              <ul class="mt-2 space-y-2">
                <li
                  v-for="(item, index) in asScheduleItems(detail.event.schedule)"
                  :key="index"
                  class="flex gap-3 rounded-xl border border-cypher-border p-3 text-sm"
                >
                  <span class="shrink-0 font-medium text-cypher-accent">{{ item.time || "--" }}</span>
                  <div>
                    <p class="font-medium text-white">{{ item.title || "Untitled" }}</p>
                    <p v-if="item.desc" class="mt-0.5 text-gray-500">{{ item.desc }}</p>
                  </div>
                </li>
              </ul>
            </div>
          </section>

          <!-- Ticket types + registration form -->
          <section class="card p-6 animate-slide-up" style="animation-delay: 0.15s">
            <h2 class="font-street text-lg tracking-wider text-white">票種與報名</h2>
            <p class="mt-1 text-sm text-cypher-muted">MVP-1 僅支援免費票</p>
            <div v-if="!detail.ticket_types.length" class="mt-4 text-cypher-muted">暫無可選票種</div>
            <div v-else class="mt-4 space-y-3">
              <button
                v-for="tt in detail.ticket_types"
                :key="tt.id"
                type="button"
                class="flex w-full items-center justify-between rounded-xl border p-4 text-left transition-all"
                :class="selectedTicketTypeId === tt.id ? 'border-cypher-accent bg-cypher-accent/10 shadow-glow-sm' : 'border-cypher-border hover:border-cypher-accent/40'"
                @click="selectTicketType(tt)"
              >
                <div>
                  <p class="font-semibold text-white">{{ tt.name }}</p>
                  <p class="mt-0.5 text-xs text-cypher-muted">名額 {{ tt.capacity }} · 已報 {{ tt.sold_count }} · 每人限 {{ tt.per_user_limit }}</p>
                </div>
                <span v-if="selectedTicketTypeId === tt.id" class="text-cypher-accent">✓ 已選</span>
              </button>
            </div>

            <div v-if="selectedTicketType" class="mt-6 border-t border-cypher-border pt-6">
              <h3 class="font-medium text-white">報名表單 · {{ selectedTicketType.name }}</h3>
              <div v-if="formLoading" class="mt-4 rounded-xl border border-cypher-border bg-cypher-surface-alt/50 p-4 text-sm text-cypher-muted">載入表單中...</div>
              <div v-else-if="formError" class="mt-4 rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-sm text-rose-300">{{ formError }}</div>
              <div v-else-if="selectedForm?.schema.fields.length" class="mt-4">
                <DynamicForm v-model="formAnswers" :schema="selectedForm!.schema" :disabled="registerLoading" />
              </div>
              <div v-else class="mt-4 rounded-xl border border-cypher-border bg-cypher-surface-alt/50 p-4 text-sm text-cypher-muted">此票種無需填寫額外資料，可直接報名。</div>
              <p v-if="registerMessage" class="mt-3 text-sm" :class="registerMessage.startsWith('報名成功') ? 'text-emerald-400' : 'text-rose-400'">{{ registerMessage }}</p>
            </div>
          </section>
        </div>

        <!-- Right: Sticky When & Where + CTA -->
        <aside class="w-full shrink-0 lg:sticky lg:top-24 lg:w-80">
          <div class="card animate-slide-up p-6" style="animation-delay: 0.2s">
            <h2 class="font-street text-sm tracking-[0.2em] text-cypher-muted">時間與地點</h2>
            <div class="mt-4 space-y-4">
              <div>
                <p class="text-xs font-medium text-cypher-muted">開始</p>
                <p class="mt-0.5 font-medium text-white">{{ formatDateTime(detail.event.start_at) }}</p>
              </div>
              <div>
                <p class="text-xs font-medium text-cypher-muted">結束</p>
                <p class="mt-0.5 font-medium text-white">{{ formatDateTime(detail.event.end_at) }}</p>
              </div>
              <div>
                <p class="text-xs font-medium text-cypher-muted">地點</p>
                <p class="mt-0.5 font-medium text-white">{{ detail.event.location_name || "待公佈" }}</p>
                <p v-if="detail.event.location_address" class="mt-0.5 text-sm text-gray-400">{{ detail.event.location_address }}</p>
                <a
                  v-if="navigateUrl"
                  :href="navigateUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="mt-2 inline-flex items-center gap-2 rounded-xl border border-cypher-border bg-cypher-surface px-3 py-2 text-sm font-medium text-gray-200 transition-colors hover:border-cypher-accent hover:bg-cypher-surface-alt"
                >
                  <span aria-hidden="true">🧭</span>
                  導航
                </a>
              </div>
              <div v-if="detail.event.registration_end_at">
                <p class="text-xs font-medium text-cypher-muted">報名截止</p>
                <p class="mt-0.5 text-sm text-gray-300">{{ formatDateTime(detail.event.registration_end_at) }}</p>
              </div>
            </div>

            <!-- Sticky CTA - glowing -->
            <div class="mt-6 space-y-3">
              <button
                type="button"
                class="btn-primary w-full py-4 text-base"
                :disabled="registerLoading || formLoading"
                @click="handleRegister"
              >
                {{ registerLoading ? "報名中..." : "立即報名" }}
              </button>
              <button
                type="button"
                class="btn-secondary w-full"
                @click="copyShareUrl"
              >
                分享活動
              </button>
            </div>
            <p v-if="shareMessage" class="mt-2 text-center text-sm text-emerald-400">{{ shareMessage }}</p>
          </div>
        </aside>
      </div>
    </template>
  </main>
</template>
