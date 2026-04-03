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
  <main class="relative flex min-h-[calc(100vh-4rem)] w-full items-center justify-center overflow-hidden px-4 py-12">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="absolute inset-0 bg-gradient-radial-purple" aria-hidden="true" />

    <!-- Card -->
    <section class="animate-slide-up relative z-10 w-full max-w-md">
      <!-- Glow ring behind card -->
      <div class="absolute -inset-px rounded-2xl bg-gradient-to-br from-cypher-accent/30 via-transparent to-cypher-accent-pink/20 blur-sm" aria-hidden="true" />

      <div class="relative rounded-2xl border border-white/10 bg-cypher-surface/90 p-8 shadow-card-glass backdrop-blur-md">

        <!-- Header -->
        <div class="mb-7">
          <!-- Mode indicator pills -->
          <div v-if="mode !== 'forgot'" class="mb-5 flex rounded-xl border border-cypher-border bg-cypher-bg/60 p-1">
            <button
              type="button"
              class="flex-1 cursor-pointer rounded-lg py-2 text-sm font-semibold transition-all duration-200"
              :class="mode === 'signin'
                ? 'bg-cypher-accent text-white shadow-glow-sm'
                : 'text-gray-400 hover:text-white'"
              @click="mode = 'signin'; errorMessage = null; infoMessage = null"
            >
              登入
            </button>
            <button
              type="button"
              class="flex-1 cursor-pointer rounded-lg py-2 text-sm font-semibold transition-all duration-200"
              :class="mode === 'signup'
                ? 'bg-cypher-accent text-white shadow-glow-sm'
                : 'text-gray-400 hover:text-white'"
              @click="mode = 'signup'; errorMessage = null; infoMessage = null"
            >
              註冊
            </button>
          </div>

          <div class="flex items-center gap-3">
            <span class="h-5 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
            <h1 class="font-street text-2xl tracking-widest text-white">
              {{ mode === 'forgot' ? '重設密碼' : mode === 'signin' ? '歡迎回來' : '加入我們' }}
            </h1>
          </div>
          <p class="mt-1.5 pl-3.5 text-sm text-cypher-muted">
            {{ mode === 'forgot' ? '輸入 Email 收取重設連結' : 'Email · 密碼' }}
          </p>
        </div>

        <!-- Form -->
        <form class="space-y-4" @submit.prevent="submit">
          <div>
            <label for="login-email" class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">
              Email
            </label>
            <input
              id="login-email"
              v-model="email"
              required
              type="email"
              inputmode="email"
              autocomplete="email"
              placeholder="name@example.com"
              class="input-field"
            />
          </div>

          <div v-if="mode !== 'forgot'">
            <div class="mb-2 flex items-center justify-between">
              <label for="login-password" class="text-xs font-semibold uppercase tracking-widest text-cypher-muted">
                密碼
              </label>
              <button
                v-if="mode === 'signin'"
                type="button"
                class="cursor-pointer text-xs text-cypher-muted transition-colors hover:text-cypher-accent"
                @click="mode = 'forgot'; errorMessage = null; infoMessage = null"
              >
                忘記密碼？
              </button>
            </div>
            <input
              id="login-password"
              v-model="password"
              required
              type="password"
              minlength="6"
              :autocomplete="mode === 'signin' ? 'current-password' : 'new-password'"
              placeholder="至少 6 個字元"
              class="input-field"
            />
            <p v-if="mode === 'signup'" class="mt-1.5 text-xs text-cypher-muted">{{ passwordHelp }}</p>
          </div>

          <!-- Submit -->
          <button type="submit" class="btn-primary w-full py-3.5 text-base" :disabled="loading">
            <span v-if="loading" class="flex items-center justify-center gap-2">
              <span class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              處理中...
            </span>
            <span v-else>
              {{ mode === 'forgot' ? '寄送重設密碼信' : mode === 'signin' ? '登入' : '建立帳號' }}
            </span>
          </button>
        </form>

        <!-- Alerts -->
        <Transition
          enter-active-class="transition-all duration-200 ease-out"
          enter-from-class="opacity-0 -translate-y-1"
          enter-to-class="opacity-100 translate-y-0"
        >
          <div v-if="infoMessage" role="alert" class="mt-4 flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
            <svg class="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-sm text-emerald-400">{{ infoMessage }}</p>
          </div>
        </Transition>

        <Transition
          enter-active-class="transition-all duration-200 ease-out"
          enter-from-class="opacity-0 -translate-y-1"
          enter-to-class="opacity-100 translate-y-0"
        >
          <div v-if="errorMessage" role="alert" class="mt-4 flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3">
            <svg class="mt-0.5 h-4 w-4 shrink-0 text-rose-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <p class="text-sm text-rose-400">{{ errorMessage }}</p>
          </div>
        </Transition>

        <!-- Back to signin (forgot mode) -->
        <button
          v-if="mode === 'forgot'"
          type="button"
          class="mt-5 flex cursor-pointer items-center gap-1.5 text-sm text-cypher-muted transition-colors hover:text-cypher-accent"
          @click="mode = 'signin'; errorMessage = null; infoMessage = null"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          返回登入
        </button>
      </div>
    </section>
  </main>
</template>
