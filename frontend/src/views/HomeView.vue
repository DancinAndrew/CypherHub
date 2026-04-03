<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { fetchEvents, type EventItem } from "../api/client";
import {
  DANCE_STYLES,
  EVENT_TYPES,
  eventTypeLabelFromKey,
  styleLabelFromKey,
  type DanceStyleKey,
  type EventTypeKey,
} from "../constants/taxonomy";
import { toApiErrorMessage } from "../utils/errorMessages";

const route = useRoute();
const router = useRouter();

const events = ref<EventItem[]>([]);
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const filterOpen = ref(false);

const selectedStyles = ref<DanceStyleKey[]>([]);
const selectedTypes = ref<EventTypeKey[]>([]);
const searchQuery = ref("");
const dateFrom = ref("");
const dateTo = ref("");
const sortMode = ref<"start_at" | "hot">("start_at");

const styleKeys = new Set(DANCE_STYLES.map((item) => item.key));
const typeKeys = new Set(EVENT_TYPES.map((item) => item.key));
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? "";

function eventMediaUrl(path: string): string {
  if (!path) return "";
  const base = supabaseUrl.replace(/\/$/, "");
  return `${base}/storage/v1/object/public/event-media/${path}`;
}

function parseQueryList(raw: unknown, allowed: Set<string>): string[] {
  if (typeof raw !== "string") {
    return [];
  }
  const items = raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item && allowed.has(item));
  return Array.from(new Set(items));
}

function toggleStyle(style: DanceStyleKey): void {
  if (selectedStyles.value.includes(style)) {
    selectedStyles.value = selectedStyles.value.filter((item) => item !== style);
  } else {
    selectedStyles.value = [...selectedStyles.value, style];
  }
  applyFilters().catch(() => {});
}

function toggleType(type: EventTypeKey): void {
  if (selectedTypes.value.includes(type)) {
    selectedTypes.value = selectedTypes.value.filter((item) => item !== type);
  } else {
    selectedTypes.value = [...selectedTypes.value, type];
  }
  applyFilters().catch(() => {});
}

function clearFilters(): void {
  selectedStyles.value = [];
  selectedTypes.value = [];
  searchQuery.value = "";
  dateFrom.value = "";
  dateTo.value = "";
  applyFilters().catch(() => {});
}

async function loadEvents(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    events.value = await fetchEvents({
      q: searchQuery.value.trim() || undefined,
      from: dateFrom.value || undefined,
      to: dateTo.value || undefined,
      styles: selectedStyles.value.length ? selectedStyles.value.join(",") : undefined,
      types: selectedTypes.value.length ? selectedTypes.value.join(",") : undefined,
      sort: sortMode.value,
    });
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Failed to load events");
  } finally {
    loading.value = false;
  }
}

async function applyFilters(): Promise<void> {
  await router.replace({
    query: {
      ...route.query,
      q: searchQuery.value.trim() || undefined,
      from: dateFrom.value || undefined,
      to: dateTo.value || undefined,
      styles: selectedStyles.value.length ? selectedStyles.value.join(",") : undefined,
      types: selectedTypes.value.length ? selectedTypes.value.join(",") : undefined,
      sort: sortMode.value,
    },
  });
  await loadEvents();
}

function setSortMode(mode: "start_at" | "hot"): void {
  sortMode.value = mode;
  applyFilters().catch(() => {});
}

function formatDateShort(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("zh-TW", { month: "short", day: "numeric", weekday: "short" });
}

function eventCardGradient(event: EventItem): string {
  const styles = event.dance_styles?.[0] || "default";
  const gradients: Record<string, string> = {
    hiphop: "from-cypher-accent via-purple-600 to-cypher-accent-pink",
    popping: "from-cypher-accent-orange via-amber-500 to-yellow-500",
    locking: "from-cypher-accent-pink via-rose-600 to-pink-500",
    breaking: "from-cypher-accent-cyan via-sky-500 to-blue-600",
    house: "from-emerald-500 via-teal-500 to-cypher-accent-cyan",
    waacking: "from-cypher-accent-pink via-fuchsia-600 to-cypher-accent",
    default: "from-cypher-accent via-purple-700 to-cypher-surface-alt",
  };
  return gradients[styles] ?? gradients.default;
}

onMounted(() => {
  selectedStyles.value = parseQueryList(route.query.styles, styleKeys) as DanceStyleKey[];
  selectedTypes.value = parseQueryList(route.query.types, typeKeys) as EventTypeKey[];
  searchQuery.value = typeof route.query.q === "string" ? route.query.q : "";
  dateFrom.value = typeof route.query.from === "string" ? route.query.from : "";
  dateTo.value = typeof route.query.to === "string" ? route.query.to : "";
  sortMode.value = route.query.sort === "hot" ? "hot" : "start_at";
  loadEvents().catch(() => {});
});
</script>

<template>
  <main class="relative min-h-screen overflow-hidden">

    <!-- ── Hero ── -->
    <section class="relative px-4 pb-16 pt-20 sm:pt-28 sm:pb-24">
      <!-- Background layers -->
      <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
      <div class="absolute inset-0 bg-gradient-radial-purple" aria-hidden="true" />
      <!-- Subtle grid overlay -->
      <div
        class="absolute inset-0 opacity-[0.03]"
        style="background-image: linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px); background-size: 40px 40px;"
        aria-hidden="true"
      />

      <div class="relative mx-auto max-w-6xl">
        <!-- Eyebrow -->
        <div class="animate-slide-up flex items-center gap-3">
          <span class="h-px w-8 bg-cypher-accent-cyan" aria-hidden="true" />
          <p class="section-label">Street Dance · 你的下一場 Battle</p>
        </div>

        <!-- Headline -->
        <h1 class="animate-slide-up mt-5 font-street text-5xl leading-[1.05] tracking-wide text-white sm:text-7xl md:text-8xl">
          街舞活動<br />
          <span class="bg-gradient-to-r from-cypher-accent via-cypher-accent-bright to-cypher-accent-cyan bg-clip-text text-transparent">
            從這裡開始
          </span>
        </h1>

        <!-- Subheadline -->
        <p class="animate-slide-up-delay mt-6 max-w-lg text-base leading-relaxed text-gray-400 sm:text-lg">
          工作坊 · 賽事 · 社團 · 派對 — 探索、報名、站上舞台
        </p>

        <!-- Marquee: dance styles -->
        <div class="animate-slide-up-delay mt-8 overflow-hidden" aria-hidden="true">
          <div class="flex w-max animate-marquee gap-4">
            <span v-for="style in [...DANCE_STYLES, ...DANCE_STYLES]" :key="`m-${style.key}-${Math.random()}`"
              class="shrink-0 rounded-full border border-cypher-accent/20 bg-cypher-accent/5 px-4 py-1.5 text-xs font-semibold text-cypher-muted">
              {{ style.label }}
            </span>
          </div>
        </div>

        <!-- Search bar -->
        <div class="animate-slide-up-delay-2 mt-8 flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <div class="relative flex-1">
            <div class="pointer-events-none absolute inset-y-0 left-4 flex items-center">
              <svg class="h-4 w-4 text-cypher-muted" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜尋活動名稱、簡介、地點..."
              class="input-field w-full py-3.5 pl-10 pr-28"
              @keydown.enter="applyFilters"
            />
            <button
              type="button"
              class="btn-primary absolute right-2 top-1/2 -translate-y-1/2 py-2 text-sm"
              @click="applyFilters"
            >
              搜尋
            </button>
          </div>
          <button
            type="button"
            class="flex shrink-0 cursor-pointer items-center justify-center gap-2 rounded-xl border border-cypher-border bg-cypher-surface px-5 py-3.5 font-medium text-gray-300 transition-all duration-200 hover:border-cypher-accent/50 hover:bg-cypher-surface-alt hover:text-white"
            @click="filterOpen = !filterOpen"
          >
            <svg class="h-4 w-4 transition-transform duration-300" :class="filterOpen ? 'rotate-180' : ''" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 12h10M11 20h2" />
            </svg>
            篩選
            <span
              v-if="selectedStyles.length || selectedTypes.length || dateFrom || dateTo"
              class="rounded-full bg-cypher-accent px-2 py-0.5 text-xs font-bold text-white"
            >
              {{ selectedStyles.length + selectedTypes.length + (dateFrom ? 1 : 0) + (dateTo ? 1 : 0) }}
            </span>
          </button>
        </div>

        <!-- Collapsible Filters -->
        <Transition
          enter-active-class="transition-all duration-300 ease-out"
          enter-from-class="opacity-0 max-h-0"
          enter-to-class="opacity-100 max-h-[600px]"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 max-h-[600px]"
          leave-to-class="opacity-0 max-h-0"
        >
          <div
            v-show="filterOpen"
            class="mt-4 overflow-hidden rounded-2xl border border-cypher-border bg-cypher-surface/80 p-6 backdrop-blur-md"
          >
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-gray-200">篩選條件</span>
              <button type="button" class="cursor-pointer text-xs font-semibold text-cypher-muted transition-colors hover:text-cypher-accent" @click="clearFilters">
                清除全部
              </button>
            </div>

            <div class="mt-5 grid gap-4 sm:grid-cols-2">
              <div>
                <label class="mb-2 block text-xs font-medium text-cypher-muted">開始日期</label>
                <input v-model="dateFrom" type="date" class="input-field py-2.5 text-sm" @change="() => applyFilters().catch(() => {})" />
              </div>
              <div>
                <label class="mb-2 block text-xs font-medium text-cypher-muted">結束日期</label>
                <input v-model="dateTo" type="date" class="input-field py-2.5 text-sm" @change="() => applyFilters().catch(() => {})" />
              </div>
            </div>

            <div class="mt-5">
              <p class="mb-3 text-xs font-semibold uppercase tracking-widest text-cypher-muted">舞風</p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="style in DANCE_STYLES"
                  :key="style.key"
                  type="button"
                  class="cursor-pointer rounded-full px-4 py-1.5 text-xs font-semibold transition-all duration-200"
                  :class="selectedStyles.includes(style.key)
                    ? 'border border-cypher-accent bg-cypher-accent/20 text-cypher-accent-bright shadow-glow-sm'
                    : 'border border-cypher-border bg-cypher-surface-alt text-gray-400 hover:border-cypher-accent/40 hover:text-gray-200'"
                  @click="toggleStyle(style.key)"
                >
                  {{ style.label }}
                </button>
              </div>
            </div>

            <div class="mt-5">
              <p class="mb-3 text-xs font-semibold uppercase tracking-widest text-cypher-muted">活動類型</p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="type in EVENT_TYPES"
                  :key="type.key"
                  type="button"
                  class="cursor-pointer rounded-full px-4 py-1.5 text-xs font-semibold transition-all duration-200"
                  :class="selectedTypes.includes(type.key)
                    ? 'border border-cypher-accent-cyan bg-cypher-accent-cyan/20 text-cypher-accent-cyan'
                    : 'border border-cypher-border bg-cypher-surface-alt text-gray-400 hover:border-cypher-accent-cyan/40 hover:text-gray-200'"
                  @click="toggleType(type.key)"
                >
                  {{ type.label }}
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </section>

    <!-- ── Events List ── -->
    <section class="relative px-4 pb-28 pt-2">
      <div class="mx-auto max-w-6xl">

        <!-- Section header -->
        <div class="mb-8 flex flex-wrap items-center justify-between gap-4 animate-fade-in">
          <div class="flex items-center gap-3">
            <span class="h-6 w-1 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
            <h2 class="font-street text-2xl tracking-wider text-white sm:text-3xl">所有活動</h2>
          </div>
          <!-- Sort tabs -->
          <div class="flex gap-1 rounded-xl border border-cypher-border bg-cypher-surface p-1">
            <button
              type="button"
              class="cursor-pointer rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-200"
              :class="sortMode === 'start_at'
                ? 'bg-cypher-accent text-white shadow-glow-sm'
                : 'text-gray-400 hover:text-white'"
              @click="setSortMode('start_at')"
            >
              依時間
            </button>
            <button
              type="button"
              class="cursor-pointer rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-200"
              :class="sortMode === 'hot'
                ? 'bg-cypher-accent-pink text-white shadow-glow-pink'
                : 'text-gray-400 hover:text-white'"
              @click="setSortMode('hot')"
            >
              熱門
            </button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="flex flex-col items-center justify-center py-32">
          <div class="relative h-12 w-12">
            <div class="absolute inset-0 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" />
            <div class="absolute inset-2 animate-spin rounded-full border-2 border-cypher-accent-cyan border-b-transparent" style="animation-direction: reverse; animation-duration: 0.8s" />
          </div>
          <p class="mt-5 text-sm font-medium text-cypher-muted">載入活動中...</p>
        </div>

        <!-- Error -->
        <div v-else-if="errorMessage" class="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-8 text-center text-rose-300 backdrop-blur-sm">
          {{ errorMessage }}
        </div>

        <!-- Empty -->
        <div v-else-if="events.length === 0" class="rounded-2xl border border-cypher-border bg-cypher-surface/50 py-28 text-center backdrop-blur-sm">
          <svg class="mx-auto h-12 w-12 text-cypher-muted/40" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
          </svg>
          <p class="mt-4 text-cypher-muted">目前沒有符合條件的活動</p>
        </div>

        <!-- Event cards grid -->
        <div v-else class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <RouterLink
            v-for="(event, idx) in events"
            :key="event.id"
            :to="{ name: 'event-detail', params: { eventId: event.id } }"
            class="group relative flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-cypher-border bg-cypher-surface transition-all duration-300 hover:-translate-y-1 hover:border-cypher-border-glow hover:shadow-glow-sm"
            :style="`animation: slideUp 0.5s ease-out ${idx * 0.06}s both`"
          >
            <!-- Thumbnail -->
            <div
              class="relative aspect-[16/9] w-full shrink-0 overflow-hidden"
              :class="`bg-gradient-to-br ${eventCardGradient(event)}`"
            >
              <img
                v-if="event.thumbnail_path"
                :src="eventMediaUrl(event.thumbnail_path)"
                :alt="event.title"
                class="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                @error="($event.target as HTMLImageElement).style.display = 'none'"
              />
              <!-- Gradient overlay -->
              <div class="absolute inset-0 bg-gradient-to-t from-cypher-bg via-cypher-bg/20 to-transparent" />

              <!-- No image placeholder -->
              <div v-if="!event.thumbnail_path" class="absolute inset-0 flex items-center justify-center">
                <svg class="h-16 w-16 text-white/10 transition-opacity duration-300 group-hover:text-white/20" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z" />
                </svg>
              </div>

              <!-- Date chip -->
              <div class="absolute left-3 top-3 flex flex-col gap-1.5">
                <span class="rounded-lg border border-white/20 bg-black/50 px-2.5 py-1 text-xs font-bold text-white backdrop-blur-sm">
                  {{ formatDateShort(event.start_at) }}
                </span>
                <span v-if="sortMode === 'hot' && (event.total_sold_count ?? 0) > 0" class="badge-hot text-[10px]">
                  {{ event.total_sold_count }} 人報名
                </span>
              </div>

              <!-- Hover arrow -->
              <div class="absolute bottom-3 right-3 flex h-8 w-8 items-center justify-center rounded-full bg-cypher-accent/0 text-white opacity-0 transition-all duration-300 group-hover:bg-cypher-accent group-hover:opacity-100">
                <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25" />
                </svg>
              </div>
            </div>

            <!-- Card body -->
            <div class="flex flex-1 flex-col p-5">
              <h3 class="font-display line-clamp-2 text-lg font-bold text-white transition-colors duration-200 group-hover:text-cypher-accent-cyan">
                {{ event.title }}
              </h3>
              <p class="mt-2 line-clamp-2 flex-1 text-sm leading-relaxed text-gray-500">
                {{ event.short_desc || event.description || "無描述" }}
              </p>
              <!-- Location -->
              <div class="mt-4 flex items-center gap-2 text-xs text-cypher-muted">
                <svg class="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                </svg>
                <span class="truncate">{{ event.location_name || "地點待定" }}</span>
              </div>
              <!-- Tags -->
              <div class="mt-3 flex flex-wrap gap-1.5">
                <span v-for="style in (event.dance_styles || []).slice(0, 2)" :key="style" class="badge-dance">
                  {{ styleLabelFromKey(style) }}
                </span>
                <span v-for="type in (event.event_types || []).slice(0, 1)" :key="type" class="badge-type">
                  {{ eventTypeLabelFromKey(type) }}
                </span>
              </div>
            </div>
          </RouterLink>
        </div>
      </div>
    </section>
  </main>
</template>
