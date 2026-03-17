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
    hiphop: "from-violet-600 to-purple-800",
    popping: "from-amber-600 to-orange-700",
    locking: "from-rose-600 to-pink-700",
    breaking: "from-sky-600 to-blue-800",
    house: "from-emerald-600 to-teal-700",
    waacking: "from-fuchsia-600 to-purple-700",
    default: "from-gray-600 to-gray-800",
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
  <main class="mx-auto w-full max-w-6xl px-4 pb-16 pt-8 sm:pt-12">
    <!-- Hero -->
    <section class="mb-12">
      <h1 class="font-display text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
        街舞活動，從這裡開始
      </h1>
      <p class="mt-2 text-lg text-gray-600">
        探索工作坊、賽事、社團與派對
      </p>

      <!-- Search + Filter Toggle -->
      <div class="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center">
        <div class="relative flex-1">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜尋活動名稱、地點..."
            class="w-full rounded-lg border border-gray-300 bg-white py-3 pl-4 pr-10 text-gray-900 placeholder-gray-400 shadow-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
            @keydown.enter="applyFilters"
          />
          <button
            type="button"
            class="btn-primary absolute right-1.5 top-1/2 -translate-y-1/2 py-2 text-sm"
            @click="applyFilters"
          >
            搜尋
          </button>
        </div>
        <button
          type="button"
          class="flex shrink-0 items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
          @click="filterOpen = !filterOpen"
        >
          <span class="inline-block transition" :class="filterOpen ? 'rotate-180' : ''">▼</span>
          篩選
          <span v-if="selectedStyles.length || selectedTypes.length" class="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700">
            {{ selectedStyles.length + selectedTypes.length }}
          </span>
        </button>
      </div>

      <!-- Collapsible Filters -->
      <div
        v-show="filterOpen"
        class="mt-4 overflow-hidden rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all"
      >
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">舞風 · 活動類型 · 日期</span>
          <button
            type="button"
            class="text-sm font-medium text-brand-600 hover:text-brand-700"
            @click="clearFilters"
          >
            清除
          </button>
        </div>
        <div class="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-xs font-medium text-gray-500">開始日期</label>
            <input
              v-model="dateFrom"
              type="date"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-gray-500">結束日期</label>
            <input
              v-model="dateTo"
              type="date"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </div>
        </div>
        <div class="mt-4">
          <p class="mb-2 text-xs font-medium text-gray-500">舞風</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="style in DANCE_STYLES"
              :key="style.key"
              type="button"
              class="rounded-full px-3 py-1.5 text-xs font-medium transition"
              :class="
                selectedStyles.includes(style.key)
                  ? 'bg-brand-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              "
              @click="toggleStyle(style.key)"
            >
              {{ style.label }}
            </button>
          </div>
        </div>
        <div class="mt-4">
          <p class="mb-2 text-xs font-medium text-gray-500">活動類型</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="type in EVENT_TYPES"
              :key="type.key"
              type="button"
              class="rounded-full px-3 py-1.5 text-xs font-medium transition"
              :class="
                selectedTypes.includes(type.key)
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              "
              @click="toggleType(type.key)"
            >
              {{ type.label }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Events List -->
    <section>
      <h2 class="mb-6 font-display text-xl font-semibold text-gray-900">
        所有活動
      </h2>

      <div v-if="loading" class="flex flex-col items-center justify-center py-16">
        <span class="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        <p class="mt-3 text-gray-500">載入活動中...</p>
      </div>

      <div v-else-if="errorMessage" class="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        {{ errorMessage }}
      </div>

      <div v-else-if="events.length === 0" class="rounded-xl border border-gray-200 bg-white py-16 text-center text-gray-500">
        目前沒有符合條件的活動
      </div>

      <div v-else class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="event in events"
          :key="event.id"
          :to="{ name: 'event-detail', params: { eventId: event.id } }"
          class="group overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition-all hover:border-gray-300 hover:shadow-md"
        >
          <!-- Image placeholder (Eventbrite-style: image first) -->
          <div
            class="relative aspect-[16/9] w-full shrink-0"
            :class="`bg-gradient-to-br ${eventCardGradient(event)}`"
          >
            <div class="absolute inset-0 flex items-center justify-center opacity-30">
              <svg class="h-16 w-16 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            </div>
            <span
              class="absolute left-3 top-3 rounded-md bg-white/95 px-2.5 py-1 text-xs font-semibold text-gray-800 shadow"
            >
              {{ formatDateShort(event.start_at) }}
            </span>
          </div>

          <div class="p-4">
            <h3 class="font-display line-clamp-2 text-lg font-semibold text-gray-900 group-hover:text-brand-600">
              {{ event.title }}
            </h3>
            <p class="mt-1 line-clamp-2 text-sm text-gray-600">
              {{ event.short_desc || event.description || "無描述" }}
            </p>
            <p class="mt-2 text-xs text-gray-500">
              {{ event.location_name || "地點待定" }}
            </p>
            <div class="mt-3 flex flex-wrap gap-1.5">
              <span
                v-for="style in (event.dance_styles || []).slice(0, 2)"
                :key="style"
                class="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700"
              >
                {{ styleLabelFromKey(style) }}
              </span>
              <span
                v-for="type in (event.event_types || []).slice(0, 1)"
                :key="type"
                class="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700"
              >
                {{ eventTypeLabelFromKey(type) }}
              </span>
            </div>
          </div>
        </RouterLink>
      </div>
    </section>
  </main>
</template>
