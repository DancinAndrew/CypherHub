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
  <div class="min-h-screen bg-cypher-bg">
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-cypher-accent focus:px-4 focus:py-2 focus:text-white focus:outline-none focus:ring-2 focus:ring-cypher-accent-pink"
    >
      跳至主內容
    </a>
    <header class="sticky top-0 z-50 border-b border-white/10 bg-cypher-bg/90 backdrop-blur-xl transition-all duration-300">
      <nav class="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4">
        <div class="flex items-center gap-10">
          <RouterLink
            :to="{ name: 'home' }"
            class="font-street text-2xl tracking-[0.2em] transition-all duration-300 hover:text-cypher-accent-pink hover:tracking-[0.25em]"
            :class="route.name === 'home' ? 'text-cypher-accent-pink' : 'text-white'"
          >
            CYPHERHUB
          </RouterLink>
          <div class="hidden items-center gap-8 md:flex">
            <RouterLink
              :to="{ name: 'my-tickets' }"
              class="nav-link"
              :class="{ 'nav-link-active': route.name === 'my-tickets' }"
            >
              My Tickets
            </RouterLink>
            <RouterLink
              :to="{ name: 'profile' }"
              class="nav-link"
              :class="{ 'nav-link-active': route.name === 'profile' }"
            >
              個人資料
            </RouterLink>
            <RouterLink
              :to="{ name: 'organizer-home' }"
              class="nav-link"
              :class="{ 'nav-link-active': route.path.startsWith('/organizer') }"
            >
              Organizer
            </RouterLink>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <p
            v-if="authStore.user"
            class="hidden max-w-[140px] truncate text-xs text-cypher-muted md:block"
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

    <main id="main-content" class="relative min-h-[calc(100vh-4rem)]" tabindex="-1">
      <div v-if="captureError" class="mx-auto max-w-2xl p-6">
        <div class="rounded-xl border border-rose-500/50 bg-rose-950/80 p-6 backdrop-blur-sm">
          <p class="font-display font-semibold text-rose-300">頁面載入錯誤</p>
          <p class="mt-2 text-sm text-rose-200">{{ captureError.message }}</p>
          <RouterLink
            to="/"
            class="mt-4 inline-block rounded bg-rose-500 px-4 py-2.5 text-sm font-semibold text-white transition-all hover:bg-rose-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-400"
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
