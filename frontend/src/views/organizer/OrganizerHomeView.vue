<script setup lang="ts">
import { useOrganizerStore } from "../../stores/organizer";

const organizerStore = useOrganizerStore();
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-12">
    <h1 class="font-display text-3xl font-bold tracking-tight text-gray-900">主辦方管理中心</h1>
    <p class="mt-2 text-gray-500">依步驟建立活動與設定報名表單。</p>

    <div class="mt-10 space-y-4">
      <router-link
        to="/organizer/apply"
        class="card flex items-center gap-5 p-6 transition-all hover:border-brand-500/40"
      >
        <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-brand-100 text-xl font-bold text-brand-700">1</span>
        <div class="flex-1 min-w-0">
          <h2 class="font-display font-semibold text-gray-900">申請成為主辦方</h2>
          <p class="mt-1 text-sm text-gray-500">建立主辦方帳號（目前免審核）</p>
        </div>
        <span class="text-brand-400">→</span>
      </router-link>

      <router-link
        to="/organizer/events/create"
        class="card flex items-center gap-5 p-6 transition-all hover:border-brand-500/40"
      >
        <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-brand-100 text-xl font-bold text-brand-700">2</span>
        <div class="flex-1 min-w-0">
          <h2 class="font-display font-semibold text-gray-900">建立活動</h2>
          <p class="mt-1 text-sm text-gray-500">建立新活動、票種、主辦方備註</p>
        </div>
        <span class="text-brand-400">→</span>
      </router-link>

      <router-link
        to="/organizer/events/edit"
        class="card flex items-center gap-5 p-6 transition-all hover:border-brand-500/40"
      >
        <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-brand-100 text-xl font-bold text-brand-700">3</span>
        <div class="flex-1 min-w-0">
          <h2 class="font-display font-semibold text-gray-900">編輯活動</h2>
          <p class="mt-1 text-sm text-gray-500">選擇既有活動載入後編輯</p>
        </div>
        <span class="text-brand-400">→</span>
      </router-link>

      <router-link
        to="/organizer/forms"
        class="card flex items-center gap-5 p-6 transition-all hover:border-brand-500/40"
      >
        <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-brand-100 text-xl font-bold text-brand-700">4</span>
        <div class="flex-1 min-w-0">
          <h2 class="font-display font-semibold text-gray-900">報名表單設定</h2>
          <p class="mt-1 text-sm text-gray-500">自訂報名時需填寫的欄位</p>
        </div>
        <span class="text-brand-400">→</span>
      </router-link>
    </div>

    <div class="card mt-12 p-6">
      <h2 class="font-display font-semibold text-gray-700">其他功能</h2>
      <div class="mt-4 flex flex-wrap gap-3">
        <router-link
          to="/organizer/manage"
          class="btn-secondary"
        >
          主辦方管理
        </router-link>
        <router-link
          to="/organizer/checkin"
          class="btn-secondary"
        >
          核銷介面
        </router-link>
      </div>
    </div>

    <p v-if="organizerStore.orgId" class="mt-6 text-xs text-gray-500">已登入主辦方：{{ organizerStore.orgId }}</p>
  </main>
</template>
