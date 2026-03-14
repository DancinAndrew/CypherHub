<script setup lang="ts">
import { BrowserQRCodeReader } from "@zxing/browser";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { organizerCommitCheckin, organizerVerifyCheckin } from "../../api/client";
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

onBeforeUnmount(() => {
  stopScan().catch(() => {});
});

watch(mode, (nextMode) => {
  if (nextMode === "manual" && scanning.value) {
    stopScan().catch(() => {});
  }
});
</script>

<template>
  <main class="mx-auto w-full max-w-3xl px-4 py-8 md:py-10">
    <h1 class="text-3xl font-bold text-slate-900">Organizer Check-in</h1>
    <p class="mt-2 text-sm text-slate-600">
      手機可直接用相機掃碼核銷；若權限受限可切手動模式。
    </p>

    <section class="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm md:p-6">
      <label class="block">
        <span class="mb-1 block text-sm text-slate-700">Event ID</span>
        <input
          v-model="eventId"
          class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
      </label>

      <div class="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          class="rounded-lg px-3 py-2 text-sm font-semibold"
          :class="mode === 'scan' ? 'bg-brand-600 text-white' : 'border border-slate-300 text-slate-700 hover:bg-slate-50'"
          @click="mode = 'scan'"
        >
          掃碼模式
        </button>
        <button
          type="button"
          class="rounded-lg px-3 py-2 text-sm font-semibold"
          :class="mode === 'manual' ? 'bg-brand-600 text-white' : 'border border-slate-300 text-slate-700 hover:bg-slate-50'"
          @click="mode = 'manual'"
        >
          手動模式
        </button>
      </div>

      <div v-if="mode === 'scan'" class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p class="text-xs text-slate-600">Start Scan 後請允許相機權限，掃到後會自動填入並執行 Verify。</p>
        <div class="mt-3 overflow-hidden rounded-lg border border-slate-200 bg-black">
          <video ref="scannerVideoRef" class="h-64 w-full object-cover md:h-72" muted playsinline />
        </div>
        <div class="mt-3 flex flex-wrap gap-3">
          <button
            type="button"
            class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            :disabled="scanning || loading"
            @click="startScan"
          >
            Start Scan
          </button>
          <button
            type="button"
            class="rounded-lg border border-brand-600 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"
            :disabled="!scanning"
            @click="stopScan"
          >
            Stop Scan
          </button>
        </div>
      </div>

      <div class="mt-4 grid gap-4">
        <label class="block">
          <span class="mb-1 block text-sm text-slate-700">Ticket ID</span>
          <input
            v-model="ticketId"
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </label>

        <label class="block">
          <span class="mb-1 block text-sm text-slate-700">QR Secret</span>
          <input
            v-model="qrSecret"
            placeholder="ticket qr_secret"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </label>
      </div>

      <div class="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          :disabled="loading"
          @click="verify"
        >
          Verify
        </button>
        <button
          type="button"
          class="rounded-lg border border-brand-600 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"
          :disabled="!canCommit"
          @click="commit"
        >
          Commit Check-in
        </button>
      </div>

      <p v-if="infoMessage" class="mt-4 text-sm text-emerald-700">{{ infoMessage }}</p>
      <p v-if="errorMessage" class="mt-2 text-sm text-rose-700">{{ errorMessage }}</p>

      <div v-if="verifySummary" class="mt-4 rounded-lg bg-slate-50 p-4">
        <p class="text-xs font-semibold text-slate-600">Verify Summary</p>
        <div class="mt-2 grid gap-1 text-sm text-slate-700">
          <p>valid: {{ verifySummary.valid }}</p>
          <p>can_checkin: {{ verifySummary.can_checkin }}</p>
          <p>status: {{ verifySummary.status ?? "-" }}</p>
          <p>user_id: {{ verifySummary.user_id ?? "-" }}</p>
          <p>ticket_type_id: {{ verifySummary.ticket_type_id ?? "-" }}</p>
          <p v-if="verifySummary.reason">reason: {{ verifySummary.reason }}</p>
        </div>
      </div>

      <div v-if="commitResult" class="mt-4 rounded-lg bg-slate-50 p-4">
        <p class="text-xs font-semibold text-slate-600">Commit Result</p>
        <pre class="mt-2 overflow-x-auto text-xs text-slate-700">{{ JSON.stringify(commitResult, null, 2) }}</pre>
      </div>
    </section>
  </main>
</template>
