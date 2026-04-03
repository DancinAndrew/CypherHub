<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchMyOrganizerSummary, type MyOrganizerOrg } from "../../api/client";
import { useOrganizerStore } from "../../stores/organizer";

const organizerStore = useOrganizerStore();
const router = useRouter();
const summary = ref<{ organizations: MyOrganizerOrg[] } | null>(null);

/** MVP-3.1: owner/admin 可管理活動；staff 僅核銷與名單 */
const canManageEvents = computed(() => {
  const orgs = summary.value?.organizations ?? [];
  return orgs.some((o) => o.role === "owner" || o.role === "admin");
});

onMounted(async () => {
  try {
    const data = await fetchMyOrganizerSummary();
    summary.value = { organizations: data.organizations };
  } catch {
    summary.value = { organizations: [] };
  }
});
</script>

<template>
  <main class="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden px-4 pb-20 pt-10">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="pointer-events-none absolute inset-0" style="background: radial-gradient(ellipse 60% 40% at 20% 0%, rgba(124,58,237,0.12) 0%, transparent 70%)" aria-hidden="true" />

    <div class="relative z-10 mx-auto w-full max-w-2xl">

      <!-- Page header -->
      <header class="animate-fade-in mb-10">
        <p class="section-label mb-2">Organizer</p>
        <div class="flex items-center gap-3">
          <span class="h-6 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
          <h1 class="font-street text-2xl tracking-widest text-white">主辦方管理中心</h1>
        </div>
        <p class="mt-2 pl-3.5 text-sm text-cypher-muted">依步驟建立活動與設定報名表單。</p>
      </header>

      <!-- Step cards -->
      <div class="space-y-4">

        <!-- Step 1: Apply (always visible) -->
        <router-link
          to="/organizer/apply"
          class="group relative block overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md transition-all duration-300 hover:border-cypher-accent/40 hover:shadow-glow-sm"
          :style="{ animation: 'slideUp 0.5s ease-out 0.05s both' }"
        >
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/50 to-transparent" aria-hidden="true" />
          <div class="flex items-center gap-5 p-6">
            <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cypher-accent/30 to-cypher-accent-pink/20 text-lg font-bold text-cypher-accent-bright ring-1 ring-cypher-accent/30">
              1
            </span>
            <div class="min-w-0 flex-1">
              <h2 class="font-display font-semibold text-white transition-colors group-hover:text-cypher-accent-bright">申請成為主辦方</h2>
              <p class="mt-0.5 text-sm text-cypher-muted">建立主辦方帳號（目前免審核）</p>
            </div>
            <svg class="h-5 w-5 shrink-0 text-cypher-muted transition-all duration-200 group-hover:translate-x-1 group-hover:text-cypher-accent" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </div>
        </router-link>

        <!-- Steps 2-4: Owner/admin only -->
        <template v-if="canManageEvents">
          <router-link
            to="/organizer/events/create"
            class="group relative block overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md transition-all duration-300 hover:border-cypher-accent/40 hover:shadow-glow-sm"
            :style="{ animation: 'slideUp 0.5s ease-out 0.1s both' }"
          >
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-cyan/40 to-transparent" aria-hidden="true" />
            <div class="flex items-center gap-5 p-6">
              <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cypher-accent-cyan/20 to-cypher-accent/10 text-lg font-bold text-cypher-accent-cyan ring-1 ring-cypher-accent-cyan/30">
                2
              </span>
              <div class="min-w-0 flex-1">
                <h2 class="font-display font-semibold text-white transition-colors group-hover:text-cypher-accent-bright">建立活動</h2>
                <p class="mt-0.5 text-sm text-cypher-muted">建立新活動、票種、主辦方備註</p>
              </div>
              <svg class="h-5 w-5 shrink-0 text-cypher-muted transition-all duration-200 group-hover:translate-x-1 group-hover:text-cypher-accent" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </div>
          </router-link>

          <router-link
            to="/organizer/events/edit"
            class="group relative block overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md transition-all duration-300 hover:border-cypher-accent/40 hover:shadow-glow-sm"
            :style="{ animation: 'slideUp 0.5s ease-out 0.15s both' }"
          >
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-pink/40 to-transparent" aria-hidden="true" />
            <div class="flex items-center gap-5 p-6">
              <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cypher-accent-pink/20 to-cypher-accent/10 text-lg font-bold text-cypher-accent-pink ring-1 ring-cypher-accent-pink/30">
                3
              </span>
              <div class="min-w-0 flex-1">
                <h2 class="font-display font-semibold text-white transition-colors group-hover:text-cypher-accent-bright">編輯活動</h2>
                <p class="mt-0.5 text-sm text-cypher-muted">選擇既有活動載入後編輯</p>
              </div>
              <svg class="h-5 w-5 shrink-0 text-cypher-muted transition-all duration-200 group-hover:translate-x-1 group-hover:text-cypher-accent" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </div>
          </router-link>

          <router-link
            to="/organizer/forms"
            class="group relative block overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md transition-all duration-300 hover:border-cypher-accent/40 hover:shadow-glow-sm"
            :style="{ animation: 'slideUp 0.5s ease-out 0.2s both' }"
          >
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-orange/40 to-transparent" aria-hidden="true" />
            <div class="flex items-center gap-5 p-6">
              <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cypher-accent-orange/20 to-cypher-accent/10 text-lg font-bold text-cypher-accent-orange ring-1 ring-cypher-accent-orange/30">
                4
              </span>
              <div class="min-w-0 flex-1">
                <h2 class="font-display font-semibold text-white transition-colors group-hover:text-cypher-accent-bright">報名表單設定</h2>
                <p class="mt-0.5 text-sm text-cypher-muted">自訂報名時需填寫的欄位</p>
              </div>
              <svg class="h-5 w-5 shrink-0 text-cypher-muted transition-all duration-200 group-hover:translate-x-1 group-hover:text-cypher-accent" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </div>
          </router-link>
        </template>

        <!-- Staff notice -->
        <div
          v-else-if="summary"
          class="flex items-start gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-5 py-4"
          style="animation: slideUp 0.5s ease-out 0.1s both"
        >
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-amber-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <p class="text-sm text-amber-300">
            您目前為 staff 身分，僅可核銷與查看名單。建立/編輯活動請聯絡主辦方 owner 或 admin。
          </p>
        </div>
      </div>

      <!-- Quick access grid -->
      <div
        class="relative mt-8 overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md"
        style="animation: slideUp 0.5s ease-out 0.25s both"
      >
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" aria-hidden="true" />
        <div class="border-b border-white/5 px-6 py-4">
          <h2 class="text-sm font-semibold text-cypher-muted">快速入口</h2>
        </div>
        <div class="grid grid-cols-1 divide-y divide-white/5 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <router-link
            v-if="canManageEvents"
            to="/organizer/members"
            class="group flex items-center gap-3 px-6 py-4 transition-colors hover:bg-white/[0.03]"
          >
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-cypher-accent/20 bg-cypher-accent/10 text-cypher-accent transition-colors group-hover:border-cypher-accent/40 group-hover:bg-cypher-accent/20" aria-hidden="true">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
              </svg>
            </span>
            <span class="text-sm font-medium text-gray-300 transition-colors group-hover:text-white">成員管理</span>
          </router-link>

          <router-link
            to="/organizer/manage"
            class="group flex items-center gap-3 px-6 py-4 transition-colors hover:bg-white/[0.03]"
          >
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-cypher-accent-cyan/20 bg-cypher-accent-cyan/10 text-cypher-accent-cyan transition-colors group-hover:border-cypher-accent-cyan/40 group-hover:bg-cypher-accent-cyan/20" aria-hidden="true">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
              </svg>
            </span>
            <span class="text-sm font-medium text-gray-300 transition-colors group-hover:text-white">主辦方管理</span>
          </router-link>

          <router-link
            to="/organizer/checkin"
            class="group flex items-center gap-3 px-6 py-4 transition-colors hover:bg-white/[0.03]"
          >
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-cypher-accent-pink/20 bg-cypher-accent-pink/10 text-cypher-accent-pink transition-colors group-hover:border-cypher-accent-pink/40 group-hover:bg-cypher-accent-pink/20" aria-hidden="true">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0113.5 9.375v-4.5z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 6.75h.75v.75h-.75v-.75zM6.75 16.5h.75v.75h-.75V16.5zM16.5 6.75h.75v.75h-.75v-.75zM13.5 13.5h.75v.75h-.75v-.75zM13.5 19.5h.75v.75h-.75v-.75zM19.5 13.5h.75v.75h-.75v-.75zM19.5 19.5h.75v.75h-.75v-.75zM16.5 16.5h.75v.75h-.75v-.75z" />
              </svg>
            </span>
            <span class="text-sm font-medium text-gray-300 transition-colors group-hover:text-white">核銷介面</span>
          </router-link>
        </div>
      </div>

      <!-- Current org indicator -->
      <p v-if="organizerStore.orgId" class="mt-5 text-center text-xs text-cypher-muted">
        已選取主辦方：<code class="rounded bg-cypher-surface-alt px-1.5 py-0.5 font-mono text-xs tracking-wider text-gray-400">{{ organizerStore.orgId.slice(0, 8).toUpperCase() }}…</code>
      </p>

    </div>
  </main>
</template>
