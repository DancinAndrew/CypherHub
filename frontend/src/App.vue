<script setup lang="ts">
import { useRouter } from "vue-router";

import { useAuthStore } from "./stores/auth";

const router = useRouter();
const authStore = useAuthStore();

async function handleSignOut(): Promise<void> {
  try {
    await authStore.signOut();
    await router.push({ name: "home" });
  } catch (error) {
    console.error(error);
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <header class="border-b border-slate-200 bg-white/95 backdrop-blur">
      <nav class="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
        <div class="flex items-center gap-3">
          <RouterLink :to="{ name: 'home' }" class="text-lg font-bold text-slate-900">CypherHub</RouterLink>
          <RouterLink :to="{ name: 'my-tickets' }" class="text-sm text-slate-600 hover:text-slate-900">My Tickets</RouterLink>
          <RouterLink :to="{ name: 'organizer-manage' }" class="text-sm text-slate-600 hover:text-slate-900">
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

    <router-view />
  </div>
</template>
