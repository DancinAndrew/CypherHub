<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { adminFetchEvents, adminUnpublishEvent, type EventItem } from "../api/client";
import { toApiErrorMessage } from "../utils/errorMessages";

const events = ref<EventItem[]>([]);
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const unpublishingId = ref<string | null>(null);

function statusLabel(s: string): string {
  const m: Record<string, string> = {
    draft: "草稿",
    published: "已上架",
    cancelled: "已取消",
    ended: "已結束",
    disabled: "已下架",
  };
  return m[s] ?? s;
}

function statusBadgeClass(s: string): string {
  const m: Record<string, string> = {
    draft: "bg-gray-100 text-gray-600",
    published: "bg-emerald-100 text-emerald-700",
    cancelled: "bg-rose-100 text-rose-700",
    ended: "bg-amber-100 text-amber-700",
    disabled: "bg-gray-100 text-gray-500",
  };
  return m[s] ?? "bg-gray-100 text-gray-600";
}

async function loadEvents(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  try {
    events.value = await adminFetchEvents();
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "載入活動失敗");
    events.value = [];
  } finally {
    loading.value = false;
  }
}

async function handleUnpublish(eventId: string): Promise<void> {
  if (unpublishingId.value) return;
  unpublishingId.value = eventId;
  try {
    await adminUnpublishEvent(eventId);
    const idx = events.value.findIndex((e) => e.id === eventId);
    if (idx >= 0) {
      events.value[idx] = { ...events.value[idx], status: "disabled" };
    }
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "下架失敗");
  } finally {
    unpublishingId.value = null;
  }
}

onMounted(() => {
  loadEvents().catch(() => {});
});
</script>

<template>
  <main class="mx-auto w-full max-w-6xl px-4 py-12">
    <header class="mb-8">
      <h1 class="font-display text-3xl font-bold text-gray-900">平台管理</h1>
      <p class="mt-2 text-sm text-gray-600">全站活動列表（含草稿、已上架、已下架）</p>
    </header>

    <div v-if="loading" class="card flex items-center justify-center p-8 text-gray-600">載入中…</div>
    <div v-else-if="errorMessage" role="alert" class="card border-rose-200 bg-rose-50 p-6 text-rose-800">
      {{ errorMessage }}
    </div>
    <div v-else-if="events.length === 0" class="card flex items-center justify-center p-8 text-gray-600">
      尚無活動。
    </div>

    <div v-else class="space-y-4">
      <article
        v-for="event in events"
        :key="event.id"
        class="card flex flex-wrap items-center justify-between gap-4 p-5"
      >
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <RouterLink
              v-if="event.status === 'published'"
              :to="{ name: 'event-detail', params: { eventId: event.id } }"
              class="text-lg font-semibold text-gray-900 transition-colors hover:text-brand-600"
            >
              {{ event.title }}
            </RouterLink>
            <span v-else class="text-lg font-semibold text-gray-900">{{ event.title }}</span>
            <span
              :class="statusBadgeClass(event.status)"
              class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
            >
              {{ statusLabel(event.status) }}
            </span>
          </div>
          <p class="mt-1 text-sm text-gray-500">
            {{ new Date(event.start_at).toLocaleString() }}
            <span v-if="event.location_name"> · {{ event.location_name }}</span>
          </p>
        </div>

        <div class="flex items-center gap-2">
          <RouterLink
            :to="{ name: 'event-detail', params: { eventId: event.id } }"
            class="btn-secondary py-2 text-sm"
          >
            詳情
          </RouterLink>
          <button
            v-if="event.status === 'published'"
            type="button"
            :disabled="unpublishingId === event.id"
            class="rounded-xl border border-rose-500/50 px-3 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-500/10 disabled:opacity-50"
            @click="handleUnpublish(event.id)"
          >
            {{ unpublishingId === event.id ? "下架中…" : "下架" }}
          </button>
        </div>
      </article>
    </div>
  </main>
</template>
