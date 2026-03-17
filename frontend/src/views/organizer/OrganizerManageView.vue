<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  fetchMyOrganizerSummary,
  organizerFetchAttendees,
  organizerResendAttendeeTicket,
  type AttendeeItem,
  type MyOrganizerEvent,
} from "../../api/client";
import { toApiErrorMessage } from "../../utils/errorMessages";

const eventId = ref("");
const myEvents = ref<MyOrganizerEvent[]>([]);
const summaryLoading = ref(true);
const attendees = ref<AttendeeItem[]>([]);
const loading = ref(false);
const loadError = ref<string | null>(null);

function formatEventOption(ev: MyOrganizerEvent): string {
  const date = ev.start_at ? new Date(ev.start_at).toLocaleDateString(undefined, { dateStyle: "short" }) : "";
  const status = ev.status === "published" ? "已上架" : "草稿";
  return `${ev.title}（${date}・${status}）`;
}

onMounted(async () => {
  summaryLoading.value = true;
  try {
    const data = await fetchMyOrganizerSummary();
    myEvents.value = data.events ?? [];
  } catch {
    myEvents.value = [];
  } finally {
    summaryLoading.value = false;
  }
});

const resendAttendeeTicketId = ref<string | null>(null);
const resendAttendeeMessage = ref<string | null>(null);

const stats = ref<{
  total: number;
  checkedIn: number;
  notCheckedIn: number;
  byTicketType: Array<{ ticket_type_id: string; total: number; checkedIn: number }>;
} | null>(null);

function formatAnswers(answers?: Record<string, unknown> | null): string {
  if (!answers || Object.keys(answers).length === 0) return "-";
  return JSON.stringify(answers, null, 2);
}

async function loadByEventId(): Promise<void> {
  const eid = eventId.value.trim();
  if (!eid) {
    attendees.value = [];
    stats.value = null;
    return;
  }
  loadError.value = null;
  loading.value = true;
  try {
    const items = await organizerFetchAttendees(eid);
    attendees.value = items;
    const active = items.filter((r) => r.status !== "cancelled");
    const checkedIn = active.filter((r) => r.status === "checked_in").length;
    const notCheckedIn = active.length - checkedIn;
    const byType: Record<string, { total: number; checkedIn: number }> = {};
    for (const r of active) {
      const tt = r.ticket_type_id ?? "unknown";
      if (!byType[tt]) byType[tt] = { total: 0, checkedIn: 0 };
      byType[tt].total += 1;
      if (r.status === "checked_in") byType[tt].checkedIn += 1;
    }
    stats.value = {
      total: active.length,
      checkedIn,
      notCheckedIn,
      byTicketType: Object.entries(byType).map(([ticket_type_id, v]) => ({
        ticket_type_id: ticket_type_id.slice(0, 8),
        total: v.total,
        checkedIn: v.checkedIn,
      })),
    };
  } catch (error: unknown) {
    loadError.value = toApiErrorMessage(error, "載入失敗");
    attendees.value = [];
    stats.value = null;
  } finally {
    loading.value = false;
  }
}

async function handleResendAttendeeTicket(ticketId: string): Promise<void> {
  const eid = eventId.value.trim();
  if (!eid) {
    resendAttendeeMessage.value = "請先選擇活動。";
    return;
  }
  resendAttendeeMessage.value = null;
  resendAttendeeTicketId.value = ticketId;
  try {
    await organizerResendAttendeeTicket(eid, ticketId);
    resendAttendeeMessage.value = "已重寄票券信至參加者信箱。";
  } catch (error: unknown) {
    resendAttendeeMessage.value = toApiErrorMessage(error, "重寄失敗");
  } finally {
    resendAttendeeTicketId.value = null;
  }
}
</script>

<template>
  <main class="mx-auto max-w-4xl px-4 py-10">
    <div class="mb-6">
      <router-link to="/organizer" class="text-sm text-slate-600 hover:text-brand-600">← 回主辦方管理中心</router-link>
    </div>

    <h1 class="text-2xl font-bold text-slate-900">主辦方管理</h1>
    <p class="mt-2 text-sm text-slate-600">選擇活動後可查核銷統計與代參加者重寄票券。</p>

    <!-- 選擇活動 -->
    <section class="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-800">選擇活動</h2>
      <div class="mt-3 flex flex-wrap items-center gap-3">
        <select
          v-model="eventId"
          class="min-w-[280px] rounded-lg border border-slate-300 px-4 py-2 text-sm"
          :disabled="summaryLoading"
          @change="loadByEventId"
        >
          <option value="">— 請選擇活動 —</option>
          <option v-for="ev in myEvents" :key="ev.id" :value="ev.id">
            {{ formatEventOption(ev) }}
          </option>
        </select>
        <button
          type="button"
          class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          :disabled="loading || !eventId"
          @click="loadByEventId"
        >
          {{ loading ? "載入中…" : "載入" }}
        </button>
      </div>
      <p v-if="summaryLoading" class="mt-2 text-sm text-slate-500">載入活動列表中…</p>
      <p v-else-if="myEvents.length === 0" class="mt-2 text-sm text-slate-500">尚無活動，請先建立活動。</p>
      <p v-if="loadError" class="mt-2 text-sm text-rose-600">{{ loadError }}</p>
    </section>

    <!-- 核銷統計 -->
    <section v-if="eventId.trim() && (stats || loading)" class="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-900">核銷統計</h2>
      <p v-if="loading" class="mt-2 text-sm text-slate-500">載入中…</p>
      <div v-else-if="stats" class="mt-3">
        <p class="text-base font-medium text-slate-700">
          已入場 <span class="text-brand-600">{{ stats.checkedIn }}</span> / 未入場
          <span class="text-slate-600">{{ stats.notCheckedIn }}</span>
          <span class="ml-2 text-sm text-slate-500">（總計 {{ stats.total }} 張有效票）</span>
        </p>
        <div v-if="stats.byTicketType.length" class="mt-3 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="border-b border-slate-200 text-left text-slate-600">
              <tr>
                <th class="pb-2 pr-4">票種 ID</th>
                <th class="pb-2 pr-4">已入場</th>
                <th class="pb-2">總數</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in stats.byTicketType" :key="row.ticket_type_id" class="border-b border-slate-100">
                <td class="py-1.5 pr-4 font-mono text-xs">{{ row.ticket_type_id }}</td>
                <td class="py-1.5 pr-4">{{ row.checkedIn }}</td>
                <td class="py-1.5">{{ row.total }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <button
          type="button"
          class="mt-3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          :disabled="loading"
          @click="loadByEventId"
        >
          重新載入統計
        </button>
      </div>
    </section>

    <!-- 代寄票券（名單與重寄） -->
    <section v-if="eventId.trim() && stats !== null" class="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-900">名單與代寄票券</h2>
      <p class="mt-1 text-sm text-slate-500">可對單張票券觸發「重寄票券信」至參加者信箱。</p>
      <p v-if="resendAttendeeMessage" class="mt-2 text-sm" :class="resendAttendeeMessage.startsWith('已') ? 'text-emerald-600' : 'text-rose-600'">
        {{ resendAttendeeMessage }}
      </p>
      <div class="mt-4 overflow-auto rounded-lg border border-slate-200">
        <table class="min-w-full text-sm">
          <thead class="bg-slate-100 text-left text-slate-600">
            <tr>
              <th class="px-3 py-2">票券 ID</th>
              <th class="px-3 py-2">user_id</th>
              <th class="px-3 py-2">狀態</th>
              <th class="px-3 py-2">已核銷</th>
              <th class="px-3 py-2">報名答案</th>
              <th class="px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in attendees" :key="row.ticket_id" class="border-t border-slate-200 align-top">
              <td class="px-3 py-2 font-mono text-xs">{{ row.ticket_id }}</td>
              <td class="px-3 py-2 font-mono text-xs">{{ row.user_id }}</td>
              <td class="px-3 py-2">{{ row.status }}</td>
              <td class="px-3 py-2">{{ row.checked_in_at || "—" }}</td>
              <td class="px-3 py-2">
                <pre class="whitespace-pre-wrap break-all text-xs text-slate-600">{{ formatAnswers(row.answers) }}</pre>
              </td>
              <td class="px-3 py-2">
                <button
                  v-if="row.status !== 'cancelled'"
                  type="button"
                  class="rounded border border-brand-600 px-2 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-50"
                  :disabled="resendAttendeeTicketId === row.ticket_id"
                  @click="handleResendAttendeeTicket(row.ticket_id)"
                >
                  {{ resendAttendeeTicketId === row.ticket_id ? "寄送中…" : "重寄票券" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="attendees.length === 0 && !loading" class="mt-3 text-sm text-slate-500">此活動尚無報名名單，或載入後無資料。</p>
    </section>
  </main>
</template>
