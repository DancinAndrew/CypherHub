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
  <main class="mx-auto flex min-h-[70vh] w-full max-w-md items-center px-4 py-12 animate-fade-in">
    <section class="card w-full p-8">
      <h1 class="font-display text-2xl font-bold text-gray-900">設定新密碼</h1>
      <p class="mt-2 text-sm text-gray-600">
        請輸入新密碼（至少 6 個字元）。若您是從重設密碼信點連結進來，已自動登入。
      </p>

      <form class="mt-6 space-y-4" @submit.prevent="submit">
        <label class="block">
          <span class="mb-2 block text-sm font-medium text-gray-700">新密碼</span>
          <input
            v-model="newPassword"
            type="password"
            minlength="6"
            autocomplete="new-password"
            placeholder="至少 6 個字元"
            class="input-field"
          />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm font-medium text-gray-700">再輸入一次</span>
          <input
            v-model="confirmPassword"
            type="password"
            minlength="6"
            autocomplete="new-password"
            placeholder="再輸入一次新密碼"
            class="input-field"
          />
        </label>
        <button type="submit" class="btn-primary w-full py-3" :disabled="loading">
          {{ loading ? "處理中…" : "更新密碼" }}
        </button>
      </form>

      <p v-if="successMessage" role="alert" class="mt-4 rounded-lg bg-emerald-100 px-4 py-2 text-sm text-emerald-700">
        {{ successMessage }}
      </p>
      <p v-if="errorMessage" role="alert" class="mt-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">
        {{ errorMessage }}
      </p>

      <router-link
        to="/login"
        class="link-back mt-4 inline-block"
      >
        ← 返回登入
      </router-link>
    </section>
  </main>
</template>
