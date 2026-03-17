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
  <div class="min-h-screen bg-slate-50">
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-brand-600 focus:px-4 focus:py-2 focus:text-white focus:outline-none focus:ring-2 focus:ring-brand-400"
    >
      跳至主內容
    </a>
    <header class="sticky top-0 z-50 border-b border-gray-200 bg-white/95 backdrop-blur-sm">
      <nav class="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
        <div class="flex items-center gap-8">
          <RouterLink
            :to="{ name: 'home' }"
            class="font-display text-lg font-bold tracking-tight text-gray-900 transition-colors hover:text-brand-600"
          >
            CypherHub
          </RouterLink>
          <div class="hidden items-center gap-6 md:flex">
            <RouterLink
              :to="{ name: 'my-tickets' }"
              class="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900"
            >
              My Tickets
            </RouterLink>
            <RouterLink
              :to="{ name: 'profile' }"
              class="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900"
            >
              個人資料
            </RouterLink>
            <RouterLink
              :to="{ name: 'organizer-home' }"
              class="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900"
            >
              Organizer
            </RouterLink>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <p
            v-if="authStore.user"
            class="hidden max-w-[140px] truncate text-xs text-gray-500 md:block"
          >
            {{ authStore.user.email }}
          </p>
          <RouterLink
            v-if="!authStore.isAuthenticated"
            :to="{ name: 'login' }"
            class="btn-primary"
          >
            Login
          </RouterLink>
          <button
            v-else
            type="button"
            class="btn-secondary"
            @click="handleSignOut"
          >
            Logout
          </button>
        </div>
      </nav>
    </header>

    <main id="main-content" class="relative min-h-[calc(100vh-3.5rem)]" tabindex="-1">
      <div v-if="captureError" class="mx-auto max-w-2xl p-6">
        <div class="rounded-xl border border-rose-200 bg-rose-50 p-6">
          <p class="font-display font-semibold text-rose-800">頁面載入錯誤</p>
          <p class="mt-2 text-sm text-rose-800">{{ captureError.message }}</p>
          <RouterLink
            to="/"
            class="mt-4 inline-block rounded-lg bg-rose-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-rose-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-500"
            @click="clearError"
          >
            返回首頁
          </RouterLink>
        </div>
      </div>
      <router-view v-else :key="route.fullPath" />
    </main>
  </div>
</template>
