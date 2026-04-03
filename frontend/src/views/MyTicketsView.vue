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
  <main class="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden px-4 py-12">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="pointer-events-none absolute inset-0" style="background: radial-gradient(ellipse 60% 40% at 80% 20%, rgba(124,58,237,0.08) 0%, transparent 70%)" aria-hidden="true" />

    <div class="relative z-10 mx-auto w-full max-w-5xl">
      <!-- Header -->
      <header class="animate-slide-up mb-10">
        <p class="section-label mb-2">My Tickets</p>
        <div class="flex items-center gap-3">
          <span class="h-6 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
          <h1 class="font-street text-3xl tracking-widest text-white sm:text-4xl">我的票券</h1>
        </div>
        <p class="mt-2 pl-3.5 text-sm text-cypher-muted">您的入場 QR Code 與票券管理</p>
      </header>

      <!-- Loading -->
      <div v-if="loading" class="card-glass flex items-center justify-center gap-3 p-16 text-cypher-muted">
        <span class="h-6 w-6 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" aria-hidden="true" />
        <span class="text-sm">載入票券中…</span>
      </div>

      <!-- Error -->
      <div v-else-if="errorMessage" role="alert" class="card-glass flex items-start gap-3 border-rose-500/30 p-6">
        <svg class="mt-0.5 h-5 w-5 shrink-0 text-rose-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        <p class="text-sm text-rose-300">{{ errorMessage }}</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="tickets.length === 0" class="card-glass flex flex-col items-center justify-center gap-5 p-16 text-center">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-cypher-surface-alt">
          <svg class="h-8 w-8 text-cypher-muted" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 010 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 010-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375z" />
          </svg>
        </div>
        <div>
          <p class="text-base font-semibold text-white">尚無任何票券</p>
          <p class="mt-1 text-sm text-cypher-muted">前往探索活動並完成報名後，票券將顯示於此</p>
        </div>
        <RouterLink to="/" class="btn-primary px-6 py-2.5 text-sm">探索活動</RouterLink>
      </div>

      <!-- Ticket grid -->
      <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="(ticket, i) in tickets"
          :key="ticket.ticket_id"
          class="group relative flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md transition-all duration-300 hover:border-cypher-accent/40 hover:shadow-glow-sm"
          :style="`animation: slideUp 0.5s ease-out ${i * 0.06}s both`"
        >
          <!-- Top glow accent -->
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/50 to-transparent" aria-hidden="true" />

          <!-- Event info -->
          <div class="border-b border-white/5 p-4">
            <div class="flex items-start justify-between gap-2">
              <h2 class="font-street line-clamp-2 text-base tracking-wide text-white leading-snug">
                {{ eventMap[ticket.event_id]?.event?.title ?? "載入中…" }}
              </h2>
              <span
                class="shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold"
                :class="{
                  'border-emerald-500/40 bg-emerald-500/10 text-emerald-400': ticket.status === 'issued',
                  'border-cypher-accent/40 bg-cypher-accent/10 text-cypher-accent-bright': ticket.status === 'checked_in',
                  'border-rose-500/40 bg-rose-500/10 text-rose-400': ticket.status === 'cancelled',
                  'border-white/10 bg-white/5 text-cypher-muted': !['issued','checked_in','cancelled'].includes(ticket.status),
                }"
              >
                {{ statusLabel(ticket.status) }}
              </span>
            </div>

            <div class="mt-2.5 space-y-1 text-xs text-cypher-muted">
              <div class="flex items-center gap-1.5">
                <svg class="h-3.5 w-3.5 shrink-0 text-cypher-accent/60" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                </svg>
                <span>{{ formatDateShort(eventMap[ticket.event_id]?.event?.start_at) }}</span>
              </div>
              <div v-if="eventMap[ticket.event_id]?.event?.location_name" class="flex items-center gap-1.5">
                <svg class="h-3.5 w-3.5 shrink-0 text-cypher-accent/60" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                </svg>
                <span class="truncate">{{ eventMap[ticket.event_id]?.event?.location_name }}</span>
              </div>
            </div>

            <p class="mt-2 text-[11px] text-cypher-muted/70">{{ ticketTypeName(ticket) }}</p>
          </div>

          <!-- QR Code -->
          <div class="flex flex-1 flex-col items-center justify-center bg-white/[0.02] px-5 py-6">
            <div
              class="relative rounded-xl p-1 transition-all duration-300"
              :class="ticket.status === 'cancelled' ? 'opacity-40 grayscale' : 'shadow-glow-sm'"
              style="background: linear-gradient(135deg, rgba(168,85,247,0.3), rgba(236,72,153,0.3))"
            >
              <div class="rounded-lg bg-white p-2">
                <QrcodeVue :value="qrPayload(ticket)" :size="148" level="M" />
              </div>
            </div>
            <p class="mt-3 font-mono text-[10px] tracking-wider text-cypher-muted/60">
              {{ ticket.ticket_id.slice(0, 8).toUpperCase() }}
            </p>
          </div>

          <!-- Dashed divider (ticket perforation) -->
          <div class="relative flex items-center px-4" aria-hidden="true">
            <div class="absolute -left-3 h-6 w-6 rounded-full bg-cypher-bg" />
            <div class="h-px w-full border-t border-dashed border-white/10" />
            <div class="absolute -right-3 h-6 w-6 rounded-full bg-cypher-bg" />
          </div>

          <!-- Actions -->
          <div class="flex flex-col gap-2 p-4 pt-3">
            <RouterLink
              v-if="ticket.event_id"
              :to="{ name: 'event-detail', params: { eventId: ticket.event_id } }"
              class="btn-primary flex items-center justify-center gap-2 py-2.5 text-sm"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
              </svg>
              前往活動頁面
            </RouterLink>

            <div class="flex gap-2">
              <button
                type="button"
                class="flex-1 rounded-xl border border-cypher-border bg-cypher-surface py-2 text-xs font-medium text-gray-300 transition-all hover:border-cypher-accent/40 hover:bg-cypher-surface-alt hover:text-white"
                @click="handleResend(ticket.ticket_id)"
              >
                重寄票券信
              </button>
              <button
                type="button"
                class="flex-1 rounded-xl border border-cypher-border bg-cypher-surface py-2 text-xs font-medium text-gray-300 transition-all hover:border-cypher-accent/40 hover:bg-cypher-surface-alt hover:text-white"
                @click="copyPayload(ticket)"
              >
                複製 Payload
              </button>
            </div>

            <button
              v-if="ticket.status === 'issued'"
              type="button"
              class="rounded-xl border border-rose-500/30 py-2 text-xs font-semibold text-rose-400/80 transition-all hover:border-rose-500/60 hover:bg-rose-500/10 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="cancellingId === ticket.ticket_id"
              @click="handleCancel(ticket.ticket_id)"
            >
              {{ cancellingId === ticket.ticket_id ? "取消中…" : "取消報名" }}
            </button>
          </div>
        </article>
      </div>

      <!-- Toast messages -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
      >
        <div v-if="resendMessage || copyMessage || cancelMessage" class="mt-6 space-y-2">
          <div
            v-if="resendMessage"
            class="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400"
          >
            <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ resendMessage }}
          </div>
          <p v-if="copyMessage" class="text-sm text-cypher-muted">{{ copyMessage }}</p>
          <div
            v-if="cancelMessage"
            class="flex items-center gap-2 rounded-xl border px-4 py-3 text-sm"
            :class="cancelMessage.startsWith('已') ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-rose-500/30 bg-rose-500/10 text-rose-400'"
          >
            {{ cancelMessage }}
          </div>
        </div>
      </Transition>
    </div>
  </main>
</template>
