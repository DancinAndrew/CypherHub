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
  <main class="mx-auto max-w-3xl px-4 py-12">
    <header>
      <h1 class="font-street text-3xl tracking-widest text-white">成員管理</h1>
      <p class="mt-2 text-cypher-muted">管理主辦方成員與角色（僅 owner/admin 可操作）</p>
    </header>

    <div v-if="orgsAdmin.length === 0" class="card mt-8 p-6">
      <p class="text-cypher-muted">您目前非任何主辦方的 owner 或 admin，無法管理成員。</p>
    </div>

    <template v-else>
      <div class="mt-6">
        <label class="block text-sm text-cypher-muted">選擇主辦方</label>
        <select
          v-model="selectedOrgId"
          class="mt-1 w-full rounded-lg border border-cypher-muted/40 bg-cypher-dark px-4 py-2 text-white focus:border-cypher-accent focus:outline-none"
        >
          <option value="">-- 請選擇 --</option>
          <option v-for="o in orgsAdmin" :key="o.id" :value="o.id">
            {{ o.name }}（{{ roleLabel(o.role) }}）
          </option>
        </select>
      </div>

      <p v-if="loadError" class="mt-4 text-sm text-red-400">{{ loadError }}</p>

      <div v-if="selectedOrgId && !loadError" class="mt-6">
        <div class="flex items-center justify-between">
          <h2 class="font-display text-lg font-semibold text-white">成員列表</h2>
          <button
            v-if="!showAddForm"
            type="button"
            class="btn-primary text-sm"
            @click="showAddForm = true"
          >
            新增成員
          </button>
        </div>

        <div v-if="showAddForm" class="card mt-4 space-y-4 p-4">
          <h3 class="font-medium text-white">新增成員</h3>
          <p class="text-xs text-cypher-muted">需已註冊使用者之 User ID（UUID），可於其個人設定或後台查詢。</p>
          <div class="flex flex-wrap gap-4">
            <div class="min-w-[200px] flex-1">
              <label class="block text-sm text-cypher-muted">User ID</label>
              <input
                v-model="addUserId"
                type="text"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                class="mt-1 w-full rounded border border-cypher-muted/40 bg-cypher-dark px-3 py-2 text-white focus:border-cypher-accent focus:outline-none"
              />
            </div>
            <div>
              <label class="block text-sm text-cypher-muted">角色</label>
              <select
                v-model="addRole"
                class="mt-1 rounded border border-cypher-muted/40 bg-cypher-dark px-3 py-2 text-white focus:border-cypher-accent focus:outline-none"
              >
                <option value="staff">工作人員</option>
                <option value="admin">管理員</option>
              </select>
            </div>
            <div class="flex items-end gap-2">
              <button
                type="button"
                class="btn-primary"
                :disabled="addSubmitting"
                @click="submitAdd"
              >
                {{ addSubmitting ? "處理中..." : "新增" }}
              </button>
              <button
                type="button"
                class="btn-secondary"
                :disabled="addSubmitting"
                @click="showAddForm = false; addError = null"
              >
                取消
              </button>
            </div>
          </div>
          <p v-if="addError" class="text-sm text-red-400">{{ addError }}</p>
        </div>

        <div v-if="loading" class="mt-4 text-cypher-muted">載入中...</div>
        <div v-else class="mt-4 space-y-2">
          <div
            v-for="m in members"
            :key="m.user_id"
            class="card flex items-center justify-between gap-4 p-4"
          >
            <div class="min-w-0 flex-1">
              <code class="text-sm text-cypher-accent/80">{{ m.user_id }}</code>
              <span class="ml-2 rounded bg-cypher-muted/20 px-2 py-0.5 text-xs text-cypher-muted">
                {{ roleLabel(m.role) }}
              </span>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <template v-if="editingUserId === m.user_id">
                <select
                  v-model="editRole"
                  class="rounded border border-cypher-muted/40 bg-cypher-dark px-2 py-1 text-sm text-white focus:border-cypher-accent focus:outline-none"
                >
                  <option value="owner">擁有者</option>
                  <option value="admin">管理員</option>
                  <option value="staff">工作人員</option>
                </select>
                <button
                  type="button"
                  class="btn-primary text-sm"
                  :disabled="editSubmitting"
                  @click="submitEdit"
                >
                  儲存
                </button>
                <button
                  type="button"
                  class="btn-secondary text-sm"
                  :disabled="editSubmitting"
                  @click="cancelEdit"
                >
                  取消
                </button>
              </template>
              <template v-else>
                <button
                  type="button"
                  class="text-sm text-cypher-accent hover:underline"
                  @click="startEdit(m)"
                >
                  編輯角色
                </button>
                <button
                  type="button"
                  class="text-sm text-red-400 hover:underline disabled:opacity-50"
                  :disabled="removingUserId === m.user_id || m.role === 'owner'"
                  :title="m.role === 'owner' ? '請先轉移擁有者再移除' : undefined"
                  @click="removeMember(m)"
                >
                  {{ removingUserId === m.user_id ? "移除中..." : "移除" }}
                </button>
              </template>
            </div>
          </div>
          <p v-if="members.length === 0" class="text-cypher-muted">尚無成員（擁有者會自動加入）</p>
        </div>
      </div>
    </template>
  </main>
</template>
