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
  <main class="mx-auto max-w-lg px-4 py-12">
    <h1 class="font-street text-3xl tracking-widest text-white">個人資料</h1>
    <p class="mt-2 text-sm text-cypher-muted">編輯顯示名稱與聯絡方式（頭像可於之後版本上傳）。</p>

    <div v-if="loading" class="mt-6 animate-pulse text-cypher-muted">載入中…</div>

    <div v-else-if="profile" class="card mt-6 space-y-4 p-6">
      <div>
        <label class="mb-1 block text-sm font-medium text-gray-300">顯示名稱 *</label>
        <input
          v-model="displayName"
          type="text"
          placeholder="您的暱稱"
          class="input-field"
        />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium text-gray-300">手機</label>
        <input
          v-model="phone"
          type="tel"
          placeholder="選填"
          class="input-field"
        />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium text-gray-300">Instagram</label>
        <input
          v-model="socialInstagram"
          type="url"
          placeholder="https://instagram.com/..."
          class="input-field"
        />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium text-gray-300">Facebook</label>
        <input
          v-model="socialFacebook"
          type="url"
          placeholder="https://facebook.com/..."
          class="input-field"
        />
      </div>

      <p v-if="message" class="text-sm text-emerald-400">{{ message }}</p>
      <p v-if="errorMessage" class="text-sm text-rose-400">{{ errorMessage }}</p>

      <button
        type="button"
        class="btn-primary w-full disabled:opacity-50"
        :disabled="saving"
        @click="save"
      >
        {{ saving ? "儲存中…" : "儲存" }}
      </button>
    </div>

    <template v-if="authStore.isAuthenticated && !loading">
      <section class="card mt-8 p-6">
        <h2 class="font-street text-lg tracking-wider text-white">主辦方帳號</h2>
        <p v-if="organizerSummaryLoading" class="mt-3 text-sm text-cypher-muted">載入中…</p>
        <p v-else-if="organizerSummaryError" class="mt-3 text-sm text-rose-400">{{ organizerSummaryError }}</p>
        <div v-else-if="organizations.length === 0" class="mt-3 text-sm text-gray-400">尚無主辦方帳號。可至主辦方申請頁建立。</div>
        <ul v-else class="mt-3 space-y-2">
          <li
            v-for="org in organizations"
            :key="org.id"
            class="flex items-center justify-between rounded-xl border border-cypher-border px-3 py-2 text-sm"
          >
            <span class="font-medium text-white">{{ org.name }}</span>
            <span class="badge-dance">{{ roleLabel(org.role) }}</span>
          </li>
        </ul>
        <router-link
          v-if="organizations.length > 0"
          to="/organizer"
          class="mt-3 inline-block text-sm font-medium text-cypher-accent transition-colors hover:text-cypher-accent-pink"
        >
          前往主辦方後台 →
        </router-link>
      </section>

      <section class="card mt-6 p-6">
        <h2 class="font-street text-lg tracking-wider text-white">主辦方底下的活動</h2>
        <p v-if="organizerSummaryLoading" class="mt-3 text-sm text-cypher-muted">載入中…</p>
        <div v-else-if="events.length === 0" class="mt-3 text-sm text-gray-400">尚無活動，或您尚未加入任何主辦方。</div>
        <ul v-else class="mt-3 space-y-2">
          <li
            v-for="ev in events"
            :key="ev.id"
            class="rounded-xl border border-cypher-border px-3 py-2 text-sm"
          >
            <router-link :to="{ name: 'event-detail', params: { eventId: ev.id } }" class="font-medium text-cypher-accent transition-colors hover:text-cypher-accent-pink">
              {{ ev.title }}
            </router-link>
            <span class="ml-2 text-cypher-muted">{{ formatEventDate(ev.start_at) }}</span>
            <span class="ml-2 rounded px-1.5 py-0.5 text-xs" :class="ev.status === 'published' ? 'badge-type' : 'bg-cypher-surface-alt text-cypher-muted'">
              {{ ev.status === "published" ? "已上架" : "草稿" }}
            </span>
          </li>
        </ul>
        <router-link
          v-if="events.length > 0"
          to="/organizer"
          class="mt-3 inline-block text-sm font-medium text-cypher-accent transition-colors hover:text-cypher-accent-pink"
        >
          管理活動 →
        </router-link>
      </section>
    </template>

    <p v-if="!loading && !profile && !authStore.isAuthenticated" class="mt-6 text-cypher-muted">請先登入。</p>
  </main>
</template>
