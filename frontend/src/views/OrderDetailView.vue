<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
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
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "無法載入訂單");
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadDetail().catch(() => {});
});
</script>

<template>
  <main class="mx-auto w-full max-w-2xl px-4 pb-20 pt-8">
    <div v-if="loading" class="flex flex-col items-center justify-center py-24">
      <span class="h-10 w-10 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" />
      <p class="mt-4 text-cypher-muted">載入訂單中...</p>
    </div>

    <div v-else-if="errorMessage" class="rounded-2xl border border-rose-500/40 bg-rose-950/60 p-6 text-rose-300">
      {{ errorMessage }}
    </div>

    <div v-else-if="detail" class="space-y-6">
      <h1 class="font-street text-2xl tracking-wider text-white">訂單詳情</h1>

      <div class="card p-6">
        <div class="flex items-center justify-between">
          <span class="text-sm text-cypher-muted">訂單編號</span>
          <code class="rounded bg-cypher-surface-alt px-2 py-1 text-xs text-gray-300">{{ detail.order.id.slice(0, 8) }}...</code>
        </div>
        <div class="mt-4 flex items-center justify-between">
          <span class="text-sm text-cypher-muted">狀態</span>
          <span
            class="rounded-full px-3 py-1 text-sm font-medium"
            :class="{
              'bg-amber-500/20 text-amber-400': detail.order.status === 'holding' || detail.order.status === 'pending_payment',
              'bg-emerald-500/20 text-emerald-400': detail.order.status === 'paid' || detail.order.status === 'issued',
              'bg-gray-500/20 text-gray-400': detail.order.status === 'cancelled' || detail.order.status === 'refunded',
            }"
          >
            {{ statusLabel[detail.order.status] ?? detail.order.status }}
          </span>
        </div>
        <div class="mt-2 flex items-center justify-between">
          <span class="text-sm text-cypher-muted">總金額</span>
          <span class="font-semibold text-white">{{ formatPrice(detail.order.total_cents) }} {{ detail.order.currency }}</span>
        </div>
        <p v-if="detail.order.hold_expires_at && detail.order.status === 'holding'" class="mt-2 text-xs text-amber-400">
          保留至 {{ formatDateTime(detail.order.hold_expires_at) }}，逾時將自動釋放
        </p>
      </div>

      <div v-if="detail.items.length" class="card p-6">
        <h2 class="font-medium text-white">訂單內容</h2>
        <ul class="mt-4 space-y-3">
          <li
            v-for="item in detail.items"
            :key="item.id"
            class="flex justify-between rounded-xl border border-cypher-border p-3 text-sm"
          >
            <span class="text-gray-300">× {{ item.quantity }} · {{ formatPrice(item.price_cents) }}/張</span>
            <span class="text-white">{{ formatPrice(item.price_cents * item.quantity) }}</span>
          </li>
        </ul>
      </div>

      <div v-if="detail.order.status === 'issued'" class="rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-4 text-emerald-300">
        <p class="font-medium">✓ 已出票</p>
        <p class="mt-1 text-sm">請至「我的票券」查看。</p>
        <button type="button" class="btn-primary mt-4" @click="router.push({ name: 'my-tickets' })">
          查看我的票券
        </button>
      </div>

      <button type="button" class="btn-secondary w-full" @click="router.push({ name: 'home' })">
        返回首頁
      </button>
    </div>
  </main>
</template>
