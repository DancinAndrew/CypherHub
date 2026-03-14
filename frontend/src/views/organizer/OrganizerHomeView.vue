<script setup lang="ts">
import { useOrganizerStore } from "../../stores/organizer";

const organizerStore = useOrganizerStore();
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-10">
    <h1 class="text-2xl font-bold text-slate-900">主辦方管理中心</h1>
    <p class="mt-2 text-sm text-slate-600">依步驟建立活動與設定報名表單。</p>

    <div class="mt-8 space-y-4">
      <router-link
        to="/organizer/apply"
        class="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-300 hover:shadow-md"
      >
        <span class="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-xl font-bold text-brand-600">1</span>
        <div class="flex-1">
          <h2 class="font-semibold text-slate-900">申請成為主辦方</h2>
          <p class="mt-1 text-sm text-slate-600">建立主辦方帳號（目前免審核）</p>
        </div>
        <span class="text-slate-400">→</span>
      </router-link>

      <router-link
        to="/organizer/events"
        class="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-300 hover:shadow-md"
      >
        <span class="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-xl font-bold text-brand-600">2</span>
        <div class="flex-1">
          <h2 class="font-semibold text-slate-900">建立 / 編輯活動</h2>
          <p class="mt-1 text-sm text-slate-600">建立活動、票種、主辦方備註</p>
        </div>
        <span class="text-slate-400">→</span>
      </router-link>

      <router-link
        to="/organizer/forms"
        class="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-300 hover:shadow-md"
      >
        <span class="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-xl font-bold text-brand-600">3</span>
        <div class="flex-1">
          <h2 class="font-semibold text-slate-900">報名表單設定</h2>
          <p class="mt-1 text-sm text-slate-600">自訂報名時需填寫的欄位</p>
        </div>
        <span class="text-slate-400">→</span>
      </router-link>
    </div>

    <div class="mt-12 rounded-xl border border-slate-200 bg-slate-50 p-6">
      <h2 class="font-semibold text-slate-800">其他功能</h2>
      <div class="mt-4 flex flex-wrap gap-4">
        <router-link
          to="/organizer/checkin"
          class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-white"
        >
          核銷介面
        </router-link>
      </div>
    </div>

    <p v-if="organizerStore.orgId" class="mt-6 text-xs text-slate-500">已登入主辦方：{{ organizerStore.orgId }}</p>
  </main>
</template>
