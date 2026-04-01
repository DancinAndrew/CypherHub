import { ref, onMounted, onUnmounted } from "vue";
import { supabase } from "../api/supabase";
import { fetchEventProgress } from "../api/client";
import type { EventProgress, EventStage } from "../api/client";

export function useEventProgress(eventId: string) {
  const progress = ref<EventProgress | null>(null);
  const stages = ref<EventStage[]>([]);
  const loading = ref(true);

  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let channelRef: ReturnType<typeof supabase.channel> | null = null;

  async function refresh() {
    try {
      const res = await fetchEventProgress(eventId);
      progress.value = res.progress;
      stages.value = res.stages;
    } catch {
      // silent — keep stale data
    }
  }

  function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(refresh, 30_000);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  onMounted(async () => {
    // initial fetch
    await refresh();
    loading.value = false;

    // Realtime subscription
    try {
      const channel = supabase
        .channel(`event-progress-${eventId}`)
        .on(
          "postgres_changes",
          {
            event: "*",
            schema: "public",
            table: "event_progress",
            filter: `event_id=eq.${eventId}`,
          },
          () => {
            // Refetch full data (includes stage title resolution)
            refresh();
          },
        )
        .subscribe((status: string) => {
          if (status === "SUBSCRIBED") {
            stopPolling();
          } else if (status === "CHANNEL_ERROR" || status === "TIMED_OUT") {
            startPolling();
          }
        });

      channelRef = channel;
    } catch {
      // Realtime unavailable — fallback to polling
      startPolling();
    }
  });

  onUnmounted(() => {
    stopPolling();
    if (channelRef) {
      supabase.removeChannel(channelRef);
      channelRef = null;
    }
  });

  return { progress, stages, loading, refresh };
}
