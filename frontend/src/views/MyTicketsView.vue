<script setup lang="ts">
import QrcodeVue from "qrcode.vue";
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import {
  cancelTicket,
  fetchEventDetail,
  fetchMyTickets,
  resendTicket,
  type EventDetail,
  type TicketItem,
} from "../api/client";
import { toApiErrorMessage } from "../utils/errorMessages";

const tickets = ref<TicketItem[]>([]);
const eventMap = ref<Record<string, EventDetail>>({});
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const resendMessage = ref<string | null>(null);
const copyMessage = ref<string | null>(null);
const cancelMessage = ref<string | null>(null);
const cancellingId = ref<string | null>(null);

function qrPayload(ticket: TicketItem): string {
  return JSON.stringify({
    ticket_id: ticket.ticket_id,
    qr_secret: ticket.qr_secret,
  });
}

function formatDateShort(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("zh-TW", { month: "short", day: "numeric", weekday: "short" });
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("zh-TW", { dateStyle: "medium", timeStyle: "short" });
}

function ticketTypeName(ticket: TicketItem): string {
  const detail = eventMap.value[ticket.event_id];
  if (!detail?.ticket_types) return "入場券";
  const tt = detail.ticket_types.find((t) => t.id === ticket.ticket_type_id);
  return tt?.name ?? "入場券";
}

function statusLabel(s: string): string {
  const m: Record<string, string> = {
    issued: "有效",
    checked_in: "已入場",
    cancelled: "已取消",
  };
  return m[s] ?? s;
}

function statusBadgeClass(s: string): string {
  const m: Record<string, string> = {
    issued: "bg-emerald-500/20 text-emerald-400",
    checked_in: "bg-cypher-accent/20 text-cypher-accent",
    cancelled: "bg-rose-500/20 text-rose-400",
  };
  return m[s] ?? "bg-cypher-surface-alt text-cypher-muted";
}

function eventForTicket(ticket: TicketItem): EventDetail["event"] | null {
  return eventMap.value[ticket.event_id]?.event ?? null;
}

async function loadTickets(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  eventMap.value = {};

  try {
    const items = await fetchMyTickets();
    tickets.value = items;

    // 並行載入活動詳情
    const eventIds = [...new Set(items.map((t) => t.event_id).filter(Boolean))];
    const details = await Promise.allSettled(
      eventIds.map((id) => fetchEventDetail(id))
    );
    const map: Record<string, EventDetail> = {};
    details.forEach((result, i) => {
      if (result.status === "fulfilled" && eventIds[i]) {
        map[eventIds[i]] = result.value;
      }
    });
    eventMap.value = map;
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Failed to load tickets");
  } finally {
    loading.value = false;
  }
}

async function handleResend(ticketId: string): Promise<void> {
  resendMessage.value = null;
  try {
    await resendTicket(ticketId);
    resendMessage.value = "已重寄票券信至您的信箱。";
  } catch (error: unknown) {
    resendMessage.value = toApiErrorMessage(error, "重寄失敗");
  }
}

async function copyPayload(ticket: TicketItem): Promise<void> {
  copyMessage.value = null;
  const payload = qrPayload(ticket);
  try {
    if (!navigator.clipboard?.writeText) {
      throw new Error("Clipboard API not supported");
    }
    await navigator.clipboard.writeText(payload);
    copyMessage.value = "已複製 QR payload";
  } catch {
    copyMessage.value = "無法直接複製，請手動複製 QR payload。";
  }
}

async function handleCancel(ticketId: string): Promise<void> {
  if (!confirm("確定要取消這張票券的報名嗎？取消後名額將釋出。")) return;
  cancelMessage.value = null;
  cancellingId.value = ticketId;
  try {
    await cancelTicket(ticketId);
    cancelMessage.value = "已取消報名。";
    await loadTickets();
  } catch (error: unknown) {
    cancelMessage.value = toApiErrorMessage(error, "取消報名失敗");
  } finally {
    cancellingId.value = null;
  }
}

onMounted(() => {
  loadTickets().catch(() => {});
});
</script>

<template>
  <main class="mx-auto w-full max-w-5xl px-4 py-12">
    <header class="mb-10 animate-fade-in">
      <h1 class="font-street text-3xl tracking-widest text-white sm:text-4xl">My Tickets</h1>
      <p class="mt-2 text-sm text-cypher-muted">您的票券與入場 QR Code</p>
    </header>

    <div v-if="loading" class="card flex items-center justify-center p-12 text-cypher-muted">
      <span class="h-8 w-8 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" />
      <span class="ml-3">Loading tickets...</span>
    </div>
    <div v-else-if="errorMessage" role="alert" class="card border-rose-500/40 bg-rose-950/60 p-6 text-rose-300">
      {{ errorMessage }}
    </div>
    <div v-else-if="tickets.length === 0" class="card flex flex-col items-center justify-center p-16 text-center">
      <p class="text-cypher-muted">尚未有票券</p>
      <RouterLink to="/" class="btn-primary mt-4">探索活動</RouterLink>
    </div>

    <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <article
        v-for="(ticket, i) in tickets"
        :key="ticket.ticket_id"
        class="card flex flex-col overflow-hidden transition-all duration-300 hover:border-cypher-accent/50 hover:shadow-glow-sm"
        :style="`animation: slideUp 0.5s ease-out ${i * 0.05}s both`"
      >
        <!-- 活動資訊區 -->
        <div class="border-b border-cypher-border p-4">
          <h2 class="font-street line-clamp-2 text-lg tracking-wide text-white">
            {{ eventMap[ticket.event_id]?.event?.title ?? "載入中…" }}
          </h2>
          <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-cypher-muted">
            <span>{{ formatDateShort(eventMap[ticket.event_id]?.event?.start_at) }}</span>
            <span v-if="eventMap[ticket.event_id]?.event?.location_name" class="truncate">
              · {{ eventMap[ticket.event_id]?.event?.location_name }}
            </span>
          </div>
          <div class="mt-2 flex items-center gap-2">
            <span
              class="rounded-full px-2 py-0.5 text-xs font-semibold"
              :class="statusBadgeClass(ticket.status)"
            >
              {{ statusLabel(ticket.status) }}
            </span>
            <span class="text-xs text-cypher-muted">{{ ticketTypeName(ticket) }}</span>
          </div>
        </div>

        <!-- QR Code -->
        <div class="flex flex-1 flex-col items-center justify-center border-b border-cypher-border bg-cypher-surface-alt/30 p-5">
          <QrcodeVue :value="qrPayload(ticket)" :size="160" level="M" class="rounded-lg bg-white p-2" />
        </div>

        <!-- 操作區 -->
        <div class="flex flex-col gap-2 p-4">
          <RouterLink
            v-if="ticket.event_id"
            :to="{ name: 'event-detail', params: { eventId: ticket.event_id } }"
            class="btn-primary flex items-center justify-center gap-2 py-2.5 text-sm"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            前往活動
          </RouterLink>
          <button type="button" class="btn-secondary py-2 text-sm" @click="handleResend(ticket.ticket_id)">
            重寄票券信
          </button>
          <button type="button" class="btn-secondary py-2 text-sm" @click="copyPayload(ticket)">
            Copy Payload
          </button>
          <button
            type="button"
            class="rounded-xl border border-rose-500/50 px-3 py-2 text-sm font-semibold text-rose-400 transition-colors hover:bg-rose-500/10 disabled:opacity-50"
            :disabled="cancellingId === ticket.ticket_id"
            @click="handleCancel(ticket.ticket_id)"
          >
            {{ cancellingId === ticket.ticket_id ? "取消中…" : "取消報名" }}
          </button>
        </div>

        <p class="px-4 pb-2 text-center text-[10px] text-cypher-muted">ID {{ ticket.ticket_id.slice(0, 8) }}</p>
      </article>
    </div>

    <p v-if="resendMessage" class="mt-4 text-sm text-emerald-400">{{ resendMessage }}</p>
    <p v-if="copyMessage" class="mt-2 text-sm text-cypher-muted">{{ copyMessage }}</p>
    <p v-if="cancelMessage" class="mt-2 text-sm" :class="cancelMessage.startsWith('已') ? 'text-emerald-400' : 'text-rose-400'">{{ cancelMessage }}</p>
  </main>
</template>
