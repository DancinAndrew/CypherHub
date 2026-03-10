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
    setTimeout(() => router.push({ name: "organizer-events" }), 1500);
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "申請主辦方失敗。");
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-10">
    <div class="mb-8">
      <router-link to="/organizer" class="text-sm text-slate-600 hover:text-brand-600">← 回主辦方主頁</router-link>
    </div>

    <h1 class="text-2xl font-bold text-slate-900">步驟 1：申請成為主辦方</h1>
    <p class="mt-2 text-sm text-slate-600">填寫主辦方資料即可建立（目前免審核）。</p>

    <div class="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">主辦方名稱 *</label>
        <input
          v-model="form.name"
          placeholder="例如：街舞工作室"
          class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">聯絡信箱</label>
        <input
          v-model="form.contact_email"
          type="email"
          placeholder="contact@example.com"
          class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">Logo URL</label>
        <input
          v-model="form.logo_url"
          placeholder="https://..."
          class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">簡介</label>
        <textarea
          v-model="form.description"
          rows="3"
          placeholder="主辦方簡介..."
          class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      <p v-if="message" class="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{{ message }}</p>
      <p v-if="errorMessage" class="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{{ errorMessage }}</p>

      <button
        class="w-full rounded-lg bg-brand-600 px-4 py-3 font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        :disabled="submitting"
        @click="submit"
      >
        {{ submitting ? "提交中..." : "建立主辦方" }}
      </button>
    </div>

    <p class="mt-4 text-center text-sm text-slate-500">
      已有主辦方？
      <router-link to="/organizer/events" class="text-brand-600 hover:underline">直接建立活動</router-link>
    </p>
  </main>
</template>
