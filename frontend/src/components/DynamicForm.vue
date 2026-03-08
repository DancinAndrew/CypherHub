<script setup lang="ts">
import type { FormField, FormSchemaDefinition } from "../api/client";

const props = defineProps<{
  schema: FormSchemaDefinition;
  modelValue: Record<string, unknown>;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: Record<string, unknown>): void;
}>();

function updateField(key: string, value: unknown): void {
  emit("update:modelValue", {
    ...props.modelValue,
    [key]: value,
  });
}

function stringValue(field: FormField): string {
  const value = props.modelValue[field.key];
  return typeof value === "string" ? value : "";
}

function numberValue(field: FormField): string | number {
  const value = props.modelValue[field.key];
  return typeof value === "number" || typeof value === "string" ? value : "";
}

function checkboxValue(field: FormField): boolean {
  return props.modelValue[field.key] === true;
}

function arrayValue(field: FormField): string[] {
  const value = props.modelValue[field.key];
  return Array.isArray(value) ? value.map(String) : [];
}

function toggleMultiOption(field: FormField, option: string): void {
  const current = arrayValue(field);
  if (current.includes(option)) {
    updateField(
      field.key,
      current.filter((item) => item !== option),
    );
    return;
  }

  updateField(field.key, [...current, option]);
}
</script>

<template>
  <div class="grid gap-4">
    <div
      v-for="field in schema.fields"
      :key="field.key"
      class="rounded-lg border border-slate-200 bg-slate-50 p-4"
    >
      <label class="block">
        <span class="text-sm font-semibold text-slate-800">
          {{ field.label }}
          <span v-if="field.required" class="text-rose-600">*</span>
        </span>
        <span v-if="field.help_text" class="mt-1 block text-xs text-slate-500">{{ field.help_text }}</span>

        <input
          v-if="['text', 'email', 'phone', 'url', 'date'].includes(field.type)"
          :type="field.type === 'date' ? 'date' : field.type === 'phone' ? 'tel' : field.type"
          :value="stringValue(field)"
          :placeholder="field.placeholder || ''"
          :disabled="disabled"
          class="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          @input="updateField(field.key, ($event.target as HTMLInputElement).value)"
        />

        <input
          v-else-if="field.type === 'number'"
          type="number"
          :value="numberValue(field)"
          :placeholder="field.placeholder || ''"
          :disabled="disabled"
          class="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          @input="updateField(field.key, ($event.target as HTMLInputElement).value)"
        />

        <select
          v-else-if="field.type === 'single_select' || field.type === 'dropdown'"
          :value="stringValue(field)"
          :disabled="disabled"
          class="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          @change="updateField(field.key, ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Select</option>
          <option v-for="option in field.options || []" :key="option" :value="option">
            {{ option }}
          </option>
        </select>

        <div v-else-if="field.type === 'multi_select'" class="mt-2 flex flex-wrap gap-2">
          <label
            v-for="option in field.options || []"
            :key="option"
            class="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-1 text-xs text-slate-700"
          >
            <input
              type="checkbox"
              :checked="arrayValue(field).includes(option)"
              :disabled="disabled"
              @change="toggleMultiOption(field, option)"
            />
            <span>{{ option }}</span>
          </label>
        </div>

        <label
          v-else-if="field.type === 'checkbox'"
          class="mt-2 inline-flex items-center gap-2 text-sm text-slate-700"
        >
          <input
            type="checkbox"
            :checked="checkboxValue(field)"
            :disabled="disabled"
            @change="updateField(field.key, ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ field.placeholder || 'I agree' }}</span>
        </label>
      </label>
    </div>
  </div>
</template>
