# Frontend Vitest 測試套件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 為前端建立 57 個測試案例（utils + stores + component），並整合進 CI，達到 portfolio 展示水準。

**Architecture:** 使用 Vitest + @vue/test-utils，設定放在 `vite.config.ts` 的 `test` 區塊，測試檔案放在 `src/tests/` 目錄下分層組織。所有 Pinia store 測試透過 `setup.ts` 自動初始化乾淨實例；`auth store` 測試用 `vi.mock` mock 掉 Supabase 和 API client。

**Tech Stack:** vitest, @vue/test-utils, jsdom, TypeScript, Pinia

---

## 檔案清單

| 動作 | 路徑 | 說明 |
|------|------|------|
| Modify | `frontend/package.json` | 加 test scripts 與 devDependencies |
| Modify | `frontend/vite.config.ts` | 加 `test` 區塊 |
| Create | `frontend/src/tests/setup.ts` | Pinia 初始化 |
| Create | `frontend/src/tests/utils/sanitizeRedirect.test.ts` | 7 cases |
| Create | `frontend/src/tests/utils/errorMessages.test.ts` | 22 cases |
| Create | `frontend/src/tests/stores/error.test.ts` | 4 cases |
| Create | `frontend/src/tests/stores/organizer.test.ts` | 3 cases |
| Create | `frontend/src/tests/stores/auth.test.ts` | 9 cases |
| Create | `frontend/src/tests/components/DynamicForm.test.ts` | 12 cases |
| Modify | `.github/workflows/ci.yml` | 加 `npm run test` + `ruff format --check` |

---

## Task 1: 安裝套件與設定 Vitest

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: 安裝 devDependencies**

```bash
cd frontend && npm install --save-dev vitest @vue/test-utils jsdom @vitest/coverage-v8
```

預期輸出：`added N packages` 並更新 `package-lock.json`。

- [ ] **Step 2: 更新 `package.json` scripts**

在 `"scripts"` 區塊加入三行（`"build"` 行之後）：

```json
"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage"
```

完整 scripts 區塊結果：

```json
"scripts": {
  "dev": "vite",
  "build": "vue-tsc --noEmit && vite build",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage"
}
```

- [ ] **Step 3: 更新 `vite.config.ts`，加入 `test` 區塊**

完整檔案替換為：

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// SEC-1: 生產建置時檢查 API URL 是否使用 HTTPS
if (process.env.NODE_ENV === "production") {
  const apiUrl = process.env.VITE_API_BASE_URL || "";
  if (apiUrl && !apiUrl.startsWith("https://")) {
    console.warn(
      "⚠️  SEC-1: VITE_API_BASE_URL should use HTTPS in production:",
      apiUrl,
    );
  }
}

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
    globals: true,
  },
});
```

- [ ] **Step 4: 建立 `src/tests/setup.ts`**

```ts
import { beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";

beforeEach(() => {
  setActivePinia(createPinia());
});
```

- [ ] **Step 5: 驗證 Vitest 能啟動（尚無測試檔案也沒關係）**

```bash
cd frontend && npm run test
```

預期輸出類似：`No test files found, exiting with code 1` 或 `0 tests passed`。
若出現設定錯誤，根據錯誤訊息修正 `vite.config.ts`。

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/tests/setup.ts
git commit -m "chore(frontend): 安裝 Vitest 並設定測試環境"
```

---

## Task 2: `sanitizeRedirect` 測試（7 cases）

**Files:**
- Create: `frontend/src/tests/utils/sanitizeRedirect.test.ts`

- [ ] **Step 1: 建立測試檔案**

```ts
import { describe, it, expect } from "vitest";
import { sanitizeRedirect } from "../../utils/sanitizeRedirect";

describe("sanitizeRedirect", () => {
  it("正常相對路徑原樣回傳", () => {
    expect(sanitizeRedirect("/dashboard")).toBe("/dashboard");
  });

  it("根路徑原樣回傳", () => {
    expect(sanitizeRedirect("/")).toBe("/");
  });

  it("含 query string 的相對路徑原樣回傳", () => {
    expect(sanitizeRedirect("/events/123?q=abc")).toBe("/events/123?q=abc");
  });

  it("protocol-relative URL（//evil.com）回傳 /", () => {
    expect(sanitizeRedirect("//evil.com")).toBe("/");
  });

  it("absolute URL（https://evil.com）回傳 /", () => {
    expect(sanitizeRedirect("https://evil.com")).toBe("/");
  });

  it("空字串回傳 /", () => {
    expect(sanitizeRedirect("")).toBe("/");
  });

  it("undefined 回傳 /", () => {
    expect(sanitizeRedirect(undefined)).toBe("/");
  });
});
```

- [ ] **Step 2: 執行並確認 7 個 tests 全部通過**

```bash
cd frontend && npm run test -- src/tests/utils/sanitizeRedirect.test.ts
```

預期：`7 passed`。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/utils/sanitizeRedirect.test.ts
git commit -m "test(frontend): 新增 sanitizeRedirect 測試（7 cases）"
```

---

## Task 3: `errorMessages` 測試（22 cases）

**Files:**
- Create: `frontend/src/tests/utils/errorMessages.test.ts`

- [ ] **Step 1: 建立測試檔案**

```ts
import { describe, it, expect } from "vitest";
import { toApiErrorMessage, toAuthErrorMessage } from "../../utils/errorMessages";

// ─── helper：建構 axios-like error ──────────────────────────────────────────
function makeApiError(status: number, code: string, message: string, details?: unknown) {
  return {
    response: {
      status,
      data: { error: { code, message, details } },
    },
  };
}

function makeStatusError(status: number) {
  return { response: { status } };
}

// ─── toApiErrorMessage ───────────────────────────────────────────────────────
describe("toApiErrorMessage", () => {
  it("HTTP 429 → rate limit 訊息（不管 body）", () => {
    const msg = toApiErrorMessage(makeStatusError(429), "fallback");
    expect(msg).toBe("操作過於頻繁，請稍後再試。");
  });

  it("已知 code SOLD_OUT → 對應中文", () => {
    const err = makeApiError(400, "SOLD_OUT", "sold out");
    expect(toApiErrorMessage(err, "fallback")).toBe("票券已售完。");
  });

  it("已知 code EVENT_NOT_FOUND → 對應中文", () => {
    const err = makeApiError(404, "EVENT_NOT_FOUND", "not found");
    expect(toApiErrorMessage(err, "fallback")).toBe("找不到此活動。");
  });

  it("已知 code FORBIDDEN → 對應中文", () => {
    const err = makeApiError(403, "FORBIDDEN", "forbidden");
    expect(toApiErrorMessage(err, "fallback")).toBe("您沒有權限執行此操作。");
  });

  it("未知 code，有 message → <message> (<CODE>)", () => {
    const err = makeApiError(400, "SOME_UNKNOWN", "未知錯誤");
    expect(toApiErrorMessage(err, "fallback")).toBe("未知錯誤 (SOME_UNKNOWN)");
  });

  it("raw details 含 PERMISSION DENIED FOR FUNCTION → RPC 權限訊息", () => {
    const err = makeApiError(400, "DB_ERROR", "db error", { raw: "permission denied for function foo" });
    expect(toApiErrorMessage(err, "fallback")).toBe(
      "目前登入身分沒有執行此操作的權限，請重新登入後再試。",
    );
  });

  it("raw details 含 COULD NOT FIND THE FUNCTION → RPC 不存在訊息", () => {
    const err = makeApiError(400, "DB_ERROR", "db error", { raw: "could not find the function bar" });
    expect(toApiErrorMessage(err, "fallback")).toBe(
      "後端 RPC 函式不存在或版本不一致，請確認 migration 已完整套用。",
    );
  });

  it("raw details 字串含 SOLD_OUT → 票券已售完", () => {
    const err = makeApiError(400, "RPC_ERROR", "rpc failed", { raw: "SOLD_OUT: capacity exhausted" });
    expect(toApiErrorMessage(err, "fallback")).toBe("票券已售完。");
  });

  it("VALIDATION_ERROR + array details → 欄位名稱 + msg", () => {
    const err = makeApiError(422, "VALIDATION_ERROR", "驗證失敗", [
      { loc: ["body", "email"], msg: "field required" },
    ]);
    expect(toApiErrorMessage(err, "fallback")).toBe("驗證失敗: body.email field required");
  });

  it("VALIDATION_ERROR + object details with field → 欄位訊息", () => {
    const err = makeApiError(422, "VALIDATION_ERROR", "驗證失敗", { field: "ticket_type_id" });
    expect(toApiErrorMessage(err, "fallback")).toBe("驗證失敗: ticket_type_id");
  });

  it("有 message 但 code 為空 → 直接回傳 message", () => {
    const err = { response: { status: 500, data: { error: { code: "", message: "server exploded" } } } };
    expect(toApiErrorMessage(err, "fallback")).toBe("server exploded");
  });

  it("完全無 response，有 error.message → 回傳 error.message", () => {
    expect(toApiErrorMessage(new Error("network error"), "fallback")).toBe("network error");
  });

  it("完全無 response 且無 message → 回傳 fallback", () => {
    expect(toApiErrorMessage({}, "fallback")).toBe("fallback");
  });

  it("error 為 null → 回傳 fallback", () => {
    expect(toApiErrorMessage(null, "fallback")).toBe("fallback");
  });
});

// ─── toAuthErrorMessage ──────────────────────────────────────────────────────
describe("toAuthErrorMessage", () => {
  it("HTTP 429 → rate limit 訊息", () => {
    expect(toAuthErrorMessage(makeStatusError(429), "signin")).toBe(
      "操作過於頻繁，請稍後再試。",
    );
  });

  it("code AUTH_FAILED → 帳密錯誤訊息", () => {
    const err = makeApiError(401, "AUTH_FAILED", "auth failed");
    expect(toAuthErrorMessage(err, "signin")).toBe("登入失敗：帳號或密碼不正確。");
  });

  it("signin + HTTP 401（無 code）→ 帳密錯誤訊息", () => {
    expect(toAuthErrorMessage(makeStatusError(401), "signin")).toBe(
      "登入失敗：帳號或密碼不正確。",
    );
  });

  it("raw message invalid login credentials → 帳密錯誤訊息", () => {
    expect(toAuthErrorMessage({ message: "Invalid login credentials" }, "signin")).toBe(
      "登入失敗：帳號或密碼不正確。",
    );
  });

  it("raw message email not confirmed → 未驗證信箱訊息", () => {
    expect(toAuthErrorMessage({ message: "Email not confirmed" }, "signin")).toBe(
      "此帳號尚未完成信箱驗證，請先到信箱點擊確認連結。",
    );
  });

  it("raw message user already registered → 已註冊訊息", () => {
    expect(toAuthErrorMessage({ message: "User already registered" }, "signup")).toBe(
      "此 Email 已註冊，請直接 Sign In。",
    );
  });

  it("raw message password should be at least → 密碼太短", () => {
    expect(toAuthErrorMessage({ message: "Password should be at least 6 characters." }, "signup")).toBe(
      "密碼長度不足，至少需要 6 個字元。",
    );
  });

  it("無匹配，mode forgot → 預設重設密碼失敗訊息", () => {
    expect(toAuthErrorMessage({}, "forgot")).toBe(
      "無法寄送重設密碼信，請確認 Email 是否已註冊。",
    );
  });
});
```

- [ ] **Step 2: 執行並確認 22 個 tests 全部通過**

```bash
cd frontend && npm run test -- src/tests/utils/errorMessages.test.ts
```

預期：`22 passed`。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/utils/errorMessages.test.ts
git commit -m "test(frontend): 新增 errorMessages 測試（22 cases）"
```

---

## Task 4: `useErrorStore` 測試（4 cases）

**Files:**
- Create: `frontend/src/tests/stores/error.test.ts`

- [ ] **Step 1: 建立測試檔案**

```ts
import { describe, it, expect } from "vitest";
import { useErrorStore } from "../../stores/error";

describe("useErrorStore", () => {
  it("初始狀態 globalError 為 null", () => {
    const store = useErrorStore();
    expect(store.globalError).toBeNull();
  });

  it("setError(Error) → globalError 是 Error 實例且 message 正確", () => {
    const store = useErrorStore();
    store.setError(new Error("oops"));
    expect(store.globalError).toBeInstanceOf(Error);
    expect(store.globalError?.message).toBe("oops");
  });

  it("setError(string) → 包成 Error 實例", () => {
    const store = useErrorStore();
    store.setError("string error");
    expect(store.globalError).toBeInstanceOf(Error);
    expect(store.globalError?.message).toBe("string error");
  });

  it("clearError() → globalError 變 null", () => {
    const store = useErrorStore();
    store.setError(new Error("some error"));
    store.clearError();
    expect(store.globalError).toBeNull();
  });
});
```

- [ ] **Step 2: 執行並確認 4 個 tests 全部通過**

```bash
cd frontend && npm run test -- src/tests/stores/error.test.ts
```

預期：`4 passed`。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/stores/error.test.ts
git commit -m "test(frontend): 新增 useErrorStore 測試（4 cases）"
```

---

## Task 5: `useOrganizerStore` 測試（3 cases）

**Files:**
- Create: `frontend/src/tests/stores/organizer.test.ts`

- [ ] **Step 1: 建立測試檔案**

```ts
import { describe, it, expect } from "vitest";
import { useOrganizerStore } from "../../stores/organizer";

describe("useOrganizerStore", () => {
  it("初始狀態兩個值都是空字串", () => {
    const store = useOrganizerStore();
    expect(store.orgId).toBe("");
    expect(store.lastCreatedEventId).toBe("");
  });

  it("setOrgId('org-123') → orgId 更新", () => {
    const store = useOrganizerStore();
    store.setOrgId("org-123");
    expect(store.orgId).toBe("org-123");
  });

  it("setLastEventId('evt-456') → lastCreatedEventId 更新", () => {
    const store = useOrganizerStore();
    store.setLastEventId("evt-456");
    expect(store.lastCreatedEventId).toBe("evt-456");
  });
});
```

- [ ] **Step 2: 執行並確認 3 個 tests 全部通過**

```bash
cd frontend && npm run test -- src/tests/stores/organizer.test.ts
```

預期：`3 passed`。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/stores/organizer.test.ts
git commit -m "test(frontend): 新增 useOrganizerStore 測試（3 cases）"
```

---

## Task 6: `useAuthStore` 測試（9 cases）

**Files:**
- Create: `frontend/src/tests/stores/auth.test.ts`

- [ ] **Step 1: 建立測試檔案**

```ts
import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { useAuthStore } from "../../stores/auth";

// mock Supabase client
vi.mock("../../api/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      setSession: vi.fn(),
      signOut: vi.fn(),
      signUp: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      updateUser: vi.fn(),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } },
      })),
    },
  },
}));

// mock authLogin from API client
vi.mock("../../api/client", () => ({
  authLogin: vi.fn(),
}));

import { supabase } from "../../api/supabase";
import { authLogin } from "../../api/client";

const mockSession = {
  access_token: "token-abc",
  refresh_token: "refresh-xyz",
  expires_in: 3600,
  token_type: "bearer",
  user: { id: "user-1", email: "test@example.com" },
};

describe("useAuthStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("初始狀態：accessToken 為 null，isAuthenticated 為 false", () => {
    const store = useAuthStore();
    expect(store.accessToken).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it("session 有 access_token → accessToken 正確回傳，isAuthenticated 為 true", async () => {
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });
    const store = useAuthStore();
    await store.refreshSession();
    expect(store.accessToken).toBe("token-abc");
    expect(store.isAuthenticated).toBe(true);
  });

  it("clearSession() → session 與 user 都變 null", async () => {
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });
    const store = useAuthStore();
    await store.refreshSession();
    expect(store.accessToken).toBe("token-abc"); // 確認 session 已設入
    store.clearSession();
    expect(store.accessToken).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it("signOut() 成功 → session 與 user 清空", async () => {
    (supabase.auth.signOut as Mock).mockResolvedValue({ error: null });
    const store = useAuthStore();
    await store.signOut();
    expect(store.accessToken).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it("signOut() Supabase 拋錯 → store re-throw", async () => {
    (supabase.auth.signOut as Mock).mockResolvedValue({ error: new Error("network") });
    const store = useAuthStore();
    await expect(store.signOut()).rejects.toThrow("network");
  });

  it("signIn() 全部 mock 成功 → session 有值", async () => {
    (authLogin as Mock).mockResolvedValue({
      access_token: "token-abc",
      refresh_token: "refresh-xyz",
    });
    (supabase.auth.setSession as Mock).mockResolvedValue({ data: {}, error: null });
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });
    const store = useAuthStore();
    await store.signIn("test@example.com", "password123");
    expect(authLogin).toHaveBeenCalledWith("test@example.com", "password123");
    expect(store.accessToken).toBe("token-abc");
  });

  it("signIn() authLogin mock 拋錯 → store re-throw", async () => {
    (authLogin as Mock).mockRejectedValue(new Error("auth failed"));
    const store = useAuthStore();
    await expect(store.signIn("test@example.com", "wrong")).rejects.toThrow("auth failed");
  });

  it("signUp() 有 session → requiresEmailConfirmation 為 false", async () => {
    (supabase.auth.signUp as Mock).mockResolvedValue({
      data: { session: mockSession, user: mockSession.user },
      error: null,
    });
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });
    const store = useAuthStore();
    const result = await store.signUp("new@example.com", "password123");
    expect(result.requiresEmailConfirmation).toBe(false);
  });

  it("signUp() 無 session → requiresEmailConfirmation 為 true", async () => {
    (supabase.auth.signUp as Mock).mockResolvedValue({
      data: { session: null, user: { id: "user-1" } },
      error: null,
    });
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: null },
      error: null,
    });
    const store = useAuthStore();
    const result = await store.signUp("new@example.com", "password123");
    expect(result.requiresEmailConfirmation).toBe(true);
  });
});
```

- [ ] **Step 2: 執行並確認 9 個 tests 全部通過**

```bash
cd frontend && npm run test -- src/tests/stores/auth.test.ts
```

預期：`9 passed`。

若 `clearSession` 的 test 出現型別問題，改用：
```ts
store.session = mockSession as never;
```
根據實際錯誤訊息調整存取方式，目標是讓 `session.value` 有值後呼叫 `clearSession()`。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/stores/auth.test.ts
git commit -m "test(frontend): 新增 useAuthStore 測試（9 cases）"
```

---

## Task 7: `DynamicForm` component 測試（12 cases）

**Files:**
- Create: `frontend/src/tests/components/DynamicForm.test.ts`

- [ ] **Step 1: 建立測試檔案**

```ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import DynamicForm from "../../components/DynamicForm.vue";
import type { FormField, FormSchemaDefinition } from "../../api/client";

function makeSchema(fields: FormField[]): FormSchemaDefinition {
  return { version: 1, fields };
}

function field(overrides: Partial<FormField> & { key: string; label: string; type: FormField["type"] }): FormField {
  return { required: false, ...overrides };
}

describe("DynamicForm", () => {
  it("text type → 渲染 <input type='text'>", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "name", label: "Name", type: "text" })]),
        modelValue: { name: "" },
      },
    });
    expect(wrapper.find("input[type='text']").exists()).toBe(true);
  });

  it("email type → 渲染 <input type='email'>", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "email", label: "Email", type: "email" })]),
        modelValue: { email: "" },
      },
    });
    expect(wrapper.find("input[type='email']").exists()).toBe(true);
  });

  it("number type → 渲染 <input type='number'>", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "age", label: "Age", type: "number" })]),
        modelValue: { age: "" },
      },
    });
    expect(wrapper.find("input[type='number']").exists()).toBe(true);
  });

  it("single_select → 渲染 <select> + 正確 option 數量", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "style", label: "Style", type: "single_select", options: ["Hiphop", "Popping", "Locking"] }),
        ]),
        modelValue: { style: "" },
      },
    });
    expect(wrapper.find("select").exists()).toBe(true);
    // 3 options + 1 placeholder "Select"
    expect(wrapper.findAll("option")).toHaveLength(4);
  });

  it("multi_select → 渲染對應數量的 checkbox", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "styles", label: "Styles", type: "multi_select", options: ["Hiphop", "Popping"] }),
        ]),
        modelValue: { styles: [] },
      },
    });
    expect(wrapper.findAll("input[type='checkbox']")).toHaveLength(2);
  });

  it("checkbox type → 渲染單一 checkbox", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "agree", label: "Agree", type: "checkbox" })]),
        modelValue: { agree: false },
      },
    });
    expect(wrapper.find("input[type='checkbox']").exists()).toBe(true);
  });

  it("required 欄位 → DOM 中有 * 標記", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "name", label: "Name", type: "text", required: true })]),
        modelValue: { name: "" },
      },
    });
    expect(wrapper.text()).toContain("*");
  });

  it("help_text 有值 → 渲染說明文字", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "name", label: "Name", type: "text", help_text: "請填寫真實姓名" }),
        ]),
        modelValue: { name: "" },
      },
    });
    expect(wrapper.text()).toContain("請填寫真實姓名");
  });

  it("text input 觸發 input 事件 → emit update:modelValue 含正確 key/value", async () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "name", label: "Name", type: "text" })]),
        modelValue: { name: "" },
      },
    });
    await wrapper.find("input").setValue("Andrew");
    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toEqual({ name: "Andrew" });
  });

  it("select 觸發 change 事件 → emit update:modelValue 含正確 value", async () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "style", label: "Style", type: "single_select", options: ["Hiphop", "Popping"] }),
        ]),
        modelValue: { style: "" },
      },
    });
    await wrapper.find("select").setValue("Hiphop");
    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toEqual({ style: "Hiphop" });
  });

  it("multi_select 勾選新項目 → emit 陣列中包含該選項", async () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "styles", label: "Styles", type: "multi_select", options: ["Hiphop", "Popping"] }),
        ]),
        modelValue: { styles: [] },
      },
    });
    await wrapper.findAll("input[type='checkbox']")[0].trigger("change");
    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    expect((emitted![0][0] as Record<string, unknown>)["styles"]).toContain("Hiphop");
  });

  it("disabled=true → 所有 input 有 disabled 屬性", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "name", label: "Name", type: "text" }),
          field({ key: "age", label: "Age", type: "number" }),
        ]),
        modelValue: { name: "", age: "" },
        disabled: true,
      },
    });
    wrapper.findAll("input").forEach((input) => {
      expect(input.attributes("disabled")).toBeDefined();
    });
  });
});
```

- [ ] **Step 2: 執行並確認 12 個 tests 全部通過**

```bash
cd frontend && npm run test -- src/tests/components/DynamicForm.test.ts
```

預期：`12 passed`。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/components/DynamicForm.test.ts
git commit -m "test(frontend): 新增 DynamicForm component 測試（12 cases）"
```

---

## Task 8: 全部測試一次跑過 + 確認總數

- [ ] **Step 1: 執行全部測試**

```bash
cd frontend && npm run test
```

預期：`57 passed`（7 + 22 + 4 + 3 + 9 + 12）。

若有 fail，根據錯誤訊息修正對應測試檔案，不修改 source code（測試必須通過現有程式邏輯）。

- [ ] **Step 2: 確認 build 仍然通過**

```bash
cd frontend && npm run build
```

預期：`✓ built in Xs`，無 TypeScript 錯誤。

---

## Task 9: CI 整合

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: 更新 CI 設定**

`.github/workflows/ci.yml` 完整替換為：

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: "backend/requirements.txt"
      - run: pip install -r backend/requirements.txt
      - run: cd backend && ruff check .
      - run: cd backend && ruff format --check .
      - run: cd backend && pytest -q -m "not integration"

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test
      - run: cd frontend && npm run build
```

- [ ] **Step 2: 確認本地 backend lint 也能通過（避免 CI 在 ruff format 這步 fail）**

```bash
cd backend && ruff check . && ruff format --check .
```

若 `ruff format --check .` 出現 diff，先跑 `ruff format .` 修正，再確認 `--check` 通過。

- [ ] **Step 3: Commit CI 設定**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: 補上前端測試與 ruff format check"
```

- [ ] **Step 4: Push，觀察 GitHub Actions 結果**

```bash
git push
```

到 GitHub repo 的 Actions 頁確認兩個 job 都綠燈。

---

## 完成標準

- [ ] `cd frontend && npm run test` 輸出 `57 passed`
- [ ] `cd frontend && npm run build` 無錯誤
- [ ] GitHub Actions CI 兩個 job 全綠
- [ ] `cd backend && ruff format --check .` 通過
