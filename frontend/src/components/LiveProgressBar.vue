<script setup lang="ts">
import { computed } from "vue";
import type { EventProgress, EventStage } from "../api/client";

const props = defineProps<{
  progress: EventProgress | null;
  stages: EventStage[];
}>();

const sortedStages = computed(() => [...props.stages].sort((a, b) => a.sort_order - b.sort_order));

const currentIndex = computed(() => {
  if (!props.progress?.current_stage_id) return -1;
  return sortedStages.value.findIndex((s) => s.id === props.progress!.current_stage_id);
});

const isLive = computed(() => props.progress?.status === "in_progress");
const isPaused = computed(() => props.progress?.status === "paused");
const isEnded = computed(() => props.progress?.status === "ended");
const isNotStarted = computed(() => !props.progress || props.progress.status === "not_started");

const statusLabel = computed(() => {
  if (isLive.value) return "LIVE";
  if (isPaused.value) return "暫停中";
  if (isEnded.value) return "已結束";
  return "尚未開始";
});

function stageState(index: number): "completed" | "current" | "upcoming" {
  if (isEnded.value) return "completed";
  if (currentIndex.value < 0) return "upcoming";
  if (index < currentIndex.value) return "completed";
  if (index === currentIndex.value) return "current";
  return "upcoming";
}

const updatedTimeStr = computed(() => {
  if (!props.progress?.updated_at) return null;
  const d = new Date(props.progress.updated_at);
  return d.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit" });
});
</script>

<template>
  <div
    v-if="stages.length > 0 && !isNotStarted"
    class="rounded-2xl border border-cypher-border bg-cypher-surface p-5"
  >
    <!-- Header -->
    <div class="mb-4 flex items-center gap-3">
      <span
        v-if="isLive"
        class="inline-flex items-center gap-1.5 rounded-full bg-red-500/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-red-400"
      >
        <span class="relative flex h-2 w-2">
          <span
            class="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75"
          />
          <span class="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
        </span>
        {{ statusLabel }}
      </span>
      <span
        v-else-if="isPaused"
        class="inline-flex items-center gap-1.5 rounded-full bg-yellow-500/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-yellow-400"
      >
        {{ statusLabel }}
      </span>
      <span
        v-else-if="isEnded"
        class="inline-flex items-center gap-1.5 rounded-full bg-cypher-muted/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-cypher-muted"
      >
        {{ statusLabel }}
      </span>
      <span class="text-sm font-semibold text-white/90">即時進度</span>
    </div>

    <!-- Progress Steps -->
    <div class="relative flex items-start justify-between">
      <template v-for="(stage, idx) in sortedStages" :key="stage.id">
        <!-- Connector Line -->
        <div
          v-if="idx > 0"
          class="mt-3 h-0.5 flex-1"
          :class="
            stageState(idx) === 'upcoming'
              ? 'bg-cypher-border'
              : 'bg-gradient-to-r from-cypher-accent to-cypher-accent-pink'
          "
        />

        <!-- Stage Dot + Label -->
        <div class="flex flex-col items-center" style="min-width: 48px; max-width: 80px">
          <div
            class="flex h-7 w-7 items-center justify-center rounded-full border-2 transition-all duration-300"
            :class="{
              'border-cypher-accent bg-cypher-accent text-white shadow-glow-sm':
                stageState(idx) === 'current',
              'border-cypher-accent bg-cypher-accent/30 text-cypher-accent':
                stageState(idx) === 'completed',
              'border-cypher-border bg-cypher-surface text-cypher-muted':
                stageState(idx) === 'upcoming',
            }"
          >
            <svg
              v-if="stageState(idx) === 'completed'"
              class="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="3"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <span
              v-else-if="stageState(idx) === 'current'"
              class="h-2 w-2 rounded-full bg-white"
            />
          </div>
          <span
            class="mt-1.5 text-center text-[10px] leading-tight"
            :class="
              stageState(idx) === 'current'
                ? 'font-bold text-white'
                : stageState(idx) === 'completed'
                  ? 'text-cypher-accent/80'
                  : 'text-cypher-muted'
            "
          >
            {{ stage.title }}
          </span>
        </div>
      </template>
    </div>

    <!-- Current Stage Info + Note -->
    <div v-if="progress && (progress.current_stage_title || progress.note)" class="mt-4 space-y-1">
      <p v-if="progress.current_stage_title" class="text-sm text-white/80">
        <span class="text-cypher-muted">目前階段：</span>
        <span class="font-semibold">{{ progress.current_stage_title }}</span>
      </p>
      <p v-if="progress.note" class="text-sm text-cypher-accent-cyan">
        {{ progress.note }}
      </p>
      <p v-if="updatedTimeStr" class="text-xs text-cypher-muted">
        更新於 {{ updatedTimeStr }}
      </p>
    </div>
  </div>
</template>
