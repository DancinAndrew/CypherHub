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

const selectedStyles = ref<DanceStyleKey[]>([]);
const selectedTypes = ref<EventTypeKey[]>([]);

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
  applyFilters().catch(() => {});
}

async function loadEvents(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    events.value = await fetchEvents({
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
      styles: selectedStyles.value.length ? selectedStyles.value.join(",") : undefined,
      types: selectedTypes.value.length ? selectedTypes.value.join(",") : undefined,
    },
  });
  await loadEvents();
}

onMounted(() => {
  selectedStyles.value = parseQueryList(route.query.styles, styleKeys) as DanceStyleKey[];
  selectedTypes.value = parseQueryList(route.query.types, typeKeys) as EventTypeKey[];
  loadEvents().catch(() => {});
});
</script>

<template>
  <main class="mx-auto w-full max-w-6xl px-4 py-10">
    <header class="mb-8">
      <h1 class="text-3xl font-bold text-slate-900">Published Events</h1>
      <p class="mt-2 text-sm text-slate-600">MVP-1.1：支援舞風/活動類型篩選</p>
    </header>

    <section class="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div class="flex items-center justify-between gap-3">
        <h2 class="text-lg font-semibold text-slate-900">Filters</h2>
        <button
          type="button"
          class="rounded-lg border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          @click="clearFilters"
        >
          Clear
        </button>
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold text-slate-500">Dance Styles</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <button
            v-for="style in DANCE_STYLES"
            :key="style.key"
            type="button"
            class="rounded-full border px-3 py-1 text-xs font-semibold"
            :class="
              selectedStyles.includes(style.key)
                ? 'border-brand-600 bg-brand-50 text-brand-700'
                : 'border-slate-300 text-slate-600 hover:bg-slate-50'
            "
            @click="toggleStyle(style.key)"
          >
            {{ style.label }}
          </button>
        </div>
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold text-slate-500">Event Types</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <button
            v-for="type in EVENT_TYPES"
            :key="type.key"
            type="button"
            class="rounded-full border px-3 py-1 text-xs font-semibold"
            :class="
              selectedTypes.includes(type.key)
                ? 'border-brand-600 bg-brand-50 text-brand-700'
                : 'border-slate-300 text-slate-600 hover:bg-slate-50'
            "
            @click="toggleType(type.key)"
          >
            {{ type.label }}
          </button>
        </div>
      </div>
    </section>

    <div v-if="loading" class="rounded-xl border border-slate-200 bg-white p-5 text-slate-600">Loading events...</div>
    <div v-else-if="errorMessage" class="rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-700">
      {{ errorMessage }}
    </div>
    <div v-else-if="events.length === 0" class="rounded-xl border border-slate-200 bg-white p-5 text-slate-600">
      No published events for current filters.
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2">
      <article v-for="event in events" :key="event.id" class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-xl font-semibold text-slate-900">{{ event.title }}</h2>
        <p class="mt-2 text-sm text-slate-600 line-clamp-3">
          {{ event.short_desc || event.description || "No description" }}
        </p>

        <div class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="style in event.dance_styles || []"
            :key="`${event.id}-style-${style}`"
            class="rounded-full bg-indigo-50 px-2 py-1 text-[11px] font-semibold text-indigo-700"
          >
            {{ styleLabelFromKey(style) }}
          </span>
          <span
            v-for="type in event.event_types || []"
            :key="`${event.id}-type-${type}`"
            class="rounded-full bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700"
          >
            {{ eventTypeLabelFromKey(type) }}
          </span>
        </div>

        <div class="mt-4 space-y-1 text-xs text-slate-500">
          <p>Start: {{ new Date(event.start_at).toLocaleString() }}</p>
          <p>Location: {{ event.location_name || "TBD" }}</p>
          <p v-if="event.registration_end_at">
            Registration deadline: {{ new Date(event.registration_end_at).toLocaleString() }}
          </p>
        </div>
        <RouterLink
          :to="{ name: 'event-detail', params: { eventId: event.id } }"
          class="mt-4 inline-flex rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          View Detail
        </RouterLink>
      </article>
    </div>
  </main>
</template>
