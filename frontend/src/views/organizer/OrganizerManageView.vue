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

/** CSV 安全：含逗號、換行、雙引號時包雙引號並跳脫。MVP-2.5 名單匯出。 */
function csvEscape(val: unknown): string {
  const s = val == null ? "" : String(val);
  if (s.includes(",") || s.includes('"') || s.includes("\n") || s.includes("\r")) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function exportAttendeesCsv(): void {
  if (attendees.value.length === 0) return;
  const answerKeys = new Set<string>();
  for (const r of attendees.value) {
    if (r.answers && typeof r.answers === "object") {
      Object.keys(r.answers).forEach((k) => answerKeys.add(k));
    }
  }
  const baseCols = ["ticket_id", "user_id", "ticket_type_id", "status", "checked_in_at"];
  const ansCols = [...answerKeys].sort();
  const headers = [...baseCols, ...ansCols];
  const rows: string[][] = [headers];
  for (const r of attendees.value) {
    const ans = r.answers && typeof r.answers === "object" ? r.answers : {};
    const line = [
      csvEscape(r.ticket_id),
      csvEscape(r.user_id),
      csvEscape(r.ticket_type_id),
      csvEscape(r.status),
      csvEscape(r.checked_in_at ?? ""),
      ...ansCols.map((k) => csvEscape(ans[k])),
    ];
    rows.push(line);
  }
  const csvContent = rows.map((row) => row.join(",")).join("\n");
  const bom = "\uFEFF";
  const blob = new Blob([bom + csvContent], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const eventTitle = myEvents.value.find((e) => e.id === eventId.value)?.title ?? "名單";
  a.download = `${eventTitle.replace(/[^a-zA-Z0-9\u4e00-\u9fff-]/g, "_")}_名單_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
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
    <div class="mb-6 animate-fade-in">
      <router-link to="/organizer" class="link-back">← 回主辦方管理中心</router-link>
    </div>

    <h1 class="font-street text-3xl tracking-widest text-white animate-slide-up">主辦方管理</h1>
    <p class="mt-2 text-cypher-muted animate-slide-up-delay">選擇活動後可查核銷統計與代參加者重寄票券。</p>

    <!-- 選擇活動 -->
    <section class="card mt-6 p-6 animate-slide-up-delay-2">
      <h2 class="font-street text-lg tracking-wider text-white">選擇活動</h2>
      <div class="mt-3 flex flex-wrap items-center gap-3">
        <select
          v-model="eventId"
          class="input-field min-w-[280px]"
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
          class="btn-primary disabled:opacity-50"
          :disabled="loading || !eventId"
          @click="loadByEventId"
        >
          {{ loading ? "載入中…" : "載入" }}
        </button>
      </div>
      <p v-if="summaryLoading" class="mt-2 text-sm text-cypher-muted">載入活動列表中…</p>
      <p v-else-if="myEvents.length === 0" class="mt-2 text-sm text-cypher-muted">尚無活動，請先建立活動。</p>
      <p v-if="loadError" class="mt-2 text-sm text-rose-600">{{ loadError }}</p>
    </section>

    <!-- 核銷統計 -->
    <section v-if="eventId.trim() && (stats || loading)" class="card mt-6 p-6">
      <h2 class="font-street text-lg tracking-wider text-white">核銷統計</h2>
      <p v-if="loading" class="mt-2 text-sm text-cypher-muted">載入中…</p>
      <div v-else-if="stats" class="mt-3">
        <p class="text-base font-medium text-gray-300">
          已入場 <span class="text-cypher-accent">{{ stats.checkedIn }}</span> / 未入場
          <span class="text-cypher-muted">{{ stats.notCheckedIn }}</span>
          <span class="ml-2 text-sm text-cypher-muted">（總計 {{ stats.total }} 張有效票）</span>
        </p>
        <div v-if="stats.byTicketType.length" class="mt-3 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="border-b border-cypher-border text-left text-cypher-muted">
              <tr>
                <th class="pb-2 pr-4">票種 ID</th>
                <th class="pb-2 pr-4">已入場</th>
                <th class="pb-2">總數</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in stats.byTicketType" :key="row.ticket_type_id" class="border-b border-cypher-border">
                <td class="py-1.5 pr-4 font-mono text-xs">{{ row.ticket_type_id }}</td>
                <td class="py-1.5 pr-4">{{ row.checkedIn }}</td>
                <td class="py-1.5">{{ row.total }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <button
          type="button"
          class="mt-3 rounded-lg border border-cypher-border px-3 py-1.5 text-sm text-gray-300 hover:bg-cypher-surface-alt"
          :disabled="loading"
          @click="loadByEventId"
        >
          重新載入統計
        </button>
      </div>
    </section>

    <!-- 代寄票券（名單與重寄） -->
    <section v-if="eventId.trim() && stats !== null" class="card mt-6 p-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="font-street text-lg tracking-wider text-white">名單與代寄票券</h2>
          <p class="mt-1 text-sm text-cypher-muted">可對單張票券觸發「重寄票券信」至參加者信箱；可匯出 CSV。</p>
        </div>
        <button
          type="button"
          class="rounded-lg border border-cypher-border px-3 py-1.5 text-sm text-gray-300 transition-colors hover:bg-cypher-surface-alt disabled:opacity-50"
          :disabled="attendees.length === 0"
          @click="exportAttendeesCsv"
        >
          匯出 CSV
        </button>
      </div>
      <p v-if="resendAttendeeMessage" class="mt-2 text-sm" :class="resendAttendeeMessage.startsWith('已') ? 'text-emerald-600' : 'text-rose-600'">
        {{ resendAttendeeMessage }}
      </p>
      <div class="mt-4 overflow-auto rounded-xl border border-cypher-border">
        <table class="min-w-full text-sm">
          <thead class="bg-cypher-surface-alt text-left text-cypher-muted">
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
            <tr v-for="row in attendees" :key="row.ticket_id" class="border-t border-cypher-border align-top text-gray-300">
              <td class="px-3 py-2 font-mono text-xs">{{ row.ticket_id }}</td>
              <td class="px-3 py-2 font-mono text-xs">{{ row.user_id }}</td>
              <td class="px-3 py-2">{{ row.status }}</td>
              <td class="px-3 py-2">{{ row.checked_in_at || "—" }}</td>
              <td class="px-3 py-2">
                <pre class="whitespace-pre-wrap break-all text-xs text-cypher-muted">{{ formatAnswers(row.answers) }}</pre>
              </td>
              <td class="px-3 py-2">
                <button
                  v-if="row.status !== 'cancelled'"
                  type="button"
                  class="rounded-lg border border-cypher-accent/50 px-2 py-1 text-xs font-medium text-cypher-accent transition-colors hover:bg-cypher-accent/20 disabled:opacity-50"
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
      <p v-if="attendees.length === 0 && !loading" class="mt-3 text-sm text-cypher-muted">此活動尚無報名名單，或載入後無資料。</p>
    </section>
  </main>
</template>
