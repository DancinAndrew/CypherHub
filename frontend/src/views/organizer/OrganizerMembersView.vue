<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import {
  fetchMyOrganizerSummary,
  organizerFetchMembers,
  organizerAddMember,
  organizerUpdateMemberRole,
  organizerRemoveMember,
  type MyOrganizerOrg,
  type OrganizerMemberItem,
} from "../../api/client";
import { toApiErrorMessage } from "../../utils/errorMessages";

const summary = ref<{ organizations: MyOrganizerOrg[] } | null>(null);
const orgsAdmin = computed(() => {
  const orgs = summary.value?.organizations ?? [];
  return orgs.filter((o) => o.role === "owner" || o.role === "admin");
});

const selectedOrgId = ref("");
const members = ref<OrganizerMemberItem[]>([]);
const loading = ref(false);
const loadError = ref<string | null>(null);

const showAddForm = ref(false);
const addUserId = ref("");
const addRole = ref<"admin" | "staff">("staff");
const addError = ref<string | null>(null);
const addSubmitting = ref(false);

const editingUserId = ref<string | null>(null);
const editRole = ref<"owner" | "admin" | "staff">("staff");
const editSubmitting = ref(false);

const removingUserId = ref<string | null>(null);

async function loadMembers() {
  if (!selectedOrgId.value) {
    members.value = [];
    return;
  }
  loading.value = true;
  loadError.value = null;
  try {
    const items = await organizerFetchMembers(selectedOrgId.value);
    members.value = items;
  } catch (e) {
    loadError.value = toApiErrorMessage(e, "載入成員失敗");
    members.value = [];
  } finally {
    loading.value = false;
  }
}

watch(selectedOrgId, () => {
  loadMembers();
});

onMounted(async () => {
  try {
    const data = await fetchMyOrganizerSummary();
    summary.value = { organizations: data.organizations };
    if (!selectedOrgId.value && orgsAdmin.value.length > 0) {
      selectedOrgId.value = orgsAdmin.value[0].id;
    }
  } catch {
    summary.value = { organizations: [] };
  } finally {
    await loadMembers();
  }
});

function roleLabel(role: string): string {
  const map: Record<string, string> = {
    owner: "擁有者",
    admin: "管理員",
    staff: "工作人員",
  };
  return map[role] ?? role;
}

async function submitAdd() {
  addError.value = null;
  if (!addUserId.value.trim()) {
    addError.value = "請輸入 User ID（UUID）";
    return;
  }
  addSubmitting.value = true;
  try {
    await organizerAddMember(selectedOrgId.value, {
      user_id: addUserId.value.trim(),
      role: addRole.value,
    });
    showAddForm.value = false;
    addUserId.value = "";
    addRole.value = "staff";
    await loadMembers();
  } catch (e) {
    addError.value = toApiErrorMessage(e, "新增成員失敗");
  } finally {
    addSubmitting.value = false;
  }
}

function startEdit(m: OrganizerMemberItem) {
  editingUserId.value = m.user_id;
  editRole.value = m.role as "owner" | "admin" | "staff";
}

function cancelEdit() {
  editingUserId.value = null;
}

async function submitEdit() {
  if (!editingUserId.value) return;
  editSubmitting.value = true;
  try {
    await organizerUpdateMemberRole(selectedOrgId.value, editingUserId.value, editRole.value);
    editingUserId.value = null;
    await loadMembers();
  } finally {
    editSubmitting.value = false;
  }
}

async function removeMember(m: OrganizerMemberItem) {
  if (!confirm(`確定要移除 ${m.user_id}（${roleLabel(m.role)}）嗎？`)) return;
  removingUserId.value = m.user_id;
  try {
    await organizerRemoveMember(selectedOrgId.value, m.user_id);
    await loadMembers();
  } finally {
    removingUserId.value = null;
  }
}
</script>

<template>
  <main class="relative min-h-[calc(100vh-4rem)] w-full overflow-hidden px-4 pb-20 pt-10">
    <!-- Background layers -->
    <div class="absolute inset-0 bg-gradient-mesh" aria-hidden="true" />
    <div class="pointer-events-none absolute inset-0" style="background: radial-gradient(ellipse 60% 40% at 80% 0%, rgba(124,58,237,0.10) 0%, transparent 70%)" aria-hidden="true" />

    <div class="relative z-10 mx-auto w-full max-w-3xl">

      <!-- Page header -->
      <header class="mb-8 animate-slide-up">
        <p class="section-label mb-2">Members</p>
        <div class="flex items-center gap-3">
          <span class="h-6 w-0.5 rounded-full bg-gradient-to-b from-cypher-accent to-cypher-accent-pink" aria-hidden="true" />
          <h1 class="font-street text-2xl tracking-widest text-white">成員管理</h1>
        </div>
        <p class="mt-2 pl-3.5 text-sm text-cypher-muted">管理主辦方成員與角色（僅 owner/admin 可操作）</p>
      </header>

      <!-- No access state -->
      <div
        v-if="orgsAdmin.length === 0"
        class="flex items-start gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 animate-slide-up-delay"
      >
        <svg class="mt-0.5 h-4 w-4 shrink-0 text-amber-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        <p class="text-sm text-amber-300">您目前非任何主辦方的 owner 或 admin，無法管理成員。</p>
      </div>

      <template v-else>

        <!-- Org selector -->
        <div class="animate-slide-up-delay">
          <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">選擇主辦方</label>
          <select v-model="selectedOrgId" class="input-field">
            <option value="">— 請選擇 —</option>
            <option v-for="o in orgsAdmin" :key="o.id" :value="o.id">
              {{ o.name }}（{{ roleLabel(o.role) }}）
            </option>
          </select>
        </div>

        <!-- Load error -->
        <div v-if="loadError" class="mt-4 flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3">
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-rose-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <p class="text-sm text-rose-300">{{ loadError }}</p>
        </div>

        <!-- Members panel -->
        <div v-if="selectedOrgId && !loadError" class="mt-6">

          <!-- Add member form -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 -translate-y-2"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition-all duration-150 ease-in"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-2"
          >
            <div v-if="showAddForm" class="relative mb-5 overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md">
              <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent-cyan/50 to-transparent" aria-hidden="true" />
              <div class="border-b border-white/5 px-6 py-4">
                <h3 class="text-sm font-semibold text-white">新增成員</h3>
                <p class="mt-0.5 text-xs text-cypher-muted">需已註冊使用者之 User ID（UUID），可於其個人設定或後台查詢。</p>
              </div>
              <div class="p-6">
                <div class="flex flex-wrap gap-4">
                  <div class="min-w-[200px] flex-1">
                    <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">User ID</label>
                    <input
                      v-model="addUserId"
                      type="text"
                      placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                      class="input-field font-mono text-sm"
                    />
                  </div>
                  <div>
                    <label class="mb-2 block text-xs font-semibold uppercase tracking-widest text-cypher-muted">角色</label>
                    <select v-model="addRole" class="input-field">
                      <option value="staff">工作人員</option>
                      <option value="admin">管理員</option>
                    </select>
                  </div>
                </div>
                <div v-if="addError" class="mt-3 flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3">
                  <p class="text-sm text-rose-300">{{ addError }}</p>
                </div>
                <div class="mt-4 flex gap-2">
                  <button
                    type="button"
                    class="btn-primary disabled:opacity-50"
                    :disabled="addSubmitting"
                    @click="submitAdd"
                  >
                    <span v-if="addSubmitting" class="flex items-center gap-2">
                      <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      處理中...
                    </span>
                    <span v-else>新增</span>
                  </button>
                  <button
                    type="button"
                    class="rounded-xl border border-cypher-border bg-cypher-surface px-4 py-2 text-sm font-medium text-gray-400 transition-colors hover:border-cypher-accent/40 hover:text-white disabled:opacity-50"
                    :disabled="addSubmitting"
                    @click="showAddForm = false; addError = null"
                  >
                    取消
                  </button>
                </div>
              </div>
            </div>
          </Transition>

          <!-- Members list header -->
          <div class="relative overflow-hidden rounded-2xl border border-white/10 bg-cypher-surface/90 shadow-card-glass backdrop-blur-md">
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cypher-accent/50 to-transparent" aria-hidden="true" />
            <div class="flex items-center justify-between border-b border-white/5 px-6 py-4">
              <h2 class="text-sm font-semibold text-white">成員列表</h2>
              <button
                v-if="!showAddForm"
                type="button"
                class="btn-primary py-1.5 text-sm"
                @click="showAddForm = true"
              >
                + 新增成員
              </button>
            </div>

            <!-- Loading -->
            <div v-if="loading" class="flex items-center gap-2 px-6 py-8 text-sm text-cypher-muted">
              <span class="h-4 w-4 animate-spin rounded-full border-2 border-cypher-muted border-t-transparent" />
              載入中…
            </div>

            <!-- Empty -->
            <p v-else-if="members.length === 0" class="px-6 py-8 text-center text-sm text-cypher-muted">
              尚無成員（擁有者會自動加入）
            </p>

            <!-- Member rows -->
            <ul v-else class="divide-y divide-white/5">
              <li
                v-for="m in members"
                :key="m.user_id"
                class="flex flex-wrap items-center gap-4 px-6 py-4 transition-colors hover:bg-white/[0.02]"
              >
                <!-- Identity -->
                <div class="min-w-0 flex-1">
                  <code class="block truncate font-mono text-xs text-gray-400" :title="m.user_id">
                    {{ m.user_id }}
                  </code>
                  <span
                    class="mt-1.5 inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold"
                    :class="m.role === 'owner'
                      ? 'border-cypher-accent/40 bg-cypher-accent/10 text-cypher-accent-bright'
                      : m.role === 'admin'
                        ? 'border-cypher-accent-cyan/40 bg-cypher-accent-cyan/10 text-cypher-accent-cyan'
                        : 'border-white/10 bg-white/5 text-gray-400'"
                  >
                    {{ roleLabel(m.role) }}
                  </span>
                </div>

                <!-- Edit mode -->
                <div v-if="editingUserId === m.user_id" class="flex shrink-0 items-center gap-2">
                  <select v-model="editRole" class="input-field py-1.5 text-sm">
                    <option value="owner">擁有者</option>
                    <option value="admin">管理員</option>
                    <option value="staff">工作人員</option>
                  </select>
                  <button
                    type="button"
                    class="btn-primary py-1.5 text-sm disabled:opacity-50"
                    :disabled="editSubmitting"
                    @click="submitEdit"
                  >
                    {{ editSubmitting ? "儲存中…" : "儲存" }}
                  </button>
                  <button
                    type="button"
                    class="rounded-lg border border-cypher-border px-3 py-1.5 text-sm text-gray-400 transition-colors hover:text-white disabled:opacity-50"
                    :disabled="editSubmitting"
                    @click="cancelEdit"
                  >
                    取消
                  </button>
                </div>

                <!-- View mode actions -->
                <div v-else class="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    class="rounded-lg border border-cypher-accent/30 px-3 py-1.5 text-xs font-medium text-cypher-accent transition-colors hover:bg-cypher-accent/10"
                    @click="startEdit(m)"
                  >
                    編輯角色
                  </button>
                  <button
                    type="button"
                    class="rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs font-medium text-rose-400 transition-colors hover:bg-rose-500/10 disabled:opacity-40"
                    :disabled="removingUserId === m.user_id || m.role === 'owner'"
                    :title="m.role === 'owner' ? '請先轉移擁有者再移除' : undefined"
                    @click="removeMember(m)"
                  >
                    {{ removingUserId === m.user_id ? "移除中…" : "移除" }}
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </div>

      </template>
    </div>
  </main>
</template>
