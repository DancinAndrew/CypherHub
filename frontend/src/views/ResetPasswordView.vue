<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";
import { toAuthErrorMessage } from "../utils/errorMessages";

const router = useRouter();
const authStore = useAuthStore();

const newPassword = ref("");
const confirmPassword = ref("");
const loading = ref(false);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

async function submit(): Promise<void> {
  errorMessage.value = null;
  successMessage.value = null;

  const pwd = newPassword.value;
  const confirm = confirmPassword.value;

  if (pwd.length < 6) {
    errorMessage.value = "密碼長度至少 6 個字元。";
    return;
  }
  if (pwd !== confirm) {
    errorMessage.value = "兩次輸入的密碼不一致。";
    return;
  }

  loading.value = true;
  try {
    await authStore.updatePassword(pwd);
    successMessage.value = "密碼已更新，正在導向首頁…";
    setTimeout(() => router.push({ name: "home" }), 1500);
  } catch (error: unknown) {
    errorMessage.value = toAuthErrorMessage(error, "signin");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="mx-auto flex min-h-[70vh] w-full max-w-md items-center px-4 py-10">
    <section class="w-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h1 class="text-2xl font-bold text-slate-900">設定新密碼</h1>
      <p class="mt-2 text-sm text-slate-600">
        請輸入新密碼（至少 6 個字元）。若您是從重設密碼信點連結進來，已自動登入。
      </p>

      <form class="mt-6 space-y-4" @submit.prevent="submit">
        <label class="block">
          <span class="mb-1 block text-sm text-slate-700">新密碼</span>
          <input
            v-model="newPassword"
            type="password"
            minlength="6"
            autocomplete="new-password"
            placeholder="至少 6 個字元"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-sm text-slate-700">再輸入一次</span>
          <input
            v-model="confirmPassword"
            type="password"
            minlength="6"
            autocomplete="new-password"
            placeholder="再輸入一次新密碼"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </label>
        <button
          type="submit"
          class="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          :disabled="loading"
        >
          {{ loading ? "處理中…" : "更新密碼" }}
        </button>
      </form>

      <p v-if="successMessage" class="mt-4 text-sm text-emerald-700">{{ successMessage }}</p>
      <p v-if="errorMessage" class="mt-4 text-sm text-rose-700">{{ errorMessage }}</p>

      <router-link to="/login" class="mt-4 inline-block text-sm text-slate-500 hover:text-brand-600">
        ← 返回登入
      </router-link>
    </section>
  </main>
</template>
