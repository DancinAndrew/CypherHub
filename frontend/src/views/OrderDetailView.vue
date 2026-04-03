<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { fetchOrderDetail, type OrderDetail } from "../api/client";
import { toApiErrorMessage } from "../utils/errorMessages";

const route = useRoute();
const router = useRouter();

const orderId = computed(() => String(route.params.orderId ?? ""));
const detail = ref<OrderDetail | null>(null);
const loading = ref(true);
const errorMessage = ref<string | null>(null);

const statusLabel: Record<string, string> = {
  holding: "名額保留中",
  pending_payment: "等待付款",
  paid: "付款成功",
  issued: "已出票",
  cancelled: "已取消",
  refunded: "已退款",
};

function formatPrice(cents: number): string {
  return `$${(cents / 100).toLocaleString()}`;
}

function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-TW", { dateStyle: "medium", timeStyle: "short" });
}

const countdown = ref("");
let countdownTimer: ReturnType<typeof setInterval> | null = null;

function updateCountdown(): void {
  const order = detail.value?.order;
  if (!order || order.status !== "holding" || !order.hold_expires_at) {
    countdown.value = "";
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
    return;
  }
  const diff = new Date(order.hold_expires_at).getTime() - Date.now();
  if (diff <= 0) {
    countdown.value = "已逾時";
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
    return;
  }
  const mins = Math.floor(diff / 60000);
  const secs = Math.floor((diff % 60000) / 1000);
  countdown.value = `${mins}:${String(secs).padStart(2, "0")}`;
}

function startCountdown(): void {
  if (countdownTimer) clearInterval(countdownTimer);
  updateCountdown();
  countdownTimer = setInterval(updateCountdown, 1000);
}

async function loadDetail(): Promise<void> {
  if (!orderId.value) {
    errorMessage.value = "缺少訂單 ID";
    loading.value = false;
    return;
  }
  loading.value = true;
  errorMessage.value = null;
  try {
    detail.value = await fetchOrderDetail(orderId.value);
    startCountdown();
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "無法載入訂單");
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadDetail().catch(() => {});
});

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer);
});
</script>

<template>
  <main class="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden px-4 pb-20 pt-10">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="pointer-events-none absolute inset-0" style="background: radial-gradient(ellipse 50% 40% at 50% 0%, rgba(124,58,237,0.10) 0%, transparent 70%)" aria-hidden="true" />

    <div class="relative z-10 mx-auto w-full max-w-2xl">

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-32">
        <span class="h-10 w-10 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" aria-hidden="true" />
        <p class="mt-4 text-sm text-cypher-muted">載入訂單中…</p>
      </div>

      <!-- Error -->
      <div v-else-if="errorMessage" role="alert" class="card-glass flex items-start gap-3 border-rose-500/30 p-6">
        <svg class="mt-0.5 h-5 w-5 shrink-0 text-rose-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        <p class="text-sm text-rose-300">{{ errorMessage }}</p>
      </div>

      <!-- Content -->
      <div v-else-if="detail" class="animate-slide-up space-y-5">

        <!-- Page header -->
        <div class="mb-8">
          <p class="section-label mb-2">Order</p>
          <div class="flex items-center gap-3">
            <span class="h-6 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
            <h1 class="font-street text-2xl tracking-widest text-white">訂單詳情</h1>
          </div>
        </div>

        <!-- Order summary card -->
        <div class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md">
          <!-- Top accent line -->
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/50 to-transparent" aria-hidden="true" />

          <div class="p-6">
            <!-- Status + amount row -->
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-xs text-cypher-muted">訂單狀態</p>
                <span
                  class="mt-1.5 inline-flex rounded-full border px-3 py-1 text-sm font-semibold"
                  :class="{
                    'border-amber-500/40 bg-amber-500/10 text-amber-400': detail.order.status === 'holding' || detail.order.status === 'pending_payment',
                    'border-emerald-500/40 bg-emerald-500/10 text-emerald-400': detail.order.status === 'paid' || detail.order.status === 'issued',
                    'border-white/10 bg-white/5 text-gray-400': detail.order.status === 'cancelled' || detail.order.status === 'refunded',
                  }"
                >
                  {{ statusLabel[detail.order.status] ?? detail.order.status }}
                </span>
              </div>
              <div class="text-right">
                <p class="text-xs text-cypher-muted">總金額</p>
                <p class="mt-1 text-2xl font-bold text-white">
                  {{ formatPrice(detail.order.total_cents) }}
                  <span class="text-sm font-normal text-cypher-muted">{{ detail.order.currency }}</span>
                </p>
              </div>
            </div>

            <!-- Divider -->
            <div class="my-5 h-px bg-white/5" />

            <!-- Meta rows -->
            <dl class="space-y-3">
              <div class="flex items-center justify-between text-sm">
                <dt class="text-cypher-muted">訂單編號</dt>
                <dd>
                  <code class="rounded-lg bg-cypher-surface-alt px-2.5 py-1 font-mono text-xs tracking-wider text-gray-300">
                    {{ detail.order.id.slice(0, 8).toUpperCase() }}…
                  </code>
                </dd>
              </div>
              <div v-if="detail.order.created_at" class="flex items-center justify-between text-sm">
                <dt class="text-cypher-muted">建立時間</dt>
                <dd class="text-gray-300">{{ formatDateTime(detail.order.created_at) }}</dd>
              </div>
            </dl>

            <!-- Countdown banner (holding status) -->
            <div
              v-if="detail.order.hold_expires_at && detail.order.status === 'holding'"
              class="mt-5 flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3"
            >
              <svg class="h-4 w-4 shrink-0 text-amber-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span v-if="countdown && countdown !== '已逾時'" class="text-sm text-amber-400">
                名額保留中，<span class="font-mono font-bold">{{ countdown }}</span> 後逾時，名額將自動釋放
              </span>
              <span v-else class="text-sm font-semibold text-rose-400">已逾時，名額將自動釋放</span>
            </div>
          </div>
        </div>

        <!-- Order items card -->
        <div v-if="detail.items.length" class="rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md">
          <div class="border-b border-white/5 px-6 py-4">
            <h2 class="text-sm font-semibold text-white">訂單內容</h2>
          </div>
          <ul class="divide-y divide-white/5 px-6">
            <li
              v-for="item in detail.items"
              :key="item.id"
              class="flex items-center justify-between py-4"
            >
              <div class="flex items-center gap-3">
                <span class="flex h-7 w-7 items-center justify-center rounded-lg border border-cypher-accent/30 bg-cypher-accent/10 text-xs font-bold text-cypher-accent-bright">
                  ×{{ item.quantity }}
                </span>
                <span class="text-sm text-gray-300">{{ formatPrice(item.price_cents) }} / 張</span>
              </div>
              <span class="font-semibold text-white">{{ formatPrice(item.price_cents * item.quantity) }}</span>
            </li>
          </ul>
          <div class="flex items-center justify-between border-t border-white/5 px-6 py-4">
            <span class="text-sm font-semibold text-cypher-muted">合計</span>
            <span class="text-base font-bold text-white">{{ formatPrice(detail.order.total_cents) }}</span>
          </div>
        </div>

        <!-- Issued success banner -->
        <div
          v-if="detail.order.status === 'issued'"
          class="relative overflow-hidden rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-6 backdrop-blur-sm"
        >
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent" aria-hidden="true" />
          <div class="flex items-start gap-4">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-500/40 bg-emerald-500/10">
              <svg class="h-5 w-5 text-emerald-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="flex-1">
              <p class="font-semibold text-emerald-300">已成功出票</p>
              <p class="mt-1 text-sm text-emerald-400/80">前往「我的票券」查看入場 QR Code。</p>
              <button
                type="button"
                class="btn-primary mt-4 px-5 py-2.5 text-sm"
                @click="router.push({ name: 'my-tickets' })"
              >
                查看我的票券
              </button>
            </div>
          </div>
        </div>

        <!-- Back button -->
        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-xl border border-cypher-border bg-cypher-surface py-3 text-sm font-medium text-gray-400 transition-all hover:border-cypher-accent/40 hover:bg-cypher-surface-alt hover:text-white"
          @click="router.push({ name: 'home' })"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          返回首頁
        </button>

      </div>
    </div>
  </main>
</template>
