<script setup lang="ts">
import { BrowserQRCodeReader } from "@zxing/browser";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { organizerCommitCheckin, organizerFetchAttendees, organizerVerifyCheckin } from "../../api/client";
import { toApiErrorMessage } from "../../utils/errorMessages";

type QrParsedPayload = {
  ticket_id: string;
  qr_secret: string;
};

const route = useRoute();
const eventId = ref<string>(typeof route.params.eventId === "string" ? route.params.eventId : "");
const ticketId = ref("");
const qrSecret = ref("");
const mode = ref<"scan" | "manual">("scan");

const attendeesStats = ref<{
  total: number;
  checkedIn: number;
  notCheckedIn: number;
  byTicketType: Array<{ ticket_type_id: string; ticket_type_name: string; total: number; checkedIn: number }>;
} | null>(null);
const attendeesStatsLoading = ref(false);
const attendeesStatsError = ref<string | null>(null);

const verifyResult = ref<Record<string, unknown> | null>(null);
const commitResult = ref<Record<string, unknown> | null>(null);
const errorMessage = ref<string | null>(null);
const infoMessage = ref<string | null>(null);
const loading = ref(false);

const scannerVideoRef = ref<HTMLVideoElement | null>(null);
const scannerReader = new BrowserQRCodeReader();
const scannerControls = ref<{ stop: () => void } | null>(null);
const scanning = ref(false);
const scanLocked = ref(false);

const requestPayload = computed(() => ({
  ticket_id: ticketId.value.trim(),
  qr_secret: qrSecret.value.trim(),
}));

const canCommit = computed(() => {
  const valid = verifyResult.value?.valid === true;
  const canCheckin = verifyResult.value?.can_checkin === true;
  return Boolean(eventId.value && requestPayload.value.ticket_id && requestPayload.value.qr_secret && valid && canCheckin && !loading.value);
});

const verifySummary = computed(() => {
  if (!verifyResult.value) {
    return null;
  }
  return {
    valid: verifyResult.value.valid,
    can_checkin: verifyResult.value.can_checkin,
    status: verifyResult.value.status,
    user_id: verifyResult.value.user_id,
    ticket_type_id: verifyResult.value.ticket_type_id,
    reason: verifyResult.value.reason,
  };
});

function normalizeUuid(value: string): string {
  return value.trim().toLowerCase();
}

function parseQueryLike(raw: string): QrParsedPayload | null {
  const query = raw.includes("?") ? raw.slice(raw.indexOf("?") + 1) : raw;
  const params = new URLSearchParams(query);
  const ticket = params.get("ticket_id");
  const secret = params.get("qr_secret");
  if (!ticket || !secret) {
    return null;
  }
  return {
    ticket_id: ticket,
    qr_secret: secret,
  };
}

function parseQrPayload(raw: string): QrParsedPayload | null {
  const input = raw.trim();
  if (!input) {
    return null;
  }

  try {
    const parsed = JSON.parse(input) as { ticket_id?: unknown; qr_secret?: unknown };
    if (typeof parsed.ticket_id === "string" && typeof parsed.qr_secret === "string") {
      return {
        ticket_id: parsed.ticket_id,
        qr_secret: parsed.qr_secret,
      };
    }
  } catch {
    // Not JSON. Continue parsing other supported formats.
  }

  if (input.includes("ticket_id=") && input.includes("qr_secret=")) {
    return parseQueryLike(input);
  }

  if (input.includes("|")) {
    const [ticket, secret] = input.split("|", 2);
    if (ticket?.trim() && secret?.trim()) {
      return {
        ticket_id: ticket.trim(),
        qr_secret: secret.trim(),
      };
    }
  }

  return null;
}

function mapVerifyReason(result: Record<string, unknown>): string | null {
  const reason = String(result.reason ?? "");
  if (!reason) {
    return null;
  }
  if (reason === "AUTH_REQUIRED") {
    return "尚未登入或 token 已失效，請重新登入。";
  }
  if (reason === "FORBIDDEN") {
    return "你不是這個活動的 organizer member，無法核銷。";
  }
  if (reason === "QR_MISMATCH") {
    return "QR 不匹配，請確認票券內容。";
  }
  if (reason === "TICKET_NOT_FOUND") {
    return "找不到此票券。";
  }
  return `核銷驗證失敗：${reason}`;
}

function mapCommitReason(result: Record<string, unknown>): string | null {
  const reason = String(result.reason ?? "");
  if (!reason) {
    return null;
  }
  if (reason === "AUTH_REQUIRED") {
    return "尚未登入或 token 已失效，請重新登入。";
  }
  if (reason === "FORBIDDEN") {
    return "你不是這個活動的 organizer member，無法核銷。";
  }
  if (reason === "QR_MISMATCH") {
    return "QR 不匹配，請確認票券內容。";
  }
  if (reason === "TICKET_NOT_FOUND") {
    return "找不到此票券。";
  }
  if (reason === "INVALID_STATUS") {
    return `票券狀態無法核銷（status=${result.status ?? "unknown"}）。`;
  }
  return `核銷失敗：${reason}`;
}

function resetNotices(): void {
  errorMessage.value = null;
  infoMessage.value = null;
}

async function verify(): Promise<void> {
  resetNotices();
  commitResult.value = null;

  if (!eventId.value.trim()) {
    errorMessage.value = "event_id 為必填。";
    return;
  }
  if (!requestPayload.value.ticket_id || !requestPayload.value.qr_secret) {
    errorMessage.value = "請提供 ticket_id 與 qr_secret。";
    return;
  }

  loading.value = true;
  verifyResult.value = null;

  try {
    const result = await organizerVerifyCheckin(eventId.value.trim(), requestPayload.value);
    verifyResult.value = result;

    if (result.valid === true) {
      infoMessage.value = "票券驗證成功。";
    } else {
      errorMessage.value = mapVerifyReason(result) ?? "票券驗證失敗。";
    }
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Verify failed");
  } finally {
    loading.value = false;
  }
}

async function commit(): Promise<void> {
  resetNotices();

  if (!canCommit.value) {
    errorMessage.value = "請先完成 Verify，且 can_checkin=true 後才能 Commit。";
    return;
  }

  loading.value = true;
  commitResult.value = null;

  try {
    const result = await organizerCommitCheckin(eventId.value.trim(), requestPayload.value);
    commitResult.value = result;

    if (result.ok === true) {
      if (result.already_checked_in === true) {
        infoMessage.value = "已重複核銷（idempotent）：票券先前已核銷。";
      } else {
        infoMessage.value = "核銷成功。";
      }
      loadAttendeesStats().catch(() => {});
    } else {
      errorMessage.value = mapCommitReason(result) ?? "Commit failed";
    }
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Commit failed");
  } finally {
    loading.value = false;
  }
}

async function stopScan(): Promise<void> {
  scanning.value = false;
  scanLocked.value = false;

  if (scannerControls.value) {
    scannerControls.value.stop();
    scannerControls.value = null;
  }
}

async function handleScanText(rawText: string): Promise<void> {
  if (scanLocked.value) {
    return;
  }
  scanLocked.value = true;

  try {
    const parsed = parseQrPayload(rawText);
    if (!parsed) {
      errorMessage.value = "QR 格式不支援，請改手動輸入。";
      mode.value = "manual";
      await stopScan();
      return;
    }

    ticketId.value = normalizeUuid(parsed.ticket_id);
    qrSecret.value = parsed.qr_secret.trim();
    infoMessage.value = "掃碼成功，已自動填入 ticket_id / qr_secret。";
    mode.value = "manual";
    await stopScan();
    await verify();
  } finally {
    scanLocked.value = false;
  }
}

async function startScan(): Promise<void> {
  resetNotices();
  verifyResult.value = null;
  commitResult.value = null;

  if (!eventId.value.trim()) {
    errorMessage.value = "請先確認 event_id。";
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    errorMessage.value = "此瀏覽器不支援相機掃碼，請改手動輸入。";
    return;
  }

  const videoEl = scannerVideoRef.value;
  if (!videoEl) {
    errorMessage.value = "掃碼元件初始化失敗，請重整頁面後再試。";
    return;
  }

  try {
    mode.value = "scan";
    scanning.value = true;
    scannerControls.value = await scannerReader.decodeFromVideoDevice(undefined, videoEl, (result, error) => {
      if (result) {
        handleScanText(result.getText()).catch(() => {
          errorMessage.value = "掃碼處理失敗，請改手動輸入。";
        });
      }

      // Ignore frequent no-result signal (no log per frontend DoD).
      if (error && error.name !== "NotFoundException") {
        // scanner library noise; user sees live feed
      }
    });
    infoMessage.value = "相機已啟動，請將票券 QR 置中。";
  } catch (error: unknown) {
    const message = String((error as { message?: string })?.message || "").toLowerCase();
    if (message.includes("permission") || message.includes("notallowederror")) {
      errorMessage.value = "相機權限被拒絕，請允許相機或改用手動輸入。";
    } else if (message.includes("notfounderror")) {
      errorMessage.value = "找不到可用相機裝置，請改用手動輸入。";
    } else {
      errorMessage.value = "無法啟動相機掃碼，請改用手動輸入。";
    }
    await stopScan();
  }
}

async function loadAttendeesStats(): Promise<void> {
  const eid = eventId.value.trim();
  if (!eid) {
    attendeesStats.value = null;
    return;
  }
  attendeesStatsLoading.value = true;
  attendeesStatsError.value = null;
  try {
    const items = await organizerFetchAttendees(eid);
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
    attendeesStats.value = {
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
    attendeesStatsError.value = toApiErrorMessage(error, "載入統計失敗");
    attendeesStats.value = null;
  } finally {
    attendeesStatsLoading.value = false;
  }
}

onMounted(() => {
  if (eventId.value.trim()) loadAttendeesStats().catch(() => {});
});

onBeforeUnmount(() => {
  stopScan().catch(() => {});
});

watch(
  () => route.params.eventId,
  (val) => {
    const next = typeof val === "string" ? val : "";
    if (eventId.value !== next) eventId.value = next;
    if (next.trim()) loadAttendeesStats().catch(() => {});
  },
  { immediate: true },
);

watch(mode, (nextMode) => {
  if (nextMode === "manual" && scanning.value) {
    stopScan().catch(() => {});
  }
});
</script>

<template>
  <main class="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden px-4 pb-20 pt-10">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="pointer-events-none absolute inset-0" style="background: radial-gradient(ellipse 60% 40% at 50% 0%, rgba(34,211,238,0.08) 0%, transparent 70%)" aria-hidden="true" />

    <div class="relative z-10 mx-auto w-full max-w-xl">

      <!-- Page header -->
      <header class="mb-8 animate-slide-up">
        <p class="section-label mb-2">Check-in</p>
        <div class="flex items-center gap-3">
          <span class="h-6 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent-cyan to-cypher-accent" aria-hidden="true" />
          <h1 class="font-street text-2xl tracking-widest text-white">核銷介面</h1>
        </div>
        <p class="mt-2 pl-3.5 text-sm text-cypher-muted">手機可直接掃碼核銷；若相機受限可切手動輸入。</p>
      </header>

      <!-- Stats card (only when eventId is set) -->
      <section
        v-if="eventId.trim()"
        class="relative mb-5 overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md animate-slide-up-delay"
      >
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-cyan/50 to-transparent" aria-hidden="true" />
        <div class="flex items-center justify-between border-b border-white/5 px-5 py-3.5">
          <h2 class="text-sm font-semibold text-white">即時核銷統計</h2>
          <button
            type="button"
            class="flex items-center gap-1 text-xs text-cypher-muted transition-colors hover:text-cypher-accent"
            :disabled="attendeesStatsLoading"
            @click="loadAttendeesStats()"
          >
            <svg class="h-3.5 w-3.5" :class="{ 'animate-spin': attendeesStatsLoading }" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            重新整理
          </button>
        </div>
        <div class="p-5">
          <p v-if="attendeesStatsLoading" class="flex items-center gap-2 text-sm text-cypher-muted">
            <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cypher-muted border-t-transparent" />
            載入中…
          </p>
          <p v-else-if="attendeesStatsError" class="text-sm text-rose-400">{{ attendeesStatsError }}</p>
          <div v-else-if="attendeesStats">
            <div class="flex gap-3">
              <div class="flex-1 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-center">
                <p class="text-xs text-cypher-muted">已入場</p>
                <p class="mt-0.5 text-2xl font-bold text-emerald-400">{{ attendeesStats.checkedIn }}</p>
              </div>
              <div class="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-center">
                <p class="text-xs text-cypher-muted">未入場</p>
                <p class="mt-0.5 text-2xl font-bold text-gray-300">{{ attendeesStats.notCheckedIn }}</p>
              </div>
              <div class="flex-1 rounded-xl border border-cypher-accent/20 bg-cypher-accent/10 px-4 py-3 text-center">
                <p class="text-xs text-cypher-muted">總計</p>
                <p class="mt-0.5 text-2xl font-bold text-cypher-accent-bright">{{ attendeesStats.total }}</p>
              </div>
            </div>
            <div v-if="attendeesStats.byTicketType.length" class="mt-4 overflow-x-auto rounded-xl border border-white/5">
              <table class="min-w-full text-sm">
                <thead class="border-b border-white/5 bg-cypher-surface-alt text-left">
                  <tr>
                    <th class="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-cypher-muted">票種</th>
                    <th class="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-cypher-muted">入場</th>
                    <th class="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-cypher-muted">總數</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-white/5">
                  <tr v-for="row in attendeesStats.byTicketType" :key="row.ticket_type_id">
                    <td class="px-4 py-2 text-gray-200">{{ row.ticket_type_name }}</td>
                    <td class="px-4 py-2 font-semibold text-emerald-400">{{ row.checkedIn }}</td>
                    <td class="px-4 py-2 text-gray-300">{{ row.total }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- Main checkin panel -->
      <section
        class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md animate-slide-up-delay-2"
      >
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/50 to-transparent" aria-hidden="true" />
        <div class="p-5 md:p-6 space-y-5">

          <!-- Event ID -->
          <div>
            <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">Event ID</label>
            <input v-model="eventId" class="input-field font-mono text-sm" placeholder="活動 UUID" />
          </div>

          <!-- Mode toggle -->
          <div class="flex rounded-xl border border-cypher-border bg-cypher-bg/60 p-1">
            <button
              type="button"
              class="flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition-all duration-200"
              :class="mode === 'scan' ? 'bg-cypher-accent text-white shadow-glow-sm' : 'text-gray-400 hover:text-white'"
              @click="mode = 'scan'"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0113.5 9.375v-4.5z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 6.75h.75v.75h-.75v-.75zM6.75 16.5h.75v.75h-.75V16.5zM16.5 6.75h.75v.75h-.75v-.75zM13.5 13.5h.75v.75h-.75v-.75zM13.5 19.5h.75v.75h-.75v-.75zM19.5 13.5h.75v.75h-.75v-.75zM19.5 19.5h.75v.75h-.75v-.75zM16.5 16.5h.75v.75h-.75v-.75z" />
              </svg>
              掃碼模式
            </button>
            <button
              type="button"
              class="flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition-all duration-200"
              :class="mode === 'manual' ? 'bg-cypher-accent text-white shadow-glow-sm' : 'text-gray-400 hover:text-white'"
              @click="mode = 'manual'"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
              </svg>
              手動輸入
            </button>
          </div>

          <!-- Camera viewfinder (scan mode) -->
          <div v-if="mode === 'scan'" class="space-y-3">
            <p class="text-xs text-cypher-muted">允許相機後將票券 QR 置中，掃到後自動 Verify。</p>
            <div class="relative overflow-hidden rounded-2xl border border-white/10 bg-black">
              <!-- Corner guides -->
              <div class="pointer-events-none absolute inset-0 z-10" aria-hidden="true">
                <div class="absolute left-4 top-4 h-8 w-8 rounded-tl-lg border-l-2 border-t-2 border-cypher-accent-cyan opacity-80" />
                <div class="absolute right-4 top-4 h-8 w-8 rounded-tr-lg border-r-2 border-t-2 border-cypher-accent-cyan opacity-80" />
                <div class="absolute bottom-4 left-4 h-8 w-8 rounded-bl-lg border-b-2 border-l-2 border-cypher-accent-cyan opacity-80" />
                <div class="absolute bottom-4 right-4 h-8 w-8 rounded-br-lg border-b-2 border-r-2 border-cypher-accent-cyan opacity-80" />
              </div>
              <video ref="scannerVideoRef" class="h-64 w-full object-cover md:h-72" muted playsinline />
              <div v-if="!scanning" class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/60">
                <svg class="h-10 w-10 text-cypher-muted" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z" />
                </svg>
                <p class="text-sm text-cypher-muted">按下「啟動相機」開始掃碼</p>
              </div>
            </div>
            <div class="flex gap-3">
              <button
                type="button"
                class="btn-primary flex-1 disabled:opacity-50"
                :disabled="scanning || loading"
                @click="startScan"
              >
                <span v-if="scanning" class="flex items-center justify-center gap-2">
                  <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  掃碼中…
                </span>
                <span v-else>啟動相機</span>
              </button>
              <button
                type="button"
                class="rounded-xl border border-cypher-border bg-cypher-surface px-5 py-2.5 text-sm font-medium text-gray-400 transition-colors hover:border-rose-500/40 hover:text-rose-400 disabled:opacity-50"
                :disabled="!scanning"
                @click="stopScan"
              >
                停止
              </button>
            </div>
          </div>

          <!-- Manual fields -->
          <div class="space-y-4">
            <div>
              <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">Ticket ID</label>
              <input v-model="ticketId" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" class="input-field font-mono text-sm" />
            </div>
            <div>
              <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">QR Secret</label>
              <input v-model="qrSecret" placeholder="ticket qr_secret" class="input-field font-mono text-sm" />
            </div>
          </div>

          <!-- Action buttons -->
          <div class="flex gap-3">
            <button
              type="button"
              class="flex-1 rounded-xl border border-cypher-accent/40 bg-cypher-accent/10 py-3 text-sm font-semibold text-cypher-accent-bright transition-all hover:bg-cypher-accent/20 disabled:opacity-50"
              :disabled="loading"
              @click="verify"
            >
              <span v-if="loading && !canCommit" class="flex items-center justify-center gap-2">
                <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" />
                驗證中…
              </span>
              <span v-else>Verify</span>
            </button>
            <button
              type="button"
              class="flex-1 rounded-xl py-3 text-sm font-bold transition-all disabled:opacity-40"
              :class="canCommit
                ? 'bg-emerald-500 text-white shadow-[0_0_20px_rgba(52,211,153,0.4)] hover:bg-emerald-400'
                : 'border border-white/10 bg-white/5 text-gray-500 cursor-not-allowed'"
              :disabled="!canCommit"
              @click="commit"
            >
              <span v-if="loading && canCommit" class="flex items-center justify-center gap-2">
                <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                核銷中…
              </span>
              <span v-else>Commit 核銷</span>
            </button>
          </div>

          <!-- Status feedback -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 scale-95"
            enter-to-class="opacity-100 scale-100"
          >
            <div v-if="infoMessage" role="status" class="flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
              <svg class="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p class="text-sm font-medium text-emerald-300">{{ infoMessage }}</p>
            </div>
          </Transition>

          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 scale-95"
            enter-to-class="opacity-100 scale-100"
          >
            <div v-if="errorMessage" role="alert" class="flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3">
              <svg class="mt-0.5 h-4 w-4 shrink-0 text-rose-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              <p class="text-sm font-medium text-rose-300">{{ errorMessage }}</p>
            </div>
          </Transition>

          <!-- Verify summary -->
          <div v-if="verifySummary" class="rounded-xl border border-white/5 bg-cypher-surface-alt px-4 py-3">
            <p class="mb-2 text-xs font-semibold uppercase tracking-wider text-cypher-muted">Verify Result</p>
            <dl class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
              <div class="flex items-center gap-1.5">
                <dt class="text-cypher-muted">valid</dt>
                <dd>
                  <span
                    class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold"
                    :class="verifySummary.valid ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'"
                  >
                    {{ verifySummary.valid ? 'true' : 'false' }}
                  </span>
                </dd>
              </div>
              <div class="flex items-center gap-1.5">
                <dt class="text-cypher-muted">can_checkin</dt>
                <dd>
                  <span
                    class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold"
                    :class="verifySummary.can_checkin ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'"
                  >
                    {{ verifySummary.can_checkin ? 'true' : 'false' }}
                  </span>
                </dd>
              </div>
              <div class="flex items-center gap-1.5">
                <dt class="text-cypher-muted">status</dt>
                <dd class="font-mono text-gray-300">{{ verifySummary.status ?? "—" }}</dd>
              </div>
              <div class="flex items-center gap-1.5 col-span-2">
                <dt class="shrink-0 text-cypher-muted">user_id</dt>
                <dd class="truncate font-mono text-gray-300">{{ verifySummary.user_id ?? "—" }}</dd>
              </div>
              <div v-if="verifySummary.reason" class="col-span-2 flex items-center gap-1.5">
                <dt class="shrink-0 text-cypher-muted">reason</dt>
                <dd class="font-mono text-rose-400">{{ verifySummary.reason }}</dd>
              </div>
            </dl>
          </div>

          <!-- Commit result -->
          <div v-if="commitResult" class="rounded-xl border border-white/5 bg-cypher-surface-alt px-4 py-3">
            <p class="mb-2 text-xs font-semibold uppercase tracking-wider text-cypher-muted">Commit Result</p>
            <pre class="overflow-x-auto font-mono text-xs text-gray-300">{{ JSON.stringify(commitResult, null, 2) }}</pre>
          </div>

        </div>
      </section>

    </div>
  </main>
</template>
