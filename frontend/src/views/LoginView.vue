<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";
import { toAuthErrorMessage } from "../utils/errorMessages";
import { sanitizeRedirect } from "../utils/sanitizeRedirect";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const mode = ref<"signin" | "signup" | "forgot">("signin");
const email = ref("");
const password = ref("");
const loading = ref(false);
const errorMessage = ref<string | null>(null);
const infoMessage = ref<string | null>(null);

const title = computed(() =>
  mode.value === "signin" ? "Sign In" : mode.value === "signup" ? "Sign Up" : "忘記密碼",
);
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
  if (mode.value !== "forgot" && pwd.length < 6) {
    errorMessage.value = "密碼長度不足，至少需要 6 個字元。";
    return null;
  }

  return normalizedEmail;
}

async function submitForgotPassword(): Promise<void> {
  const normalizedEmail = validateForm();
  if (!normalizedEmail) return;

  loading.value = true;
  errorMessage.value = null;
  infoMessage.value = null;
  try {
    await authStore.resetPasswordForEmail(normalizedEmail);
    infoMessage.value = `已寄送重設密碼信至 ${normalizedEmail}，請到信箱點擊連結並設定新密碼。`;
  } catch (error: unknown) {
    errorMessage.value = toAuthErrorMessage(error, "forgot");
  } finally {
    loading.value = false;
  }
}

async function submit(): Promise<void> {
  if (mode.value === "forgot") {
    await submitForgotPassword();
    return;
  }

  const normalizedEmail = validateForm();
  if (!normalizedEmail) return;

  loading.value = true;
  errorMessage.value = null;
  infoMessage.value = null;

  try {
    if (mode.value === "signin") {
      await authStore.signIn(normalizedEmail, password.value.trim());
    } else {
      const result = await authStore.signUp(normalizedEmail, password.value.trim());
      if (result.requiresEmailConfirmation) {
        infoMessage.value = `註冊成功。此專案目前需要 Email 驗證，請先到 ${result.email} 收信並點擊確認連結，再回來 Sign In。`;
        mode.value = "signin";
        return;
      }
    }

    const redirect = sanitizeRedirect(route.query.redirect);
    await router.push(redirect);
  } catch (error: unknown) {
    errorMessage.value = toAuthErrorMessage(error, mode.value);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="mx-auto flex min-h-[70vh] w-full max-w-md items-center px-4 py-12 animate-fade-in">
    <section class="card w-full p-8">
      <h1 class="font-street text-3xl tracking-widest text-white">{{ title }}</h1>
      <p class="mt-2 text-sm text-cypher-muted">Email / 密碼登入</p>
      <div class="mt-4 rounded-xl border border-cypher-border bg-cypher-surface-alt/50 p-4 text-xs text-gray-400">
        <p>{{ emailHelp }}</p>
        <p>{{ passwordHelp }}</p>
      </div>

      <form class="mt-6 space-y-4" @submit.prevent="submit">
        <label class="block">
          <span class="mb-2 block text-sm font-medium text-gray-300">Email</span>
          <input
            v-model="email"
            required
            type="email"
            inputmode="email"
            autocomplete="email"
            placeholder="name@example.com"
            class="input-field"
          />
        </label>

        <label v-if="mode !== 'forgot'" class="block">
          <span class="mb-2 block text-sm font-medium text-gray-300">Password</span>
          <input
            v-model="password"
            required
            type="password"
            minlength="6"
            :autocomplete="mode === 'signin' ? 'current-password' : 'new-password'"
            placeholder="至少 6 個字元"
            class="input-field"
          />
        </label>

        <button type="submit" class="btn-primary w-full py-3" :disabled="loading">
          {{ loading ? "處理中..." : mode === "forgot" ? "寄送重設密碼信" : title }}
        </button>
      </form>

      <p v-if="mode !== 'forgot'" class="mt-3 text-right">
        <button
          type="button"
          class="text-sm text-cypher-muted transition-colors hover:text-cypher-accent"
          @click="
            mode = 'forgot';
            errorMessage = null;
            infoMessage = null;
          "
        >
          忘記密碼？
        </button>
      </p>

      <p v-if="infoMessage" role="alert" class="mt-4 rounded-xl bg-emerald-500/20 px-4 py-2 text-sm text-emerald-400">
        {{ infoMessage }}
      </p>
      <p v-if="errorMessage" role="alert" class="mt-4 rounded-xl bg-rose-500/20 px-4 py-2 text-sm text-rose-400">
        {{ errorMessage }}
      </p>

      <button
        v-if="mode !== 'forgot'"
        type="button"
        class="mt-4 text-sm font-medium text-cypher-accent transition-colors hover:text-cypher-accent-pink"
        @click="
          mode = mode === 'signin' ? 'signup' : 'signin';
          errorMessage = null;
          infoMessage = null;
        "
      >
        {{ mode === "signin" ? "還沒有帳號？註冊" : "已有帳號？登入" }}
      </button>
      <button
        v-else
        type="button"
        class="mt-4 text-sm font-medium text-cypher-muted transition-colors hover:text-cypher-accent link-back"
        @click="
          mode = 'signin';
          errorMessage = null;
          infoMessage = null;
        "
      >
        ← 返回登入
      </button>
    </section>
  </main>
</template>
