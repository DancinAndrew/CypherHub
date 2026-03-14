<script setup lang="ts">
import { onErrorCaptured, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "./stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const captureError = ref<Error | null>(null);

onErrorCaptured((err) => {
  captureError.value = err;
  return false;
});

async function handleSignOut(): Promise<void> {
  try {
    await authStore.signOut();
    await router.push({ name: "home" });
  } catch {
    // signOut failed; user remains on current page
  }
}

function clearError() {
  captureError.value = null;
}
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <header class="border-b border-slate-200 bg-white/95 backdrop-blur">
      <nav class="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
        <div class="flex items-center gap-3">
          <RouterLink :to="{ name: 'home' }" class="text-lg font-bold text-slate-900">CypherHub</RouterLink>
          <RouterLink :to="{ name: 'my-tickets' }" class="text-sm text-slate-600 hover:text-slate-900">My Tickets</RouterLink>
          <RouterLink :to="{ name: 'profile' }" class="text-sm text-slate-600 hover:text-slate-900">個人資料</RouterLink>
          <RouterLink :to="{ name: 'organizer-home' }" class="text-sm text-slate-600 hover:text-slate-900">
            Organizer
          </RouterLink>
        </div>

        <div class="flex items-center gap-3">
          <p v-if="authStore.user" class="hidden text-xs text-slate-500 md:block">{{ authStore.user.email }}</p>
          <RouterLink
            v-if="!authStore.isAuthenticated"
            :to="{ name: 'login' }"
            class="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Login
          </RouterLink>
          <button
            v-else
            type="button"
            class="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            @click="handleSignOut"
          >
            Logout
          </button>
        </div>
      </nav>
    </header>

    <main class="min-h-[calc(100vh-4rem)]">
      <div v-if="captureError" class="mx-auto max-w-2xl p-6">
        <div class="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-800">
          <p class="font-semibold">頁面載入錯誤</p>
          <p class="mt-1 text-sm">{{ captureError.message }}</p>
          <RouterLink to="/" class="mt-3 inline-block rounded-lg bg-rose-200 px-3 py-1 text-sm font-medium hover:bg-rose-300" @click="clearError">返回首頁</RouterLink>
        </div>
      </div>
      <router-view v-else :key="route.fullPath" />
    </main>
  </div>
</template>
