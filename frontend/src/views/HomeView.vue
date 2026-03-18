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
    },
  });
  await loadEvents();
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
  loadEvents().catch(() => {});
});
</script>

<template>
  <main class="relative min-h-screen overflow-hidden">
    <!-- Hero: gradient mesh + bold typography -->
    <section class="relative px-4 pt-16 pb-12 sm:pt-24 sm:pb-20">
      <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(168,85,247,0.25),transparent)]" aria-hidden="true" />

      <div class="relative mx-auto max-w-6xl">
        <div class="animate-slide-up">
          <p class="font-street text-cypher-accent-cyan text-sm uppercase tracking-[0.4em]">
            Street Dance · 你的下一場 Battle
          </p>
          <h1 class="mt-4 font-street text-5xl leading-[1.05] tracking-wide text-white sm:text-7xl md:text-8xl">
            街舞活動<br />
            <span class="bg-gradient-to-r from-cypher-accent via-cypher-accent-pink to-cypher-accent-cyan bg-clip-text text-transparent">
              從這裡開始
            </span>
          </h1>
          <p class="mt-6 max-w-xl text-lg text-gray-400 animate-slide-up-delay">
            工作坊 · 賽事 · 社團 · 派對 — 探索、報名、站上舞台
          </p>
        </div>

        <!-- Search + Filter -->
        <div class="mt-10 flex flex-col gap-4 sm:flex-row sm:items-stretch animate-slide-up-delay-2">
          <div class="relative flex-1">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜尋活動名稱、地點..."
              class="input-field w-full py-3.5 pl-5 pr-28"
              @keydown.enter="applyFilters"
            />
            <button
              type="button"
              class="btn-primary absolute right-2 top-1/2 -translate-y-1/2 py-2.5 text-sm"
              @click="applyFilters"
            >
              搜尋
            </button>
          </div>
          <button
            type="button"
            class="flex shrink-0 items-center justify-center gap-2 rounded-xl border border-cypher-border bg-cypher-surface px-5 py-3.5 font-medium text-gray-300 transition-all hover:border-cypher-accent/50 hover:text-white"
            @click="filterOpen = !filterOpen"
          >
            <span class="text-lg transition-transform duration-300" :class="filterOpen ? 'rotate-180' : ''">▼</span>
            篩選
            <span
              v-if="selectedStyles.length || selectedTypes.length"
              class="rounded-full bg-cypher-accent px-2.5 py-0.5 text-xs font-bold text-white"
            >
              {{ selectedStyles.length + selectedTypes.length }}
            </span>
          </button>
        </div>

        <!-- Collapsible Filters -->
        <Transition
          enter-active-class="transition-all duration-300 ease-out"
          enter-from-class="opacity-0 max-h-0"
          enter-to-class="opacity-100 max-h-[500px]"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 max-h-[500px]"
          leave-to-class="opacity-0 max-h-0"
        >
          <div
            v-show="filterOpen"
            class="mt-6 overflow-hidden rounded-2xl border border-cypher-border bg-cypher-surface/80 p-6 backdrop-blur-sm"
          >
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-300">舞風 · 活動類型 · 日期</span>
              <button type="button" class="text-sm font-semibold text-cypher-accent hover:text-cypher-accent-pink" @click="clearFilters">
                清除
              </button>
            </div>
            <div class="mt-5 grid gap-4 sm:grid-cols-2">
              <div>
                <label class="mb-2 block text-xs font-medium text-cypher-muted">開始日期</label>
                <input v-model="dateFrom" type="date" class="input-field py-2.5 text-sm" />
              </div>
              <div>
                <label class="mb-2 block text-xs font-medium text-cypher-muted">結束日期</label>
                <input v-model="dateTo" type="date" class="input-field py-2.5 text-sm" />
              </div>
            </div>
            <div class="mt-5">
              <p class="mb-3 text-xs font-medium text-cypher-muted">舞風</p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="style in DANCE_STYLES"
                  :key="style.key"
                  type="button"
                  class="rounded-full px-4 py-2 text-xs font-semibold transition-all duration-200"
                  :class="
                    selectedStyles.includes(style.key)
                      ? 'bg-gradient-to-r from-cypher-accent to-cypher-accent-pink text-white shadow-glow-sm'
                      : 'bg-cypher-surface-alt text-gray-400 hover:border hover:border-cypher-accent/50 hover:text-gray-200'
                  "
                  @click="toggleStyle(style.key)"
                >
                  {{ style.label }}
                </button>
              </div>
            </div>
            <div class="mt-5">
              <p class="mb-3 text-xs font-medium text-cypher-muted">活動類型</p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="type in EVENT_TYPES"
                  :key="type.key"
                  type="button"
                  class="rounded-full px-4 py-2 text-xs font-semibold transition-all duration-200"
                  :class="
                    selectedTypes.includes(type.key)
                      ? 'bg-cypher-accent-pink text-white'
                      : 'bg-cypher-surface-alt text-gray-400 hover:border hover:border-cypher-accent-pink/50 hover:text-gray-200'
                  "
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

    <!-- Events List -->
    <section class="relative px-4 pb-24 pt-4">
      <div class="mx-auto max-w-6xl">
        <h2 class="mb-8 font-street text-3xl tracking-wider text-white sm:text-4xl animate-fade-in">
          <span class="text-cypher-muted">//</span> 所有活動
        </h2>

        <div v-if="loading" class="flex flex-col items-center justify-center py-24">
          <div class="h-12 w-12 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" />
          <p class="mt-5 font-medium text-cypher-muted">載入活動中...</p>
        </div>

        <div
          v-else-if="errorMessage"
          class="rounded-2xl border border-rose-500/50 bg-rose-950/50 p-8 text-center text-rose-300"
        >
          {{ errorMessage }}
        </div>

        <div
          v-else-if="events.length === 0"
          class="rounded-2xl border border-cypher-border bg-cypher-surface py-24 text-center text-cypher-muted"
        >
          目前沒有符合條件的活動
        </div>

        <div v-else class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <RouterLink
            v-for="(event, idx) in events"
            :key="event.id"
            :to="{ name: 'event-detail', params: { eventId: event.id } }"
            class="group relative overflow-hidden rounded-2xl border border-cypher-border bg-cypher-surface transition-all duration-300 hover:scale-[1.02] hover:border-cypher-accent/50 hover:shadow-glow-sm"
            :style="`animation: slideUp 0.5s ease-out ${idx * 0.06}s both`"
          >
            <!-- Card Image -->
            <div
              class="relative aspect-[16/9] w-full overflow-hidden bg-cypher-surface"
              :class="`bg-gradient-to-br ${eventCardGradient(event)}`"
            >
              <img
                v-if="event.thumbnail_path"
                :src="eventMediaUrl(event.thumbnail_path)"
                :alt="event.title"
                class="absolute inset-0 h-full w-full object-cover"
                @error="($event.target as HTMLImageElement).style.display = 'none'"
              />
              <div class="absolute inset-0 bg-gradient-to-t from-cypher-bg/90 via-transparent to-transparent" />
              <div
                v-if="!event.thumbnail_path"
                class="absolute inset-0 flex items-center justify-center opacity-20 transition-opacity group-hover:opacity-40"
              >
                <svg class="h-20 w-20 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                </svg>
              </div>
              <span
                class="absolute left-4 top-4 rounded-lg border border-white/30 bg-black/40 px-3 py-1.5 text-xs font-bold text-white backdrop-blur-sm"
              >
                {{ formatDateShort(event.start_at) }}
              </span>
              <span
                class="absolute bottom-4 right-4 rounded-md bg-cypher-accent/90 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-white opacity-0 transition-all duration-300 group-hover:opacity-100"
              >
                查看 →
              </span>
            </div>

            <div class="p-5">
              <h3 class="font-display line-clamp-2 text-xl font-bold text-white transition-colors group-hover:text-cypher-accent-cyan">
                {{ event.title }}
              </h3>
              <p class="mt-2 line-clamp-2 text-sm text-gray-400">
                {{ event.short_desc || event.description || "無描述" }}
              </p>
              <p class="mt-3 flex items-center gap-1.5 text-xs text-cypher-muted">
                <span class="inline-block h-1 w-1 rounded-full bg-cypher-accent" />
                {{ event.location_name || "地點待定" }}
              </p>
              <div class="mt-4 flex flex-wrap gap-2">
                <span
                  v-for="style in (event.dance_styles || []).slice(0, 2)"
                  :key="style"
                  class="badge-dance"
                >
                  {{ styleLabelFromKey(style) }}
                </span>
                <span
                  v-for="type in (event.event_types || []).slice(0, 1)"
                  :key="type"
                  class="badge-type"
                >
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
