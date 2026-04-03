<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { organizerApply } from "../../api/client";
import { useOrganizerStore } from "../../stores/organizer";
import { toApiErrorMessage } from "../../utils/errorMessages";

const router = useRouter();
const organizerStore = useOrganizerStore();

const form = ref({
  name: "",
  description: "",
  contact_email: "",
  logo_url: "",
});
const message = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const submitting = ref(false);

function optionalText(value: string | undefined): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

async function submit() {
  message.value = null;
  errorMessage.value = null;

  const orgName = form.value.name.trim();
  const contactEmail = form.value.contact_email.trim();

  if (!orgName) {
    errorMessage.value = "主辦方名稱為必填。";
    return;
  }
  if (contactEmail && !isValidEmail(contactEmail)) {
    errorMessage.value = "聯絡信箱格式不正確。";
    return;
  }

  submitting.value = true;
  try {
    const result = await organizerApply({
      name: orgName,
      description: optionalText(form.value.description),
      contact_email: contactEmail || undefined,
      logo_url: optionalText(form.value.logo_url),
    });
    organizerStore.setOrgId(result.organization.id);
    message.value = `主辦方建立成功！org_id: ${result.organization.id}`;
    setTimeout(() => router.push({ name: "organizer-event-create" }), 1500);
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "申請主辦方失敗。");
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden px-4 pb-20 pt-10">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="pointer-events-none absolute inset-0" style="background: radial-gradient(ellipse 60% 50% at 50% -10%, rgba(124,58,237,0.15) 0%, transparent 70%)" aria-hidden="true" />

    <div class="relative z-10 mx-auto w-full max-w-lg">

      <!-- Back link -->
      <div class="mb-8 animate-fade-in">
        <router-link
          to="/organizer"
          class="inline-flex items-center gap-1.5 text-sm text-cypher-muted transition-colors hover:text-cypher-accent"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          回主辦方主頁
        </router-link>
      </div>

      <!-- Page header -->
      <div class="mb-8 animate-slide-up">
        <p class="section-label mb-2">Step 1</p>
        <div class="flex items-center gap-3">
          <span class="h-6 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
          <h1 class="font-street text-2xl tracking-widest text-white">申請成為主辦方</h1>
        </div>
        <p class="mt-2 pl-3.5 text-sm text-cypher-muted">填寫主辦方資料即可建立（目前免審核）。</p>
      </div>

      <!-- Form card -->
      <div class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md animate-slide-up-delay">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/50 to-transparent" aria-hidden="true" />

        <div class="space-y-5 p-6">

          <!-- 主辦方名稱 -->
          <div>
            <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">
              主辦方名稱 <span class="text-cypher-accent">*</span>
            </label>
            <input
              v-model="form.name"
              placeholder="例如：街舞工作室"
              class="input-field"
            />
          </div>

          <!-- 聯絡信箱 -->
          <div>
            <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">
              聯絡信箱
            </label>
            <input
              v-model="form.contact_email"
              type="email"
              placeholder="contact@example.com"
              class="input-field"
            />
          </div>

          <!-- Logo URL -->
          <div>
            <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">
              Logo URL
            </label>
            <input
              v-model="form.logo_url"
              placeholder="https://..."
              class="input-field"
            />
          </div>

          <!-- Divider -->
          <div class="h-px bg-white/5" />

          <!-- 簡介 -->
          <div>
            <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">
              簡介
            </label>
            <textarea
              v-model="form.description"
              rows="3"
              placeholder="主辦方簡介..."
              class="input-field min-h-[80px] resize-y"
            />
          </div>

          <!-- Submit -->
          <button
            class="btn-primary w-full py-3.5 text-base disabled:opacity-50"
            :disabled="submitting"
            @click="submit"
          >
            <span v-if="submitting" class="flex items-center justify-center gap-2">
              <span class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              提交中...
            </span>
            <span v-else>建立主辦方</span>
          </button>
        </div>
      </div>

      <!-- Alerts -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 -translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
      >
        <div v-if="message" role="alert" class="mt-4 flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-sm text-emerald-400">{{ message }}</p>
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

      <!-- Footer hint -->
      <p class="mt-6 text-center text-sm text-cypher-muted">
        已有主辦方？
        <router-link to="/organizer/events/create" class="text-cypher-accent transition-colors hover:text-cypher-accent-bright">
          直接建立活動
        </router-link>
      </p>

    </div>
  </main>
</template>
