<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import {
  organizerFetchProgress,
  organizerUpdateProgress,
  organizerFetchProgressLog,
  organizerReplaceStages,
  type EventProgress,
  type EventStage,
  type EventProgressLogEntry,
} from "../../api/client";
import { toApiErrorMessage } from "../../utils/errorMessages";

const route = useRoute();
const eventId = computed(() => String(route.params.eventId ?? ""));

const progress = ref<EventProgress | null>(null);
const stages = ref<EventStage[]>([]);
const log = ref<EventProgressLogEntry[]>([]);
const loading = ref(true);
const updating = ref(false);
const errorMsg = ref<string | null>(null);
const successMsg = ref<string | null>(null);
const noteInput = ref("");
const showStageEditor = ref(false);
const stageEditorText = ref("");
const savingStages = ref(false);

const sortedStages = computed(() => [...stages.value].sort((a, b) => a.sort_order - b.sort_order));

const currentIndex = computed(() => {
  if (!progress.value?.current_stage_id) return -1;
  return sortedStages.value.findIndex((s) => s.id === progress.value!.current_stage_id);
});

const BATTLE_TEMPLATE = [
  "報到",
  "海選",
  "海選結果公布",
  "Top 16",
  "Top 8",
  "Top 4 / 準決賽",
  "決賽",
  "頒獎",
  "活動結束",
];

async function fetchData() {
  loading.value = true;
  errorMsg.value = null;
  try {
    const res = await organizerFetchProgress(eventId.value);
    progress.value = res.progress;
    stages.value = res.stages;
    noteInput.value = progress.value?.note ?? "";
    const logRes = await organizerFetchProgressLog(eventId.value);
    log.value = logRes;
  } catch (err) {
    errorMsg.value = toApiErrorMessage(err, "操作失敗");
  } finally {
    loading.value = false;
  }
}

function flashSuccess(msg: string) {
  successMsg.value = msg;
  setTimeout(() => {
    successMsg.value = null;
  }, 3000);
}

async function setStatus(status: string) {
  updating.value = true;
  errorMsg.value = null;
  try {
    const res = await organizerUpdateProgress(eventId.value, { status });
    progress.value = res;
    flashSuccess(`狀態已更新為「${statusLabel(status)}」`);
    await refreshLog();
  } catch (err) {
    errorMsg.value = toApiErrorMessage(err, "操作失敗");
  } finally {
    updating.value = false;
  }
}

async function switchToStage(stageId: string) {
  updating.value = true;
  errorMsg.value = null;
  try {
    const res = await organizerUpdateProgress(eventId.value, { current_stage_id: stageId });
    progress.value = res;
    flashSuccess("已切換階段");
    await refreshLog();
  } catch (err) {
    errorMsg.value = toApiErrorMessage(err, "操作失敗");
  } finally {
    updating.value = false;
  }
}

async function updateNote() {
  updating.value = true;
  errorMsg.value = null;
  try {
    const res = await organizerUpdateProgress(eventId.value, { note: noteInput.value || null });
    progress.value = res;
    flashSuccess("備註已更新");
    await refreshLog();
  } catch (err) {
    errorMsg.value = toApiErrorMessage(err, "操作失敗");
  } finally {
    updating.value = false;
  }
}

async function refreshLog() {
  try {
    log.value = await organizerFetchProgressLog(eventId.value);
  } catch {
    // silent
  }
}

function statusLabel(s: string): string {
  const map: Record<string, string> = {
    not_started: "未開始",
    in_progress: "進行中",
    paused: "暫停",
    ended: "已結束",
  };
  return map[s] ?? s;
}

function stageState(idx: number): "completed" | "current" | "upcoming" {
  if (progress.value?.status === "ended") return "completed";
  if (currentIndex.value < 0) return "upcoming";
  if (idx < currentIndex.value) return "completed";
  if (idx === currentIndex.value) return "current";
  return "upcoming";
}

function formatTime(ts: string | null): string {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit" });
}

function formatDateTime(ts: string | null): string {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleString("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// --- Stage Editor ---

function openStageEditor() {
  if (stages.value.length > 0) {
    stageEditorText.value = sortedStages.value.map((s) => s.title).join("\n");
  } else {
    stageEditorText.value = BATTLE_TEMPLATE.join("\n");
  }
  showStageEditor.value = true;
}

function loadTemplate() {
  stageEditorText.value = BATTLE_TEMPLATE.join("\n");
}

async function saveStages() {
  const lines = stageEditorText.value
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  if (lines.length === 0) {
    errorMsg.value = "至少需要一個階段";
    return;
  }
  savingStages.value = true;
  errorMsg.value = null;
  try {
    const stagePayload = lines.map((title, idx) => ({
      title,
      sort_order: idx,
    }));
    stages.value = await organizerReplaceStages(eventId.value, stagePayload);
    showStageEditor.value = false;
    flashSuccess("階段已儲存");
    // Refresh progress (stage IDs may have changed)
    const res = await organizerFetchProgress(eventId.value);
    progress.value = res.progress;
  } catch (err) {
    errorMsg.value = toApiErrorMessage(err, "操作失敗");
  } finally {
    savingStages.value = false;
  }
}

onMounted(fetchData);
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-8">
    <h1 class="font-street text-3xl tracking-wider text-white">活動進度控制台</h1>

    <!-- Loading -->
    <div v-if="loading" class="mt-8 text-center text-cypher-muted">載入中...</div>

    <template v-else>
      <!-- Error / Success -->
      <div v-if="errorMsg" class="mt-4 rounded-lg bg-red-500/20 p-3 text-sm text-red-300">
        {{ errorMsg }}
      </div>
      <div
        v-if="successMsg"
        class="mt-4 rounded-lg bg-green-500/20 p-3 text-sm text-green-300 transition-opacity"
      >
        {{ successMsg }}
      </div>

      <!-- No stages yet -->
      <div v-if="stages.length === 0" class="mt-8">
        <div class="card p-6 text-center">
          <p class="text-cypher-muted">尚未設定活動階段</p>
          <button
            class="mt-4 rounded-lg bg-cypher-accent px-4 py-2 text-sm font-semibold text-white hover:bg-cypher-accent/80"
            @click="openStageEditor"
          >
            設定階段
          </button>
        </div>
      </div>

      <template v-else>
        <!-- Status Buttons -->
        <div class="mt-6 flex flex-wrap gap-2">
          <button
            v-for="s in ['not_started', 'in_progress', 'paused', 'ended']"
            :key="s"
            class="rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
            :class="
              progress?.status === s
                ? 'bg-cypher-accent text-white'
                : 'bg-cypher-surface-alt text-cypher-muted hover:text-white'
            "
            :disabled="updating"
            @click="setStatus(s)"
          >
            {{ statusLabel(s) }}
          </button>
        </div>

        <!-- Stage List -->
        <div class="mt-6 card p-4 space-y-1">
          <div class="flex items-center justify-between mb-3">
            <h2 class="font-semibold text-white">活動階段</h2>
            <button
              class="text-xs text-cypher-accent hover:underline"
              @click="openStageEditor"
            >
              編輯階段
            </button>
          </div>
          <div
            v-for="(stage, idx) in sortedStages"
            :key="stage.id"
            class="flex items-center justify-between rounded-lg px-3 py-2.5 transition-colors"
            :class="{
              'bg-cypher-accent/20 border border-cypher-accent/40': stageState(idx) === 'current',
              'bg-cypher-surface-alt/50': stageState(idx) === 'completed',
              '': stageState(idx) === 'upcoming',
            }"
          >
            <div class="flex items-center gap-3">
              <div
                class="flex h-6 w-6 items-center justify-center rounded-full border-2 text-xs"
                :class="{
                  'border-cypher-accent bg-cypher-accent text-white':
                    stageState(idx) === 'current',
                  'border-cypher-accent/60 bg-cypher-accent/20 text-cypher-accent':
                    stageState(idx) === 'completed',
                  'border-cypher-border text-cypher-muted': stageState(idx) === 'upcoming',
                }"
              >
                <svg
                  v-if="stageState(idx) === 'completed'"
                  class="h-3 w-3"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="3"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <span
                class="text-sm"
                :class="
                  stageState(idx) === 'current'
                    ? 'font-bold text-white'
                    : stageState(idx) === 'completed'
                      ? 'text-white/60'
                      : 'text-cypher-muted'
                "
              >
                {{ stage.title }}
              </span>
              <span
                v-if="stageState(idx) === 'current'"
                class="ml-1 text-[10px] font-bold uppercase tracking-wider text-cypher-accent"
              >
                目前
              </span>
            </div>
            <button
              v-if="stageState(idx) !== 'current'"
              class="text-xs text-cypher-muted hover:text-cypher-accent"
              :disabled="updating"
              @click="switchToStage(stage.id)"
            >
              切換到此
            </button>
          </div>
        </div>

        <!-- Note -->
        <div class="mt-6 card p-4">
          <h2 class="mb-3 font-semibold text-white">即時備註</h2>
          <p class="mb-2 text-xs text-cypher-muted">
            會即時顯示給所有觀看活動頁面的參加者
          </p>
          <div class="flex gap-2">
            <input
              v-model="noteInput"
              type="text"
              maxlength="500"
              placeholder="例如：第三輪進行中，預計 15:30 結束"
              class="flex-1 rounded-lg border border-cypher-border bg-cypher-bg px-3 py-2 text-sm text-white placeholder-cypher-muted focus:border-cypher-accent focus:outline-none"
              @keyup.enter="updateNote"
            />
            <button
              class="rounded-lg bg-cypher-accent px-4 py-2 text-sm font-semibold text-white hover:bg-cypher-accent/80 disabled:opacity-50"
              :disabled="updating"
              @click="updateNote"
            >
              更新
            </button>
          </div>
        </div>

        <!-- Log -->
        <div class="mt-6 card p-4">
          <h2 class="mb-3 font-semibold text-white">變更歷史</h2>
          <div v-if="log.length === 0" class="text-sm text-cypher-muted">尚無變更記錄</div>
          <div v-else class="max-h-64 space-y-2 overflow-y-auto">
            <div
              v-for="entry in log"
              :key="entry.id"
              class="flex items-start gap-3 text-sm"
            >
              <span class="mt-0.5 whitespace-nowrap text-xs text-cypher-muted">
                {{ formatDateTime(entry.changed_at) }}
              </span>
              <div>
                <span class="text-white/80">
                  {{ statusLabel(entry.status) }}
                </span>
                <span v-if="entry.stage_title" class="text-cypher-accent">
                  &middot; {{ entry.stage_title }}
                </span>
                <span v-if="entry.note" class="ml-1 text-cypher-accent-cyan">
                  &mdash; {{ entry.note }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Stage Editor Modal -->
      <div
        v-if="showStageEditor"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
        @click.self="showStageEditor = false"
      >
        <div class="w-full max-w-md rounded-2xl bg-cypher-surface p-6 shadow-glow">
          <h2 class="font-street text-xl tracking-wider text-white">編輯活動階段</h2>
          <p class="mt-1 text-xs text-cypher-muted">每行一個階段名稱，由上到下為順序</p>
          <button
            class="mt-2 text-xs text-cypher-accent hover:underline"
            @click="loadTemplate"
          >
            載入 Battle 預設模板
          </button>
          <textarea
            v-model="stageEditorText"
            rows="12"
            class="mt-3 w-full rounded-lg border border-cypher-border bg-cypher-bg p-3 text-sm text-white placeholder-cypher-muted focus:border-cypher-accent focus:outline-none"
            placeholder="報到&#10;海選&#10;Top 16&#10;Top 8&#10;決賽&#10;頒獎"
          />
          <div class="mt-4 flex justify-end gap-2">
            <button
              class="rounded-lg bg-cypher-surface-alt px-4 py-2 text-sm text-cypher-muted hover:text-white"
              @click="showStageEditor = false"
            >
              取消
            </button>
            <button
              class="rounded-lg bg-cypher-accent px-4 py-2 text-sm font-semibold text-white hover:bg-cypher-accent/80 disabled:opacity-50"
              :disabled="savingStages"
              @click="saveStages"
            >
              {{ savingStages ? "儲存中..." : "儲存" }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
