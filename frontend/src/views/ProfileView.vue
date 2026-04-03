<script setup lang="ts">
import { ref, watch } from "vue";
import { useRouter } from "vue-router";

import { fetchMyOrganizerSummary, type MyOrganizerEvent, type MyOrganizerOrg } from "../api/client";
import { supabase } from "../api/supabase";
import { useAuthStore } from "../stores/auth";
import { toApiErrorMessage } from "../utils/errorMessages";

export type ProfileRow = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  phone: string | null;
  social_links: Record<string, string> | null;
  created_at?: string;
  updated_at?: string;
};

const router = useRouter();
const authStore = useAuthStore();

const profile = ref<ProfileRow | null>(null);
const displayName = ref("");
const phone = ref("");
const socialInstagram = ref("");
const socialFacebook = ref("");
const loading = ref(true);
const saving = ref(false);
const errorMessage = ref<string | null>(null);
const message = ref<string | null>(null);

const organizations = ref<MyOrganizerOrg[]>([]);
const events = ref<MyOrganizerEvent[]>([]);
const organizerSummaryLoading = ref(false);
const organizerSummaryError = ref<string | null>(null);

async function loadOrCreateProfile(): Promise<void> {
  const user = authStore.user;
  if (!user?.id) {
    router.push({ name: "login", query: { redirect: "/profile" } });
    return;
  }

  loading.value = true;
  errorMessage.value = null;
  try {
    const { data, error } = await supabase
      .from("profiles")
      .select("id, display_name, avatar_url, phone, social_links, created_at, updated_at")
      .eq("id", user.id)
      .maybeSingle();

    if (error) throw error;

    if (data) {
      profile.value = data as ProfileRow;
      displayName.value = data.display_name ?? "";
      phone.value = data.phone ?? "";
      const sl = (data.social_links as Record<string, string> | null) ?? {};
      socialInstagram.value = sl.instagram ?? sl.Instagram ?? "";
      socialFacebook.value = sl.facebook ?? sl.Facebook ?? "";
    } else {
      const displayNameDefault = user.email?.split("@")[0]?.trim() || "User";
      const { data: inserted, error: insertError } = await supabase
        .from("profiles")
        .insert({
          id: user.id,
          display_name: displayNameDefault,
          avatar_url: null,
          phone: null,
          social_links: null,
        })
        .select()
        .single();

      if (insertError) throw insertError;
      profile.value = inserted as ProfileRow;
      displayName.value = displayNameDefault;
      phone.value = "";
      socialInstagram.value = "";
      socialFacebook.value = "";
    }
  } catch (e: unknown) {
    errorMessage.value = (e as { message?: string })?.message ?? "無法載入個人資料";
  } finally {
    loading.value = false;
  }
}

async function loadOrganizerSummary(): Promise<void> {
  organizerSummaryError.value = null;
  organizerSummaryLoading.value = true;
  try {
    const data = await fetchMyOrganizerSummary();
    organizations.value = data.organizations ?? [];
    events.value = data.events ?? [];
  } catch (e: unknown) {
    organizerSummaryError.value = toApiErrorMessage(e, "無法載入主辦方資訊");
    organizations.value = [];
    events.value = [];
  } finally {
    organizerSummaryLoading.value = false;
  }
}

function formatEventDate(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString(undefined, { dateStyle: "short" });
}

function roleLabel(role: string): string {
  const map: Record<string, string> = { owner: "負責人", admin: "管理員", staff: "工作人員" };
  return map[role] ?? role;
}

watch(
  () => authStore.initialized,
  (initialized) => {
    if (initialized && authStore.isAuthenticated) {
      loadOrCreateProfile();
      loadOrganizerSummary();
    }
  },
  { immediate: true },
);

async function save(): Promise<void> {
  if (!profile.value?.id) return;

  const name = displayName.value.trim();
  if (!name) {
    errorMessage.value = "顯示名稱不可為空。";
    return;
  }

  saving.value = true;
  errorMessage.value = null;
  message.value = null;
  try {
    const socialLinks: Record<string, string> = {};
    if (socialInstagram.value.trim()) socialLinks.instagram = socialInstagram.value.trim();
    if (socialFacebook.value.trim()) socialLinks.facebook = socialFacebook.value.trim();

    const { error } = await supabase
      .from("profiles")
      .update({
        display_name: name,
        phone: phone.value.trim() || null,
        social_links: Object.keys(socialLinks).length ? socialLinks : null,
      })
      .eq("id", profile.value.id);

    if (error) throw error;
    profile.value = {
      ...profile.value,
      display_name: name,
      phone: phone.value.trim() || null,
      social_links: Object.keys(socialLinks).length ? socialLinks : null,
    };
    message.value = "已儲存。";
  } catch (e: unknown) {
    errorMessage.value = (e as { message?: string })?.message ?? "儲存失敗";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <main class="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden px-4 pb-20 pt-10">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="pointer-events-none absolute inset-0" style="background: radial-gradient(ellipse 50% 40% at 20% 0%, rgba(124,58,237,0.10) 0%, transparent 70%)" aria-hidden="true" />

    <div class="relative z-10 mx-auto w-full max-w-lg">

      <!-- Header -->
      <header class="animate-slide-up mb-8">
        <p class="section-label mb-2">Profile</p>
        <div class="flex items-center gap-3">
          <span class="h-6 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
          <h1 class="font-street text-2xl tracking-widest text-white">個人資料</h1>
        </div>
        <p class="mt-2 pl-3.5 text-sm text-cypher-muted">編輯顯示名稱與聯絡方式</p>
      </header>

      <!-- Loading -->
      <div v-if="loading" class="card-glass flex items-center justify-center gap-3 p-12 text-cypher-muted">
        <span class="h-5 w-5 animate-spin rounded-full border-2 border-cypher-accent border-t-transparent" aria-hidden="true" />
        <span class="text-sm">載入中…</span>
      </div>

      <!-- Not authenticated -->
      <p v-else-if="!authStore.isAuthenticated" class="text-sm text-cypher-muted">請先登入。</p>

      <!-- Profile form -->
      <div v-else-if="profile" class="animate-slide-up space-y-5">

        <!-- Avatar + email display -->
        <div class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 p-6 shadow-card-glass backdrop-blur-md">
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/40 to-transparent" aria-hidden="true" />
          <div class="flex items-center gap-4">
            <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-cypher-accent/30 bg-gradient-to-br from-cypher-accent to-cypher-accent-pink text-xl font-bold text-white shadow-glow-sm">
              {{ authStore.user?.email?.charAt(0).toUpperCase() ?? '?' }}
            </div>
            <div>
              <p class="font-semibold text-white">{{ profile.display_name || '—' }}</p>
              <p class="mt-0.5 text-sm text-cypher-muted">{{ authStore.user?.email }}</p>
            </div>
          </div>
        </div>

        <!-- Edit form -->
        <div class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 p-6 shadow-card-glass backdrop-blur-md">
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/30 to-transparent" aria-hidden="true" />

          <h2 class="mb-5 text-sm font-semibold text-white">基本資訊</h2>

          <div class="space-y-4">
            <div>
              <label for="profile-display-name" class="mb-1.5 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">
                顯示名稱 <span class="text-cypher-accent">*</span>
              </label>
              <input
                id="profile-display-name"
                v-model="displayName"
                type="text"
                placeholder="您的暱稱"
                class="input-field"
              />
            </div>
            <div>
              <label for="profile-phone" class="mb-1.5 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">
                手機（選填）
              </label>
              <input
                id="profile-phone"
                v-model="phone"
                type="tel"
                placeholder="例如 0912-345-678"
                class="input-field"
              />
            </div>
          </div>

          <div class="my-5 h-px bg-white/5" />

          <h2 class="mb-4 text-sm font-semibold text-white">社群連結</h2>
          <div class="space-y-4">
            <div>
              <label for="profile-instagram" class="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-cypher-muted">
                <svg class="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                </svg>
                Instagram
              </label>
              <input
                id="profile-instagram"
                v-model="socialInstagram"
                type="url"
                placeholder="https://instagram.com/yourhandle"
                class="input-field"
              />
            </div>
            <div>
              <label for="profile-facebook" class="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-cypher-muted">
                <svg class="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                Facebook
              </label>
              <input
                id="profile-facebook"
                v-model="socialFacebook"
                type="url"
                placeholder="https://facebook.com/yourpage"
                class="input-field"
              />
            </div>
          </div>

          <!-- Alerts -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
          >
            <div v-if="message" class="mt-4 flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
              <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {{ message }}
            </div>
          </Transition>
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
          >
            <div v-if="errorMessage" class="mt-4 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
              <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              {{ errorMessage }}
            </div>
          </Transition>

          <button
            type="button"
            class="btn-primary mt-5 w-full py-3"
            :disabled="saving"
            @click="save"
          >
            <span v-if="saving" class="flex items-center justify-center gap-2">
              <span class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" aria-hidden="true" />
              儲存中…
            </span>
            <span v-else>儲存變更</span>
          </button>
        </div>

        <!-- Organizer section -->
        <template v-if="authStore.isAuthenticated">

          <!-- My organizations -->
          <div class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md" style="animation: slideUp 0.5s ease-out 0.1s both">
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-cyan/30 to-transparent" aria-hidden="true" />
            <div class="border-b border-white/5 px-6 py-4">
              <h2 class="text-sm font-semibold text-white">主辦方帳號</h2>
            </div>
            <div class="p-6">
              <div v-if="organizerSummaryLoading" class="flex items-center gap-2 text-sm text-cypher-muted">
                <span class="h-4 w-4 animate-spin rounded-full border border-cypher-accent border-t-transparent" aria-hidden="true" />
                載入中…
              </div>
              <p v-else-if="organizerSummaryError" class="text-sm text-rose-400">{{ organizerSummaryError }}</p>
              <div v-else-if="organizations.length === 0" class="flex flex-col items-center gap-3 py-4 text-center">
                <p class="text-sm text-gray-400">尚無主辦方帳號</p>
                <router-link to="/organizer/apply" class="text-sm font-medium text-cypher-accent transition-colors hover:text-cypher-accent-pink">
                  立即申請 →
                </router-link>
              </div>
              <ul v-else class="space-y-2">
                <li
                  v-for="(org, i) in organizations"
                  :key="org.id"
                  class="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3 text-sm"
                  :style="`animation: slideUp 0.4s ease-out ${i * 0.05}s both`"
                >
                  <span class="font-medium text-white">{{ org.name }}</span>
                  <span class="badge-dance">{{ roleLabel(org.role) }}</span>
                </li>
              </ul>
              <router-link
                v-if="organizations.length > 0"
                to="/organizer"
                class="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-cypher-accent transition-colors hover:text-cypher-accent-pink"
              >
                前往主辦方後台
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </router-link>
            </div>
          </div>

          <!-- My events -->
          <div class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md" style="animation: slideUp 0.5s ease-out 0.15s both">
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-pink/30 to-transparent" aria-hidden="true" />
            <div class="border-b border-white/5 px-6 py-4">
              <h2 class="text-sm font-semibold text-white">主辦活動</h2>
            </div>
            <div class="p-6">
              <p v-if="organizerSummaryLoading" class="text-sm text-cypher-muted">載入中…</p>
              <div v-else-if="events.length === 0" class="text-sm text-gray-400">尚無活動，或您尚未加入任何主辦方。</div>
              <ul v-else class="space-y-2">
                <li
                  v-for="(ev, i) in events"
                  :key="ev.id"
                  class="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3 text-sm"
                  :style="`animation: slideUp 0.4s ease-out ${i * 0.05}s both`"
                >
                  <div class="min-w-0 flex-1">
                    <router-link
                      :to="{ name: 'event-detail', params: { eventId: ev.id } }"
                      class="block truncate font-medium text-white transition-colors hover:text-cypher-accent"
                    >
                      {{ ev.title }}
                    </router-link>
                    <p class="mt-0.5 text-xs text-cypher-muted">{{ formatEventDate(ev.start_at) }}</p>
                  </div>
                  <span
                    class="ml-3 shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold"
                    :class="ev.status === 'published'
                      ? 'border-cypher-accent-cyan/40 bg-cypher-accent-cyan/10 text-cypher-accent-cyan'
                      : 'border-white/10 bg-white/5 text-cypher-muted'"
                  >
                    {{ ev.status === 'published' ? '已上架' : '草稿' }}
                  </span>
                </li>
              </ul>
              <router-link
                v-if="events.length > 0"
                to="/organizer"
                class="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-cypher-accent transition-colors hover:text-cypher-accent-pink"
              >
                管理活動
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </router-link>
            </div>
          </div>

        </template>
      </div>

    </div>
  </main>
</template>
