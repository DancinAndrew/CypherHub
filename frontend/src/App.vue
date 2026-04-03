<script setup lang="ts">
import { computed, onErrorCaptured, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "./stores/auth";
import { useErrorStore } from "./stores/error";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const errorStore = useErrorStore();

const displayError = computed(() => errorStore.globalError);
const mobileMenuOpen = ref(false);

onErrorCaptured((err) => {
  errorStore.setError(err);
  return false; // stop propagation
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
  errorStore.clearError();
}
</script>

<template>
  <div class="min-h-screen bg-cypher-bg">
    <!-- Skip link -->
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-cypher-accent focus:px-4 focus:py-2 focus:text-white focus:outline-none"
    >
      跳至主內容
    </a>

    <!-- ── Navbar ── -->
    <header class="sticky top-0 z-50 border-b border-white/5 bg-cypher-bg/80 backdrop-blur-xl">
      <!-- Subtle glow line under navbar -->
      <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/30 to-transparent" aria-hidden="true" />

      <nav class="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
        <!-- Left: Logo + Desktop links -->
        <div class="flex items-center gap-8">
          <RouterLink
            :to="{ name: 'home' }"
            class="group flex items-center gap-2 font-street text-xl tracking-[0.25em] text-white transition-all duration-300 hover:tracking-[0.3em]"
          >
            <!-- Logo mark -->
            <span
              class="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-cypher-accent to-cypher-accent-pink text-xs font-black text-white shadow-glow-sm transition-shadow duration-300 group-hover:shadow-glow"
              aria-hidden="true"
            >C</span>
            <span :class="route.name === 'home' ? 'text-white' : 'text-white/80 group-hover:text-white'">
              CYPHERHUB
            </span>
          </RouterLink>

          <!-- Desktop nav links -->
          <div class="hidden items-center gap-1 md:flex">
            <RouterLink
              :to="{ name: 'my-tickets' }"
              class="rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200"
              :class="route.name === 'my-tickets'
                ? 'bg-cypher-accent/10 text-cypher-accent-cyan'
                : 'text-gray-400 hover:bg-white/5 hover:text-white'"
            >
              我的票券
            </RouterLink>
            <RouterLink
              :to="{ name: 'organizer-home' }"
              class="rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200"
              :class="route.path.startsWith('/organizer')
                ? 'bg-cypher-accent/10 text-cypher-accent-cyan'
                : 'text-gray-400 hover:bg-white/5 hover:text-white'"
            >
              主辦方
            </RouterLink>
          </div>
        </div>

        <!-- Right: User area + Mobile menu button -->
        <div class="flex items-center gap-3">
          <!-- Authenticated: avatar + email -->
          <template v-if="authStore.isAuthenticated">
            <RouterLink
              :to="{ name: 'profile' }"
              class="hidden items-center gap-2.5 rounded-xl border border-cypher-border px-3 py-2 transition-all duration-200 hover:border-cypher-accent/40 hover:bg-cypher-surface-alt md:flex"
            >
              <!-- Avatar initials -->
              <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cypher-accent to-cypher-accent-pink text-[10px] font-bold text-white">
                {{ authStore.user?.email?.charAt(0).toUpperCase() ?? '?' }}
              </span>
              <span class="max-w-[120px] truncate text-xs text-gray-400">
                {{ authStore.user?.email }}
              </span>
            </RouterLink>
            <button
              type="button"
              class="btn-secondary hidden py-2 text-sm md:inline-flex"
              @click="handleSignOut"
            >
              登出
            </button>
          </template>

          <!-- Not authenticated -->
          <RouterLink
            v-else
            :to="{ name: 'login' }"
            class="btn-primary hidden py-2 text-sm md:inline-flex"
          >
            登入 / 註冊
          </RouterLink>

          <!-- Mobile menu button -->
          <button
            type="button"
            class="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg border border-cypher-border text-gray-400 transition-all duration-200 hover:border-cypher-accent/40 hover:bg-cypher-surface-alt hover:text-white md:hidden"
            :aria-expanded="mobileMenuOpen"
            aria-label="開啟選單"
            @click="mobileMenuOpen = !mobileMenuOpen"
          >
            <svg v-if="!mobileMenuOpen" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
            <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </nav>

      <!-- Mobile menu -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 -translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-2"
      >
        <div
          v-show="mobileMenuOpen"
          class="border-t border-white/5 bg-cypher-bg/95 px-4 pb-4 pt-3 backdrop-blur-xl md:hidden"
        >
          <div class="space-y-1">
            <RouterLink
              :to="{ name: 'home' }"
              class="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors"
              :class="route.name === 'home' ? 'bg-cypher-accent/10 text-cypher-accent-cyan' : 'text-gray-300 hover:bg-white/5 hover:text-white'"
              @click="mobileMenuOpen = false"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
              </svg>
              探索活動
            </RouterLink>
            <RouterLink
              :to="{ name: 'my-tickets' }"
              class="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors"
              :class="route.name === 'my-tickets' ? 'bg-cypher-accent/10 text-cypher-accent-cyan' : 'text-gray-300 hover:bg-white/5 hover:text-white'"
              @click="mobileMenuOpen = false"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 010 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 010-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375z" />
              </svg>
              我的票券
            </RouterLink>
            <RouterLink
              :to="{ name: 'profile' }"
              class="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors"
              :class="route.name === 'profile' ? 'bg-cypher-accent/10 text-cypher-accent-cyan' : 'text-gray-300 hover:bg-white/5 hover:text-white'"
              @click="mobileMenuOpen = false"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
              </svg>
              個人資料
            </RouterLink>
            <RouterLink
              :to="{ name: 'organizer-home' }"
              class="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors"
              :class="route.path.startsWith('/organizer') ? 'bg-cypher-accent/10 text-cypher-accent-cyan' : 'text-gray-300 hover:bg-white/5 hover:text-white'"
              @click="mobileMenuOpen = false"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
              </svg>
              主辦方管理
            </RouterLink>
          </div>

          <!-- Mobile auth actions -->
          <div class="mt-3 border-t border-white/5 pt-3">
            <div v-if="authStore.isAuthenticated" class="flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cypher-accent to-cypher-accent-pink text-xs font-bold text-white">
                  {{ authStore.user?.email?.charAt(0).toUpperCase() ?? '?' }}
                </span>
                <span class="max-w-[180px] truncate text-xs text-gray-400">{{ authStore.user?.email }}</span>
              </div>
              <button
                type="button"
                class="cursor-pointer rounded-lg border border-cypher-border px-3 py-1.5 text-xs font-medium text-gray-400 transition-colors hover:border-rose-500/40 hover:text-rose-400"
                @click="handleSignOut(); mobileMenuOpen = false"
              >
                登出
              </button>
            </div>
            <RouterLink
              v-else
              :to="{ name: 'login' }"
              class="btn-primary w-full text-sm"
              @click="mobileMenuOpen = false"
            >
              登入 / 註冊
            </RouterLink>
          </div>
        </div>
      </Transition>
    </header>

    <!-- ── Main content ── -->
    <main id="main-content" class="relative min-h-[calc(100vh-4rem)]" tabindex="-1">
      <div v-if="displayError" class="mx-auto max-w-2xl p-6">
        <div class="rounded-2xl border border-rose-500/30 bg-rose-950/60 p-6 backdrop-blur-sm">
          <p class="font-display font-semibold text-rose-300">頁面載入錯誤</p>
          <p class="mt-2 text-sm text-rose-200">{{ displayError.message }}</p>
          <RouterLink
            to="/"
            class="mt-4 inline-flex items-center gap-2 rounded-xl bg-rose-500 px-4 py-2.5 text-sm font-semibold text-white transition-all hover:bg-rose-400"
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
