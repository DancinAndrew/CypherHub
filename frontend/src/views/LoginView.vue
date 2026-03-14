<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";
import { toAuthErrorMessage } from "../utils/errorMessages";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const mode = ref<"signin" | "signup">("signin");
const email = ref("");
const password = ref("");
const loading = ref(false);
const errorMessage = ref<string | null>(null);
const infoMessage = ref<string | null>(null);

const title = computed(() => (mode.value === "signin" ? "Sign In" : "Sign Up"));
const emailHelp = "請輸入有效 Email（例如 name@example.com）";
const passwordHelp = "密碼至少 6 個字元";

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function validateForm(): string | null {
  const normalizedEmail = email.value.trim().toLowerCase();
  const pwd = password.value;

  if (!isValidEmail(normalizedEmail)) {
    errorMessage.value = "Email 格式不正確，請輸入有效信箱（例如 name@example.com）。";
    return null;
  }
  if (pwd.length < 6) {
    errorMessage.value = "密碼長度不足，至少需要 6 個字元。";
    return null;
  }

  return normalizedEmail;
}

async function submit(): Promise<void> {
  const normalizedEmail = validateForm();
  if (!normalizedEmail) {
    return;
  }

  loading.value = true;
  errorMessage.value = null;
  infoMessage.value = null;

  try {
    if (mode.value === "signin") {
      await authStore.signIn(normalizedEmail, password.value);
    } else {
      const result = await authStore.signUp(normalizedEmail, password.value);
      if (result.requiresEmailConfirmation) {
        infoMessage.value = `註冊成功。此專案目前需要 Email 驗證，請先到 ${result.email} 收信並點擊確認連結，再回來 Sign In。`;
        mode.value = "signin";
        return;
      }
    }

    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
    await router.push(redirect);
  } catch (error: unknown) {
    errorMessage.value = toAuthErrorMessage(error, mode.value);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="mx-auto flex min-h-[70vh] w-full max-w-md items-center px-4 py-10">
    <section class="w-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h1 class="text-2xl font-bold text-slate-900">{{ title }}</h1>
      <p class="mt-2 text-sm text-slate-600">Use Supabase Auth email/password.</p>
      <div class="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
        <p>{{ emailHelp }}</p>
        <p>{{ passwordHelp }}</p>
        <p>Sign Up 可能受 Supabase rate limit 影響（短時間內多次註冊會被暫時拒絕）。</p>
      </div>

      <form class="mt-6 space-y-4" @submit.prevent="submit">
        <label class="block">
          <span class="mb-1 block text-sm text-slate-700">Email</span>
          <input
            v-model="email"
            required
            type="email"
            inputmode="email"
            autocomplete="email"
            placeholder="name@example.com"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </label>

        <label class="block">
          <span class="mb-1 block text-sm text-slate-700">Password</span>
          <input
            v-model="password"
            required
            type="password"
            minlength="6"
            autocomplete="current-password"
            placeholder="At least 6 characters"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </label>

        <button
          type="submit"
          class="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          :disabled="loading"
        >
          {{ loading ? "Please wait..." : title }}
        </button>
      </form>

      <p v-if="infoMessage" class="mt-4 text-sm text-emerald-700">{{ infoMessage }}</p>
      <p v-if="errorMessage" class="mt-4 text-sm text-rose-700">{{ errorMessage }}</p>

      <button
        type="button"
        class="mt-4 text-sm font-medium text-brand-700 hover:text-brand-800"
        @click="
          mode = mode === 'signin' ? 'signup' : 'signin';
          errorMessage = null;
          infoMessage = null;
        "
      >
        {{ mode === "signin" ? "Need an account? Sign up" : "Have an account? Sign in" }}
      </button>
    </section>
  </main>
</template>
