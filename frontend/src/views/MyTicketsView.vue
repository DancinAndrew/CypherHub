<script setup lang="ts">
import QrcodeVue from "qrcode.vue";
import { onMounted, ref } from "vue";

import { cancelTicket, fetchMyTickets, resendTicket, type TicketItem } from "../api/client";
import { toApiErrorMessage } from "../utils/errorMessages";

const tickets = ref<TicketItem[]>([]);
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

async function loadTickets(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    tickets.value = await fetchMyTickets();
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
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      throw new Error("Clipboard API not supported");
    }
    await navigator.clipboard.writeText(payload);
    copyMessage.value = `Copied payload for ticket ${ticket.ticket_id.slice(0, 8)}...`;
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
  <main class="mx-auto w-full max-w-5xl px-4 py-10">
    <h1 class="text-3xl font-bold text-slate-900">My Tickets</h1>

    <div v-if="loading" class="mt-6 rounded-xl border border-slate-200 bg-white p-5 text-slate-600">Loading tickets...</div>
    <div v-else-if="errorMessage" class="mt-6 rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-700">
      {{ errorMessage }}
    </div>
    <div v-else-if="tickets.length === 0" class="mt-6 rounded-xl border border-slate-200 bg-white p-5 text-slate-600">
      No issued tickets.
    </div>

    <div v-else class="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <article v-for="ticket in tickets" :key="ticket.ticket_id" class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-sm font-semibold text-slate-900">Ticket {{ ticket.ticket_id.slice(0, 8) }}</h2>
        <p class="mt-1 text-xs text-slate-500">Status: {{ ticket.status }}</p>
        <p class="mt-1 text-xs text-slate-500">Issued: {{ ticket.issued_at ? new Date(ticket.issued_at).toLocaleString() : "-" }}</p>

        <div class="mt-4 flex justify-center rounded-lg bg-slate-50 p-3">
          <QrcodeVue :value="qrPayload(ticket)" :size="160" level="M" />
        </div>

        <button
          type="button"
          class="mt-4 inline-flex rounded-lg border border-brand-600 px-3 py-2 text-xs font-semibold text-brand-700 hover:bg-brand-50"
          @click="handleResend(ticket.ticket_id)"
        >
          重寄票券信
        </button>
        <button
          type="button"
          class="mt-2 inline-flex rounded-lg border border-slate-400 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          @click="copyPayload(ticket)"
        >
          Copy Payload
        </button>
        <button
          type="button"
          class="mt-2 inline-flex rounded-lg border border-rose-400 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
          :disabled="cancellingId === ticket.ticket_id"
          @click="handleCancel(ticket.ticket_id)"
        >
          {{ cancellingId === ticket.ticket_id ? "取消中…" : "取消報名" }}
        </button>
      </article>
    </div>

    <p v-if="resendMessage" class="mt-4 text-sm text-brand-700">{{ resendMessage }}</p>
    <p v-if="copyMessage" class="mt-2 text-sm text-slate-700">{{ copyMessage }}</p>
    <p v-if="cancelMessage" class="mt-2 text-sm" :class="cancelMessage.startsWith('已') ? 'text-emerald-700' : 'text-rose-700'">{{ cancelMessage }}</p>
  </main>
</template>
