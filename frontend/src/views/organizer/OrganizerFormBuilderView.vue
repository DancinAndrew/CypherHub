<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  fetchMyOrganizerSummary,
  organizerFetchForms,
  organizerUpsertForm,
  type EventForm,
  type FormField,
  type FormFieldType,
  type FormSchemaDefinition,
  type MyOrganizerEvent,
} from "../../api/client";
import { toApiErrorMessage } from "../../utils/errorMessages";

const route = useRoute();

const FIELD_TYPES: { value: FormFieldType; label: string }[] = [
  { value: "text", label: "單行文字" },
  { value: "number", label: "數字" },
  { value: "email", label: "Email" },
  { value: "phone", label: "電話" },
  { value: "url", label: "網址" },
  { value: "date", label: "日期" },
  { value: "single_select", label: "單選（圓鈕）" },
  { value: "dropdown", label: "下拉選單" },
  { value: "multi_select", label: "多選（勾選框）" },
  { value: "checkbox", label: "同意勾選" },
];

type EditorField = {
  id: string;
  key: string;
  label: string;
  type: FormFieldType;
  required: boolean;
  placeholder: string;
  help_text: string;
  options: string[];
};

function newEditorField(overrides?: Partial<EditorField>): EditorField {
  return {
    id: crypto.randomUUID?.() ?? `f-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    key: overrides?.key ?? "",
    label: overrides?.label ?? "",
    type: overrides?.type ?? "text",
    required: overrides?.required ?? false,
    placeholder: overrides?.placeholder ?? "",
    help_text: overrides?.help_text ?? "",
    options: overrides?.options ? [...overrides.options] : [],
  };
}

function formFieldToEditor(f: FormField, index: number): EditorField {
  return newEditorField({
    key: f.key || `field_${index}`,
    label: f.label ?? "",
    type: f.type ?? "text",
    required: f.required ?? false,
    placeholder: f.placeholder ?? "",
    help_text: f.help_text ?? "",
    options: f.options ?? [],
  });
}

function editorFieldToFormField(f: EditorField): FormField {
  return {
    key: (f.key || `field_${f.id}`).trim() || "field",
    label: (f.label || "未命名欄位").trim(),
    type: f.type,
    required: f.required,
    placeholder: f.placeholder.trim() || undefined,
    help_text: f.help_text.trim() || undefined,
    options: f.type === "single_select" || f.type === "multi_select" || f.type === "dropdown" ? f.options.filter((o) => o.trim()) : [],
  };
}

function defaultTemplateFields(): EditorField[] {
  return [
    newEditorField({ key: "full_name", label: "姓名", type: "text", required: true, placeholder: "請輸入姓名", help_text: "請填寫真實姓名" }),
    newEditorField({ key: "phone", label: "聯絡電話", type: "phone", required: true, placeholder: "0900-000-000", help_text: "活動聯絡使用" }),
    newEditorField({ key: "ig_account", label: "Instagram", type: "text", required: false, placeholder: "@your_handle", help_text: "選填" }),
    newEditorField({ key: "agree_media", label: "同意活動影像紀錄", type: "checkbox", required: true, placeholder: "我同意主辦方於活動現場拍攝與使用活動紀錄", help_text: "必填同意條款" }),
  ];
}

const myEvents = ref<MyOrganizerEvent[]>([]);
const summaryLoading = ref(true);
const eventId = ref("");
const ticketTypeId = ref("");
const editorFields = ref<EditorField[]>(defaultTemplateFields());
const forms = ref<EventForm[]>([]);
const message = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const submitting = ref<"form" | "load" | null>(null);

function formatEventOption(ev: MyOrganizerEvent): string {
  const date = ev.start_at ? new Date(ev.start_at).toLocaleDateString(undefined, { dateStyle: "short" }) : "";
  const status = ev.status === "published" ? "已上架" : "草稿";
  return `${ev.title}（${date}・${status}）`;
}

function addField() {
  const idx = editorFields.value.length;
  editorFields.value.push(newEditorField({ key: `field_${idx}` }));
}

function removeField(index: number) {
  editorFields.value.splice(index, 1);
}

function moveField(index: number, dir: number) {
  const next = index + dir;
  if (next < 0 || next >= editorFields.value.length) return;
  const arr = [...editorFields.value];
  const [removed] = arr.splice(index, 1);
  arr.splice(next, 0, removed);
  editorFields.value = arr;
}

function addOption(field: EditorField) {
  field.options.push("");
}

function removeOption(field: EditorField, optIndex: number) {
  field.options.splice(optIndex, 1);
}

function useTemplate() {
  editorFields.value = defaultTemplateFields();
  message.value = "已填入預設欄位。";
}

function loadFormIntoEditor(form: EventForm) {
  const fields = (form.schema?.fields ?? []).map((f, i) => formFieldToEditor(f, i));
  editorFields.value = fields.length ? fields : defaultTemplateFields();
  message.value = "已載入表單到編輯器，可修改後儲存。";
}

function buildSchema(): FormSchemaDefinition {
  return {
    version: 1,
    fields: editorFields.value.map(editorFieldToFormField),
  };
}

onMounted(async () => {
  summaryLoading.value = true;
  try {
    const data = await fetchMyOrganizerSummary();
    myEvents.value = data.events ?? [];
    const paramId = route.params.eventId && typeof route.params.eventId === "string" ? route.params.eventId : "";
    if (paramId && myEvents.value.some((e) => e.id === paramId)) {
      eventId.value = paramId;
      await loadForms();
    }
  } catch {
    myEvents.value = [];
  } finally {
    summaryLoading.value = false;
  }
});

async function loadForms() {
  message.value = null;
  errorMessage.value = null;
  const id = eventId.value.trim();
  if (!id) {
    errorMessage.value = "請選擇活動。";
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
  if (!id) {
    errorMessage.value = "請選擇活動。";
    return;
  }
  const tid = ticketTypeId.value.trim();
  if (tid && !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(tid)) {
    errorMessage.value = "票種 ID 若填寫須為有效 UUID。";
    return;
  }
  const schema = buildSchema();
  if (!schema.fields.length) {
    errorMessage.value = "請至少新增一個欄位。";
    return;
  }
  const keySet = new Set<string>();
  for (const f of schema.fields) {
    if (keySet.has(f.key)) {
      errorMessage.value = `欄位代碼重複：「${f.key}」，請修改其中一個。`;
      return;
    }
    keySet.add(f.key);
  }
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

const needsOptions = (type: FormFieldType) =>
  type === "single_select" || type === "multi_select" || type === "dropdown";

watch(
  () => route.params.eventId,
  (id) => {
    if (id && typeof id === "string") {
      eventId.value = id;
      if (!summaryLoading.value) loadForms();
    }
  },
  { immediate: true }
);
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-10">
    <div class="mb-8">
      <router-link to="/organizer" class="text-sm text-slate-600 hover:text-brand-600">← 回主辦方主頁</router-link>
    </div>

    <h1 class="text-2xl font-bold text-slate-900">步驟 4：報名表單設定</h1>
    <p class="mt-2 text-sm text-slate-600">新增、排序與編輯報名欄位，儲存後會套用到該活動。可設 event-level（票種留空）或針對特定票種。</p>

    <div class="mt-6 space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">活動 *</label>
          <select
            v-model="eventId"
            class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm"
            :disabled="summaryLoading"
          >
            <option value="">— 請選擇活動 —</option>
            <option v-for="ev in myEvents" :key="ev.id" :value="ev.id">
              {{ formatEventOption(ev) }}
            </option>
          </select>
          <p v-if="summaryLoading" class="mt-1 text-xs text-slate-500">載入活動列表中…</p>
          <p v-else-if="myEvents.length === 0" class="mt-1 text-xs text-amber-600">尚無活動，請先建立活動。</p>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">票種 ID（選填）</label>
          <input
            v-model="ticketTypeId"
            placeholder="留空為整場活動共用"
            class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm"
          />
        </div>
      </div>

      <div class="flex flex-wrap gap-3">
        <button
          type="button"
          class="rounded-lg border border-slate-400 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          @click="useTemplate"
        >
          填入預設欄位
        </button>
        <button
          type="button"
          class="rounded-lg border border-slate-400 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          :disabled="submitting === 'load'"
          @click="loadForms"
        >
          {{ submitting === "load" ? "載入中…" : "載入現有表單" }}
        </button>
        <button
          type="button"
          class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          :disabled="submitting === 'form'"
          @click="submit"
        >
          {{ submitting === "form" ? "儲存中…" : "儲存表單" }}
        </button>
      </div>

      <div>
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-slate-800">報名欄位</h2>
          <button
            type="button"
            class="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
            @click="addField"
          >
            ＋ 新增欄位
          </button>
        </div>
        <p class="mb-4 text-xs text-slate-500">欄位代碼（key）用於後台辨識，建議英文或數字，勿重複。</p>

        <div class="space-y-4">
          <div
            v-for="(field, index) in editorFields"
            :key="field.id"
            class="rounded-lg border border-slate-200 bg-slate-50/80 p-4"
          >
            <div class="mb-3 flex items-center justify-between">
              <span class="text-sm font-medium text-slate-600">欄位 {{ index + 1 }}</span>
              <div class="flex gap-1">
                <button type="button" class="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-200" :disabled="index === 0" @click="moveField(index, -1)">↑</button>
                <button type="button" class="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-200" :disabled="index === editorFields.length - 1" @click="moveField(index, 1)">↓</button>
                <button type="button" class="rounded px-2 py-1 text-xs text-rose-600 hover:bg-rose-50" @click="removeField(index)">刪除</button>
              </div>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <div>
                <label class="mb-0.5 block text-xs font-medium text-slate-600">欄位名稱（顯示給報名者）*</label>
                <input v-model="field.label" type="text" placeholder="例：姓名" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label class="mb-0.5 block text-xs font-medium text-slate-600">欄位代碼（key）*</label>
                <input v-model="field.key" type="text" placeholder="例：full_name" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono" />
                <p class="mt-0.5 text-xs text-slate-400">可填英文/數字，儲存時會用於辨識</p>
              </div>
            </div>
            <div class="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <label class="mb-0.5 block text-xs font-medium text-slate-600">欄位類型</label>
                <select v-model="field.type" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option v-for="opt in FIELD_TYPES" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                </select>
              </div>
              <div class="flex items-end">
                <label class="flex items-center gap-2">
                  <input v-model="field.required" type="checkbox" class="rounded border-slate-300" />
                  <span class="text-sm text-slate-700">必填</span>
                </label>
              </div>
            </div>
            <div class="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <label class="mb-0.5 block text-xs font-medium text-slate-600">佔位文字（選填）</label>
                <input v-model="field.placeholder" type="text" placeholder="例：請輸入姓名" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label class="mb-0.5 block text-xs font-medium text-slate-600">說明文字（選填）</label>
                <input v-model="field.help_text" type="text" placeholder="例：請填寫真實姓名" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
            </div>
            <!-- 選項（單選/多選/下拉） -->
            <div v-if="needsOptions(field.type)" class="mt-3">
              <label class="mb-1 block text-xs font-medium text-slate-600">選項</label>
              <div class="space-y-2">
                <div v-for="(opt, optIndex) in field.options" :key="optIndex" class="flex items-center gap-2">
                  <input v-model="field.options[optIndex]" type="text" placeholder="選項內容" class="w-48 rounded border border-slate-300 px-2 py-1 text-sm" />
                  <button type="button" class="text-slate-400 hover:text-rose-600" title="移除選項" @click="removeOption(field, optIndex)">×</button>
                </div>
                <button type="button" class="rounded border border-dashed border-slate-400 px-2 py-1 text-xs text-slate-500 hover:bg-slate-100" @click="addOption(field)">＋ 新增選項</button>
              </div>
            </div>
          </div>
        </div>
        <p v-if="editorFields.length === 0" class="rounded-lg bg-amber-50 py-4 text-center text-sm text-amber-700">尚無欄位，請點「新增欄位」或「填入預設欄位」。</p>
      </div>

      <p v-if="message" class="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{{ message }}</p>
      <p v-if="errorMessage" class="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{{ errorMessage }}</p>

      <div v-if="forms.length > 0" class="rounded-lg border border-slate-200">
        <p class="bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700">已儲存表單</p>
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-left text-slate-600">
            <tr>
              <th class="px-3 py-2">票種</th>
              <th class="px-3 py-2">版本</th>
              <th class="px-3 py-2">欄位數</th>
              <th class="px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in forms" :key="f.id" class="border-t border-slate-200">
              <td class="px-3 py-2">{{ f.ticket_type_id ? f.ticket_type_id.slice(0, 8) + "…" : "整場活動" }}</td>
              <td class="px-3 py-2">{{ f.version }}</td>
              <td class="px-3 py-2">{{ f.schema.fields.length }}</td>
              <td class="px-3 py-2">
                <button type="button" class="text-brand-600 hover:underline" @click="loadFormIntoEditor(f)">載入到編輯器</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </main>
</template>
