<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import DynamicForm from "../components/DynamicForm.vue";
import {
  fetchEventDetail,
  fetchEventForm,
  registerFree,
  type EventDetail,
  type EventForm,
  type TicketType,
} from "../api/client";
import { eventTypeLabelFromKey, styleLabelFromKey } from "../constants/taxonomy";
import { useAuthStore } from "../stores/auth";
import { toApiErrorMessage } from "../utils/errorMessages";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const eventId = computed(() => String(route.params.eventId ?? ""));
const detail = ref<EventDetail | null>(null);
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const registerMessage = ref<string | null>(null);
const registerLoading = ref(false);
const formLoading = ref(false);
const formError = ref<string | null>(null);

const selectedTicketTypeId = ref<string | null>(null);
const selectedForm = ref<EventForm | null>(null);
const formAnswers = ref<Record<string, unknown>>({});

const selectedTicketType = computed<TicketType | null>(() => {
  if (!detail.value || !selectedTicketTypeId.value) {
    return null;
  }
  return detail.value.ticket_types.find((item) => item.id === selectedTicketTypeId.value) ?? null;
});

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function asSocialEntries(raw: Record<string, string> | undefined): Array<{ key: string; value: string }> {
  if (!raw || typeof raw !== "object") {
    return [];
  }
  return Object.entries(raw)
    .filter(([, value]) => Boolean(value))
    .map(([key, value]) => ({ key, value }));
}

function asScheduleItems(raw: Array<Record<string, string>> | undefined): Array<Record<string, string>> {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((item) => item && typeof item === "object");
}

function validateClientAnswers(): string | null {
  if (!selectedForm.value) {
    return null;
  }

  for (const field of selectedForm.value.schema.fields) {
    const value = formAnswers.value[field.key];

    if (!field.required) {
      continue;
    }

    if (field.type === "checkbox") {
      if (value !== true) {
        return `${field.label} 為必填，且必須勾選。`;
      }
      continue;
    }

    if (field.type === "multi_select") {
      if (!Array.isArray(value) || value.length === 0) {
        return `${field.label} 為必填。`;
      }
      continue;
    }

    if (value === undefined || value === null || String(value).trim() === "") {
      return `${field.label} 為必填。`;
    }
  }

  return null;
}

async function loadDetail(): Promise<void> {
  if (!eventId.value) {
    errorMessage.value = "Missing event id";
    loading.value = false;
    return;
  }

  loading.value = true;
  errorMessage.value = null;

  try {
    detail.value = await fetchEventDetail(eventId.value);
    if (detail.value.ticket_types.length === 1) {
      await selectTicketType(detail.value.ticket_types[0]);
    }
  } catch (error: unknown) {
    errorMessage.value = toApiErrorMessage(error, "Failed to load event");
  } finally {
    loading.value = false;
  }
}

async function selectTicketType(ticketType: TicketType): Promise<void> {
  selectedTicketTypeId.value = ticketType.id;
  formLoading.value = true;
  formError.value = null;
  registerMessage.value = null;
  formAnswers.value = {};

  try {
    selectedForm.value = await fetchEventForm(eventId.value, ticketType.id);
  } catch (error: unknown) {
    selectedForm.value = null;
    formError.value = toApiErrorMessage(error, "Failed to load registration form");
  } finally {
    formLoading.value = false;
  }
}

async function handleRegister(): Promise<void> {
  registerMessage.value = null;

  if (!selectedTicketType.value) {
    registerMessage.value = "請先選擇票種。";
    return;
  }

  if (!authStore.isAuthenticated) {
    await router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }

  const validationMessage = validateClientAnswers();
  if (validationMessage) {
    registerMessage.value = validationMessage;
    return;
  }

  registerLoading.value = true;

  try {
    const tickets = await registerFree(eventId.value, {
      ticket_type_id: selectedTicketType.value.id,
      quantity: 1,
      answers: formAnswers.value,
    });
    registerMessage.value = `Registration success. Issued ${tickets.length} ticket(s).`;
    formAnswers.value = {};
  } catch (error: unknown) {
    registerMessage.value = toApiErrorMessage(error, "Registration failed");
  } finally {
    registerLoading.value = false;
  }
}

onMounted(() => {
  loadDetail().catch(() => {});
});
</script>

<template>
  <main class="mx-auto w-full max-w-4xl px-4 py-10">
    <div v-if="loading" class="rounded-xl border border-slate-200 bg-white p-5 text-slate-600">Loading event...</div>
    <div v-else-if="errorMessage" class="rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-700">{{ errorMessage }}</div>

    <section v-else-if="detail" class="space-y-6">
      <div
        v-if="detail.event_media && detail.event_media.length > 0"
        class="overflow-hidden rounded-xl border border-slate-200 bg-slate-100"
      >
        <div class="relative aspect-[16/9] w-full">
          <img
            v-for="(item, idx) in detail.event_media"
            :key="item.id"
            :src="eventMediaUrl(item.path)"
            :alt="`${detail.event.title} image ${idx + 1}`"
            class="absolute inset-0 h-full w-full object-cover transition-opacity duration-300"
            :class="carouselIndex === idx ? 'opacity-100' : 'opacity-0'"
          />
        </div>
        <div v-if="detail.event_media.length > 1" class="flex justify-center gap-2 py-2">
          <button
            type="button"
            class="rounded-full bg-slate-300 p-1.5 text-white hover:bg-slate-400"
            aria-label="上一張"
            @click="carouselIndex = (carouselIndex - 1 + detail.event_media.length) % detail.event_media.length"
          >
            ←
          </button>
          <span class="flex items-center text-sm text-slate-600">{{ carouselIndex + 1 }} / {{ detail.event_media.length }}</span>
          <button
            type="button"
            class="rounded-full bg-slate-300 p-1.5 text-white hover:bg-slate-400"
            aria-label="下一張"
            @click="carouselIndex = (carouselIndex + 1) % detail.event_media.length"
          >
            →
          </button>
        </div>
      </div>

      <header class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 class="text-3xl font-bold text-slate-900">{{ detail.event.title }}</h1>
        <p class="mt-3 text-slate-600">{{ detail.event.description || detail.event.short_desc || "No description" }}</p>
        <div class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="style in detail.event.dance_styles || []"
            :key="`style-${style}`"
            class="rounded-full bg-indigo-50 px-2 py-1 text-xs font-semibold text-indigo-700"
          >
            {{ styleLabelFromKey(style) }}
          </span>
          <span
            v-for="type in detail.event.event_types || []"
            :key="`type-${type}`"
            class="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700"
          >
            {{ eventTypeLabelFromKey(type) }}
          </span>
        </div>
        <div class="mt-4 grid gap-2 text-sm text-slate-500">
          <p>Start: {{ formatDateTime(detail.event.start_at) }}</p>
          <p>End: {{ formatDateTime(detail.event.end_at) }}</p>
          <p v-if="detail.event.registration_start_at || detail.event.registration_end_at">
            Registration:
            {{ formatDateTime(detail.event.registration_start_at) }} ~
            {{ formatDateTime(detail.event.registration_end_at) }}
          </p>
          <p>Location: {{ detail.event.location_name || "TBD" }}</p>
          <p v-if="detail.event.location_address">Address: {{ detail.event.location_address }}</p>
          <p v-if="detail.event.map_url">
            Map:
            <a
              :href="detail.event.map_url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-brand-700 underline"
            >
              Open map
            </a>
          </p>
        </div>
      </header>

      <section class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 class="text-xl font-semibold text-slate-900">Event Information</h2>

        <div class="mt-4 grid gap-2 text-sm text-slate-600">
          <p v-if="detail.event.eligibility"><span class="font-semibold text-slate-800">Eligibility:</span> {{ detail.event.eligibility }}</p>
          <p v-if="detail.event.event_language"><span class="font-semibold text-slate-800">Language:</span> {{ detail.event.event_language }}</p>
          <p v-if="detail.event.checkin_open_at"><span class="font-semibold text-slate-800">Check-in opens:</span> {{ formatDateTime(detail.event.checkin_open_at) }}</p>
          <p v-if="detail.event.checkin_note"><span class="font-semibold text-slate-800">Check-in note:</span> {{ detail.event.checkin_note }}</p>
          <p v-if="detail.event.contact_email"><span class="font-semibold text-slate-800">Contact email:</span> {{ detail.event.contact_email }}</p>
          <p v-if="detail.event.contact_phone"><span class="font-semibold text-slate-800">Contact phone:</span> {{ detail.event.contact_phone }}</p>
        </div>

        <div v-if="asSocialEntries(detail.event.socials).length > 0" class="mt-4">
          <h3 class="text-sm font-semibold text-slate-800">Social Links</h3>
          <ul class="mt-2 grid gap-1 text-sm text-slate-600">
            <li v-for="item in asSocialEntries(detail.event.socials)" :key="item.key">
              <span class="font-semibold text-slate-800">{{ item.key.toUpperCase() }}:</span>
              <a :href="item.value" target="_blank" rel="noopener noreferrer" class="ml-1 text-brand-700 underline">
                {{ item.value }}
              </a>
            </li>
          </ul>
        </div>

        <div v-if="asScheduleItems(detail.event.schedule).length > 0" class="mt-4">
          <h3 class="text-sm font-semibold text-slate-800">Schedule</h3>
          <ul class="mt-2 space-y-2">
            <li
              v-for="(item, index) in asScheduleItems(detail.event.schedule)"
              :key="`${index}-${item.time || ''}-${item.title || ''}`"
              class="rounded-lg border border-slate-200 p-3 text-sm"
            >
              <p class="font-semibold text-slate-800">
                {{ item.time || "--:--" }} {{ item.title || "Untitled" }}
              </p>
              <p v-if="item.desc" class="mt-1 text-slate-600">{{ item.desc }}</p>
            </li>
          </ul>
        </div>
      </section>

      <section class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 class="text-xl font-semibold text-slate-900">Ticket Types</h2>
        <p class="mt-2 text-xs text-slate-500">
          MVP-1 限制：僅免費票。選擇票種後，若主辦方有設定報名表單，會在下方動態顯示。
        </p>

        <div v-if="detail.ticket_types.length === 0" class="mt-3 text-slate-500">No active ticket types.</div>

        <div v-else class="mt-4 space-y-4">
          <article
            v-for="ticketType in detail.ticket_types"
            :key="ticketType.id"
            class="rounded-lg border border-slate-200 p-4"
            :class="selectedTicketTypeId === ticketType.id ? 'ring-2 ring-brand-200' : ''"
          >
            <div class="flex items-center justify-between gap-4">
              <div>
                <h3 class="font-semibold text-slate-900">{{ ticketType.name }}</h3>
                <p class="text-sm text-slate-600">{{ ticketType.description || "No description" }}</p>
                <p class="mt-2 text-xs text-slate-500">
                  Capacity: {{ ticketType.capacity }} / Sold: {{ ticketType.sold_count }} / Limit: {{ ticketType.per_user_limit }}
                </p>
              </div>
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm font-semibold"
                :class="selectedTicketTypeId === ticketType.id ? 'bg-slate-200 text-slate-800' : 'bg-brand-600 text-white hover:bg-brand-700'"
                @click="selectTicketType(ticketType)"
              >
                {{ selectedTicketTypeId === ticketType.id ? "Selected" : "Use This Ticket Type" }}
              </button>
            </div>
          </article>
        </div>
      </section>

      <section v-if="selectedTicketType" class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div class="flex items-center justify-between gap-4">
          <div>
            <h2 class="text-xl font-semibold text-slate-900">Registration Form</h2>
            <p class="mt-1 text-sm text-slate-600">
              Ticket type: {{ selectedTicketType.name }}
            </p>
          </div>
          <button
            type="button"
            class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            :disabled="registerLoading || formLoading"
            @click="handleRegister"
          >
            {{ registerLoading ? "Registering..." : "Submit Registration" }}
          </button>
        </div>

        <div v-if="formLoading" class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading registration form...
        </div>
        <div v-else-if="formError" class="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {{ formError }}
        </div>
        <div v-else-if="selectedForm && selectedForm.schema.fields.length > 0" class="mt-4">
          <DynamicForm v-model="formAnswers" :schema="selectedForm.schema" :disabled="registerLoading" />
        </div>
        <div v-else class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          This ticket type has no extra form fields. You can register directly.
        </div>

        <p v-if="registerMessage" class="mt-4 text-sm text-brand-700">{{ registerMessage }}</p>
      </section>
    </section>
  </main>
</template>
