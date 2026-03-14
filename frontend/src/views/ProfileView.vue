<script setup lang="ts">
import { ref, watch } from "vue";
import { useRouter } from "vue-router";

import { supabase } from "../api/supabase";
import { useAuthStore } from "../stores/auth";

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
const loading = ref(true);
const saving = ref(false);
const errorMessage = ref<string | null>(null);
const message = ref<string | null>(null);

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
    }
  } catch (e: unknown) {
    errorMessage.value = (e as { message?: string })?.message ?? "無法載入個人資料";
  } finally {
    loading.value = false;
  }
}

watch(
  () => authStore.initialized,
  (initialized) => {
    if (initialized && authStore.isAuthenticated) loadOrCreateProfile();
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
    const { error } = await supabase
      .from("profiles")
      .update({
        display_name: name,
        phone: phone.value.trim() || null,
      })
      .eq("id", profile.value.id);

    if (error) throw error;
    profile.value = { ...profile.value, display_name: name, phone: phone.value.trim() || null };
    message.value = "已儲存。";
  } catch (e: unknown) {
    errorMessage.value = (e as { message?: string })?.message ?? "儲存失敗";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <main class="mx-auto max-w-lg px-4 py-10">
    <h1 class="text-2xl font-bold text-slate-900">個人資料</h1>
    <p class="mt-2 text-sm text-slate-600">編輯顯示名稱與聯絡方式（頭像可於之後版本上傳）。</p>

    <div v-if="loading" class="mt-6 text-slate-500">載入中…</div>

    <div v-else-if="profile" class="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">顯示名稱 *</label>
        <input
          v-model="displayName"
          type="text"
          placeholder="您的暱稱"
          class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">手機</label>
        <input
          v-model="phone"
          type="tel"
          placeholder="選填"
          class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
      </div>

      <p v-if="message" class="text-sm text-emerald-700">{{ message }}</p>
      <p v-if="errorMessage" class="text-sm text-rose-700">{{ errorMessage }}</p>

      <button
        type="button"
        class="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        :disabled="saving"
        @click="save"
      >
        {{ saving ? "儲存中…" : "儲存" }}
      </button>
    </div>

    <p v-else class="mt-6 text-slate-500">請先登入。</p>
  </main>
</template>
