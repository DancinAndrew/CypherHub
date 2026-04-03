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
  byTicketType: Array<{ ticket_type_id: string; ticket_type_name: string; total: number; checkedIn: number }>;
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
  const baseCols = [
    "ticket_id",
    "user_id",
    "user_display_name",
    "ticket_type_id",
    "ticket_type_name",
    "status",
    "checked_in_at",
  ];
  const ansCols = [...answerKeys].sort();
  const headers = [...baseCols, ...ansCols];
  const rows: string[][] = [headers];
  for (const r of attendees.value) {
    const ans = r.answers && typeof r.answers === "object" ? r.answers : {};
    const line = [
      csvEscape(r.ticket_id),
      csvEscape(r.user_id),
      csvEscape(r.user_display_name ?? ""),
      csvEscape(r.ticket_type_id),
      csvEscape(r.ticket_type_name ?? ""),
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
    const byType: Record<string, { total: number; checkedIn: number; name: string }> = {};
    for (const r of active) {
      const tt = r.ticket_type_id ?? "unknown";
      const nm = (r.ticket_type_name || "").trim() || "（未知票種）";
      if (!byType[tt]) {
        byType[tt] = { total: 0, checkedIn: 0, name: nm };
      }
      byType[tt].total += 1;
      if (r.status === "checked_in") byType[tt].checkedIn += 1;
    }
    stats.value = {
      total: active.length,
      checkedIn,
      notCheckedIn,
      byTicketType: Object.entries(byType).map(([ticket_type_id, v]) => ({
        ticket_type_id,
        ticket_type_name: v.name,
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
  <main class="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden px-4 pb-20 pt-10">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="pointer-events-none absolute inset-0" style="background: radial-gradient(ellipse 50% 40% at 50% 0%, rgba(124,58,237,0.10) 0%, transparent 70%)" aria-hidden="true" />

    <div class="relative z-10 mx-auto w-full max-w-4xl">

      <!-- Back link -->
      <div class="mb-8 animate-fade-in">
        <router-link
          to="/organizer"
          class="inline-flex items-center gap-1.5 text-sm text-cypher-muted transition-colors hover:text-cypher-accent"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          回主辦方管理中心
        </router-link>
      </div>

      <!-- Page header -->
      <div class="mb-8 animate-slide-up">
        <p class="section-label mb-2">Manage</p>
        <div class="flex items-center gap-3">
          <span class="h-6 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
          <h1 class="font-street text-2xl tracking-widest text-white">主辦方管理</h1>
        </div>
        <p class="mt-2 pl-3.5 text-sm text-cypher-muted">選擇活動後可查核銷統計與代參加者重寄票券。</p>
      </div>

      <!-- 選擇活動 -->
      <section
        class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md animate-slide-up-delay"
      >
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/50 to-transparent" aria-hidden="true" />
        <div class="border-b border-white/5 px-6 py-4">
          <h2 class="text-sm font-semibold text-white">選擇活動</h2>
        </div>
        <div class="p-6">
          <div class="flex flex-wrap items-center gap-3">
            <select
              v-model="eventId"
              class="input-field min-w-[280px] flex-1"
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
              <span v-if="loading" class="flex items-center gap-2">
                <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                載入中…
              </span>
              <span v-else>載入</span>
            </button>
          </div>
          <p v-if="summaryLoading" class="mt-3 flex items-center gap-2 text-sm text-cypher-muted">
            <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cypher-muted border-t-transparent" />
            載入活動列表中…
          </p>
          <p v-else-if="myEvents.length === 0" class="mt-3 text-sm text-cypher-muted">尚無活動，請先建立活動。</p>
          <div v-if="loadError" class="mt-3 flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3">
            <svg class="mt-0.5 h-4 w-4 shrink-0 text-rose-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <p class="text-sm text-rose-300">{{ loadError }}</p>
          </div>
        </div>
      </section>

      <!-- 核銷統計 -->
      <section
        v-if="eventId.trim() && (stats || loading)"
        class="relative mt-5 overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md"
      >
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-cyan/40 to-transparent" aria-hidden="true" />
        <div class="border-b border-white/5 px-6 py-4">
          <h2 class="text-sm font-semibold text-white">核銷統計</h2>
        </div>
        <div class="p-6">
          <p v-if="loading" class="flex items-center gap-2 text-sm text-cypher-muted">
            <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cypher-muted border-t-transparent" />
            載入中…
          </p>
          <div v-else-if="stats">
            <!-- Summary row -->
            <div class="flex flex-wrap gap-4">
              <div class="flex-1 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-5 py-3 text-center">
                <p class="text-xs text-cypher-muted">已入場</p>
                <p class="mt-1 text-2xl font-bold text-emerald-400">{{ stats.checkedIn }}</p>
              </div>
              <div class="flex-1 rounded-xl border border-white/10 bg-white/5 px-5 py-3 text-center">
                <p class="text-xs text-cypher-muted">未入場</p>
                <p class="mt-1 text-2xl font-bold text-gray-300">{{ stats.notCheckedIn }}</p>
              </div>
              <div class="flex-1 rounded-xl border border-cypher-accent/20 bg-cypher-accent/10 px-5 py-3 text-center">
                <p class="text-xs text-cypher-muted">有效票總計</p>
                <p class="mt-1 text-2xl font-bold text-cypher-accent-bright">{{ stats.total }}</p>
              </div>
            </div>

            <!-- Per-ticket-type breakdown -->
            <div v-if="stats.byTicketType.length" class="mt-5 overflow-x-auto rounded-xl border border-white/5">
              <table class="min-w-full text-sm">
                <thead class="border-b border-white/5 bg-cypher-surface-alt text-left">
                  <tr>
                    <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">票種</th>
                    <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">已入場</th>
                    <th class="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">總數</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-white/5">
                  <tr v-for="row in stats.byTicketType" :key="row.ticket_type_id">
                    <td class="px-4 py-2.5 text-gray-200">{{ row.ticket_type_name }}</td>
                    <td class="px-4 py-2.5 font-semibold text-emerald-400">{{ row.checkedIn }}</td>
                    <td class="px-4 py-2.5 text-gray-300">{{ row.total }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <button
              type="button"
              class="mt-4 flex items-center gap-1.5 rounded-xl border border-cypher-border px-3 py-1.5 text-sm text-gray-400 transition-colors hover:border-cypher-accent/40 hover:bg-cypher-surface-alt hover:text-white"
              :disabled="loading"
              @click="loadByEventId"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              重新載入統計
            </button>
          </div>
        </div>
      </section>

      <!-- 名單與代寄票券 -->
      <section
        v-if="eventId.trim() && stats !== null"
        class="relative mt-5 overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md"
      >
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-pink/40 to-transparent" aria-hidden="true" />
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 px-6 py-4">
          <div>
            <h2 class="text-sm font-semibold text-white">名單與代寄票券</h2>
            <p class="mt-0.5 text-xs text-cypher-muted">可對單張票券觸發「重寄票券信」至參加者信箱；可匯出 CSV。</p>
          </div>
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-xl border border-cypher-border px-3 py-1.5 text-sm text-gray-400 transition-colors hover:border-cypher-accent/40 hover:bg-cypher-surface-alt hover:text-white disabled:opacity-50"
            :disabled="attendees.length === 0"
            @click="exportAttendeesCsv"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            匯出 CSV
          </button>
        </div>

        <div class="p-6">
          <!-- Resend feedback -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
          >
            <div
              v-if="resendAttendeeMessage"
              class="mb-4 flex items-start gap-2 rounded-xl px-4 py-3 text-sm"
              :class="resendAttendeeMessage.startsWith('已')
                ? 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                : 'border border-rose-500/30 bg-rose-500/10 text-rose-400'"
            >
              {{ resendAttendeeMessage }}
            </div>
          </Transition>

          <!-- Attendees table -->
          <div class="overflow-x-auto rounded-xl border border-white/5">
            <table class="min-w-full text-sm">
              <thead class="border-b border-white/5 bg-cypher-surface-alt text-left">
                <tr>
                  <th class="px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">票種</th>
                  <th class="px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">報名者</th>
                  <th class="px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">票券 ID</th>
                  <th class="px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">狀態</th>
                  <th class="px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">核銷時間</th>
                  <th class="px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">報名答案</th>
                  <th class="px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-cypher-muted">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="row in attendees" :key="row.ticket_id" class="align-top transition-colors hover:bg-white/[0.02]">
                  <td class="px-3 py-2.5 text-gray-200">{{ row.ticket_type_name?.trim() || "—" }}</td>
                  <td class="px-3 py-2.5 text-gray-200" :title="row.user_id">
                    {{ row.user_display_name?.trim() || "—" }}
                  </td>
                  <td class="px-3 py-2.5 font-mono text-[11px] text-cypher-muted" :title="row.ticket_id">
                    {{ row.ticket_id.slice(0, 8) }}…
                  </td>
                  <td class="px-3 py-2.5">
                    <span
                      class="inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold"
                      :class="row.status === 'checked_in'
                        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                        : row.status === 'cancelled'
                          ? 'border-white/10 bg-white/5 text-gray-500'
                          : 'border-cypher-accent/30 bg-cypher-accent/10 text-cypher-accent-bright'"
                    >
                      {{ row.status }}
                    </span>
                  </td>
                  <td class="px-3 py-2.5 text-xs text-cypher-muted">{{ row.checked_in_at || "—" }}</td>
                  <td class="px-3 py-2.5">
                    <pre class="whitespace-pre-wrap break-all text-xs text-cypher-muted">{{ formatAnswers(row.answers) }}</pre>
                  </td>
                  <td class="px-3 py-2.5">
                    <button
                      v-if="row.status !== 'cancelled'"
                      type="button"
                      class="rounded-lg border border-cypher-accent/40 px-2.5 py-1 text-xs font-medium text-cypher-accent transition-colors hover:bg-cypher-accent/20 disabled:opacity-50"
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

          <p v-if="attendees.length === 0 && !loading" class="mt-4 text-center text-sm text-cypher-muted">
            此活動尚無報名名單，或載入後無資料。
          </p>
        </div>
      </section>

    </div>
  </main>
</template>
