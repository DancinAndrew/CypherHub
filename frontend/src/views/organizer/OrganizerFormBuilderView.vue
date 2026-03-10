<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import { organizerFetchForms, organizerUpsertForm, type EventForm, type FormSchemaDefinition } from "../../api/client";
import { toApiErrorMessage } from "../../utils/errorMessages";

const route = useRoute();

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const eventId = ref("");
const ticketTypeId = ref("");
const formSchemaText = ref("");
const forms = ref<EventForm[]>([]);
const message = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const submitting = ref<"form" | "load" | null>(null);

function defaultTemplate(): FormSchemaDefinition {
  return {
    version: 1,
    fields: [
      { key: "full_name", label: "姓名", type: "text", required: true, placeholder: "請輸入姓名", help_text: "請填寫真實姓名", options: [] },
      { key: "phone", label: "聯絡電話", type: "phone", required: true, placeholder: "0900-000-000", help_text: "活動聯絡使用", options: [] },
      { key: "ig_account", label: "Instagram", type: "text", required: false, placeholder: "@your_handle", help_text: "選填", options: [] },
      { key: "agree_media", label: "同意活動影像紀錄", type: "checkbox", required: true, placeholder: "我同意主辦方於活動現場拍攝與使用活動紀錄", help_text: "必填同意條款", options: [] },
    ],
  };
}

function isValidUuid(s: string) {
  return uuidRegex.test(s.trim());
}

function useTemplate() {
  formSchemaText.value = JSON.stringify(defaultTemplate(), null, 2);
  message.value = "已填入範本。";
}

function parseSchema(): FormSchemaDefinition | null {
  const raw = formSchemaText.value.trim();
  if (!raw) {
    errorMessage.value = "表單 schema 不可為空。";
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as FormSchemaDefinition;
    if (!parsed || !Array.isArray(parsed.fields)) {
      errorMessage.value = "schema 必須包含 version 與 fields array。";
      return null;
    }
    return parsed;
  } catch {
    errorMessage.value = "JSON 無法解析。";
    return null;
  }
}

async function loadForms() {
  message.value = null;
  errorMessage.value = null;
  const id = eventId.value.trim();
  if (!isValidUuid(id)) {
    errorMessage.value = "請輸入有效的活動 ID。";
    return;
  }
  submitting.value = "load";
  try {
    forms.value = await organizerFetchForms(id);
    message.value = `已載入 ${forms.value.length} 個表單版本。`;
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "載入表單失敗。");
  } finally {
    submitting.value = null;
  }
}

async function submit() {
  message.value = null;
  errorMessage.value = null;
  const id = eventId.value.trim();
  if (!isValidUuid(id)) {
    errorMessage.value = "請輸入有效的活動 ID。";
    return;
  }
  if (ticketTypeId.value.trim() && !isValidUuid(ticketTypeId.value)) {
    errorMessage.value = "ticket_type_id 若填寫須為有效 UUID。";
    return;
  }
  const schema = parseSchema();
  if (!schema) return;
  submitting.value = "form";
  try {
    await organizerUpsertForm(id, {
      ticket_type_id: ticketTypeId.value.trim() || null,
      schema,
      is_active: true,
    });
    await loadForms();
    message.value = "表單已儲存。";
  } catch (err: unknown) {
    errorMessage.value = toApiErrorMessage(err, "儲存表單失敗。");
  } finally {
    submitting.value = null;
  }
}

watch(
  () => route.params.eventId,
  (id) => {
    if (id && typeof id === "string") {
      eventId.value = id;
      loadForms();
    }
  },
  { immediate: true }
);

formSchemaText.value = JSON.stringify(defaultTemplate(), null, 2);
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-10">
    <div class="mb-8">
      <router-link to="/organizer" class="text-sm text-slate-600 hover:text-brand-600">← 回主辦方主頁</router-link>
    </div>

    <h1 class="text-2xl font-bold text-slate-900">步驟 3：報名表單設定</h1>
    <p class="mt-2 text-sm text-slate-600">設定活動報名時需填寫的欄位。可設 event-level（ticket_type_id 留空）或針對特定票種。</p>

    <div class="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">活動 ID *</label>
          <input
            v-model="eventId"
            placeholder="UUID"
            class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm"
          />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">票種 ID（選填）</label>
          <input
            v-model="ticketTypeId"
            placeholder="留空為 event-level"
            class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm"
          />
        </div>
      </div>

      <div class="flex flex-wrap gap-3">
        <button
          class="rounded-lg border border-slate-400 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          @click="useTemplate"
        >
          使用範本
        </button>
        <button
          class="rounded-lg border border-slate-400 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          :disabled="submitting === 'load'"
          @click="loadForms"
        >
          {{ submitting === "load" ? "載入中..." : "載入現有表單" }}
        </button>
        <button
          class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          :disabled="submitting === 'form'"
          @click="submit"
        >
          {{ submitting === "form" ? "儲存中..." : "儲存表單" }}
        </button>
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">表單 JSON Schema</label>
        <textarea
          v-model="formSchemaText"
          rows="16"
          class="w-full rounded-lg border border-slate-300 px-4 py-2 font-mono text-xs"
          placeholder='{"version":1,"fields":[...]}'
        />
      </div>

      <p v-if="message" class="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{{ message }}</p>
      <p v-if="errorMessage" class="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{{ errorMessage }}</p>

      <div v-if="forms.length > 0" class="rounded-lg border border-slate-200">
        <p class="bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700">已儲存表單</p>
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-left text-slate-600">
            <tr>
              <th class="px-3 py-2">ID</th>
              <th class="px-3 py-2">票種</th>
              <th class="px-3 py-2">版本</th>
              <th class="px-3 py-2">欄位數</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in forms" :key="f.id" class="border-t border-slate-200">
              <td class="px-3 py-2 font-mono text-xs">{{ f.id.slice(0, 8) }}...</td>
              <td class="px-3 py-2">{{ f.ticket_type_id ? f.ticket_type_id.slice(0, 8) + "..." : "event-level" }}</td>
              <td class="px-3 py-2">{{ f.version }}</td>
              <td class="px-3 py-2">{{ f.schema.fields.length }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </main>
</template>
