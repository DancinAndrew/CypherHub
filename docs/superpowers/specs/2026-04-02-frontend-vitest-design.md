# Frontend Vitest 測試套件設計

**日期：** 2026-04-02  
**目標：** 補強前端測試覆蓋，達到 portfolio 展示水準（工程師 + 客戶兩者都有說服力）  
**方案：** 方案 C — utils + stores + component tests + CI 整合

---

## 背景

現有後端有 30+ 個測試檔，前端測試為零。`package.json` 目前無任何測試相關套件。這個不對稱在技術 reviewer 眼中是明顯缺口，需補齊。

---

## 技術選型

| 套件 | 版本策略 | 用途 |
|------|----------|------|
| `vitest` | latest | 測試 runner，Vite 原生，零額外設定 |
| `@vue/test-utils` | latest | Vue component 掛載 + 事件互動 |
| `jsdom` | latest | 瀏覽器環境模擬 |
| `@vitest/coverage-v8` | latest | 覆蓋率報告（選用） |

全部放入 `devDependencies`。

---

## 設定方式

### vite.config.ts

在現有 `defineConfig` 內加入 `test` 區塊（不另建 `vitest.config.ts`）：

```ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: { host: "0.0.0.0", port: 5173, strictPort: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
    globals: true,
  },
});
```

### src/tests/setup.ts

```ts
import { setActivePinia, createPinia } from "pinia";
import { beforeEach } from "vitest";

beforeEach(() => {
  setActivePinia(createPinia());
});
```

每個 test 都拿到乾淨的 Pinia 實例，store 狀態不互相汙染。

### package.json scripts

```json
"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage"
```

---

## 測試檔案結構

```
frontend/src/tests/
├── setup.ts
├── utils/
│   ├── sanitizeRedirect.test.ts
│   └── errorMessages.test.ts
├── stores/
│   ├── error.test.ts
│   ├── organizer.test.ts
│   └── auth.test.ts
└── components/
    └── DynamicForm.test.ts
```

---

## 測試案例清單

### `utils/sanitizeRedirect.test.ts`（7 cases）

測試對象：`sanitizeRedirect(value: unknown): string`  
用途：SEC-2 open redirect 防護，只允許以 `/` 開頭的相對路徑。

| 輸入 | 預期輸出 | 說明 |
|------|----------|------|
| `"/dashboard"` | `"/dashboard"` | 正常相對路徑 |
| `"/"` | `"/"` | 根路徑 |
| `"/events/123?q=abc"` | `"/events/123?q=abc"` | 含 query string |
| `"//evil.com"` | `"/"` | protocol-relative URL 阻擋 |
| `"https://evil.com"` | `"/"` | absolute URL 阻擋 |
| `""` | `"/"` | 空字串 |
| `undefined` | `"/"` | 非字串型別 |

---

### `utils/errorMessages.test.ts`（22 cases）

#### `toApiErrorMessage(error, fallback)`（14 cases）

| 情境 | 預期輸出 |
|------|----------|
| HTTP status 429 | rate limit 中文訊息 |
| 已知 code `SOLD_OUT` | `"票券已售完。"` |
| 已知 code `EVENT_NOT_FOUND` | `"找不到此活動。"` |
| 已知 code `FORBIDDEN` | `"您沒有權限執行此操作。"` |
| 未知 code，有 message | `"<message> (<CODE>)"` |
| raw details 含 `PERMISSION DENIED FOR FUNCTION` | RPC 權限訊息 |
| raw details 含 `COULD NOT FIND THE FUNCTION` | RPC 不存在訊息 |
| raw message 含 `SOLD_OUT`（從 raw 匹配） | `"票券已售完。"` |
| `VALIDATION_ERROR` + array details | `"<message>: <loc> <msg>"` |
| `VALIDATION_ERROR` + object details with `field` | `"<message>: <field>"` |
| 有 message 但無 code | 直接回傳 message |
| 完全無 response，有 error.message | 回傳 error.message |
| 完全無 response，無 message | 回傳 fallback |
| error 為 null | 回傳 fallback |

#### `toAuthErrorMessage(error, mode)`（8 cases）

| 情境 | mode | 預期輸出 |
|------|------|----------|
| HTTP 429 | `"signin"` | rate limit 訊息 |
| code `AUTH_FAILED` | `"signin"` | 帳密錯誤訊息 |
| HTTP 401 | `"signin"` | 帳密錯誤訊息 |
| raw `invalid login credentials` | `"signin"` | 帳密錯誤訊息 |
| raw `email not confirmed` | `"signin"` | 未驗證信箱訊息 |
| raw `user already registered` | `"signup"` | 已註冊訊息 |
| raw `password should be at least` | `"signup"` | 密碼太短訊息 |
| 無匹配，mode `"forgot"` | `"forgot"` | 預設重設密碼失敗訊息 |

---

### `stores/error.test.ts`（4 cases）

測試對象：`useErrorStore`

| 情境 | 預期 |
|------|------|
| 初始狀態 | `globalError` 為 null |
| `setError(new Error("oops"))` | `globalError.value` 是 Error 實例，message 為 `"oops"` |
| `setError("string error")` | 包成 `new Error("string error")` |
| `clearError()` 後 | `globalError.value` 為 null |

---

### `stores/organizer.test.ts`（3 cases）

測試對象：`useOrganizerStore`

| 情境 | 預期 |
|------|------|
| 初始狀態 | `orgId` 與 `lastCreatedEventId` 都為空字串 |
| `setOrgId("org-123")` | `orgId.value === "org-123"` |
| `setLastEventId("evt-456")` | `lastCreatedEventId.value === "evt-456"` |

---

### `stores/auth.test.ts`（9 cases）

測試對象：`useAuthStore`  
Mock 對象：`../api/supabase`（`supabase.auth.*`）、`../api/client`（`authLogin`）

| 情境 | 預期 |
|------|------|
| 初始：session 為 null | `accessToken` 為 null，`isAuthenticated` 為 false |
| session 有 access_token | `accessToken` 回傳 token，`isAuthenticated` 為 true |
| `clearSession()` | `session` 與 `user` 都變 null |
| `signOut()` — Supabase mock 成功 | `session` 與 `user` 清空 |
| `signOut()` — Supabase mock 拋錯 | store 應 re-throw |
| `signIn()` — 全部 mock 成功 | 呼叫 `authLogin`、`setSession`、`refreshSession`，session 有值 |
| `signIn()` — `authLogin` mock 拋錯 | store 應 re-throw |
| `signUp()` — Supabase mock 成功，有 session | `requiresEmailConfirmation === false` |
| `signUp()` — Supabase mock 成功，無 session | `requiresEmailConfirmation === true` |

---

### `components/DynamicForm.test.ts`（12 cases）

測試對象：`DynamicForm.vue`  
使用 `@vue/test-utils` `mount()`

| 情境 | 預期 |
|------|------|
| `text` type 欄位 | 渲染 `<input type="text">` |
| `email` type 欄位 | 渲染 `<input type="email">` |
| `number` type 欄位 | 渲染 `<input type="number">` |
| `single_select` / `dropdown` 欄位 | 渲染 `<select>` + 正確 `<option>` 數量 |
| `multi_select` 欄位 | 渲染對應數量的 checkbox |
| `checkbox` 欄位 | 渲染單一 checkbox |
| `required` 欄位 | DOM 中有 `*` 標記 |
| `help_text` 有值 | 渲染說明文字 |
| text input 觸發 `input` 事件 | emit `update:modelValue`，含正確 key/value |
| select 觸發 `change` 事件 | emit `update:modelValue`，含正確 value |
| `toggleMultiOption`：勾選新項目 | emit 陣列中包含該選項 |
| `disabled=true` | 所有 input/select 有 `disabled` 屬性 |

---

## 總計

| 檔案 | Cases |
|------|-------|
| `sanitizeRedirect.test.ts` | 7 |
| `errorMessages.test.ts` | 22 |
| `error.test.ts` | 4 |
| `organizer.test.ts` | 3 |
| `auth.test.ts` | 9 |
| `DynamicForm.test.ts` | 12 |
| **合計** | **57** |

---

## CI 整合

`.github/workflows/ci.yml` 修改兩處：

**frontend job** — 在 `npm ci` 後、`npm run build` 前加：

```yaml
- run: cd frontend && npm run test
```

**backend job** — 補上遺漏的 format check：

```yaml
- run: cd backend && ruff format --check .
```

最終 CI 流程：

```
backend:  checkout → setup python → pip install → ruff check → ruff format --check → pytest
frontend: checkout → setup node  → npm ci      → npm test   → npm run build
```

---

## 不在此次範圍

- E2E 測試（Playwright）
- 覆蓋率 badge（`@vitest/coverage-v8` 安裝完成後可選擇性加）
- `LiveProgressBar.vue` component test（邏輯與 `useEventProgress` 綁定緊密，需額外 mock Supabase Realtime，成本高）
