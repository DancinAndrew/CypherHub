# SEC-2：身份與資料保護（帳密、URL、敏感資料）

> **階段**：SEC-2（上線前安全強化）
> **狀態**：✅ 已完成
> **前置條件**：SEC-1 已完成（Referrer-Policy header 已在 SEC-1 設定）
> **參考規格**：[develop.md — SEC-2](develop.md#sec-2身份與資料保護-)

---

## 一、目標與範圍

### 目標

確保使用者的身份憑證（密碼、Token）與敏感資料（Email）不會透過 URL、日誌、回應 payload 或其他管道洩漏，並防止 open redirect 攻擊。

### Done 條件（來自 develop.md）

> 密碼不經手刻 API；URL 與 redirect 不含 email/密碼/token（重設密碼 hash 除外）；必要時加上 Referrer-Policy。

### 範圍內（In Scope）

| # | 項目 | 說明 |
|---|------|------|
| 1 | 密碼欄位 `type="password"` | 登入/註冊/重設密碼使用遮罩輸入 |
| 2 | 密碼不經後端 | 登入由 Supabase Auth 處理，後端僅轉發 |
| 3 | JWT 存放安全 | Token 在記憶體，非易被 XSS 讀取的位置 |
| 4 | URL 不含敏感資料 | query string 無 email/密碼/完整 token |
| 5 | Redirect 安全驗證 | 防止 open redirect 攻擊 |
| 6 | 重設密碼連結安全 | Supabase 一次性連結，使用後失效 |
| 7 | Referrer-Policy | 避免敏感路徑外洩至第三方 |

### 範圍外（Out of Scope）

- CSRF 防護 → 屬 SEC-3
- Rate Limiting → 已在 MVP-3 完成
- XSS 防護 → 屬 SEC-3
- Cookie 安全設定 → 目前未使用 cookie 儲存 token

---

## 二、現況分析

### ✅ 已通過（經審計確認）

| 項目 | 實作位置 | 說明 |
|------|----------|------|
| 密碼欄位 `type="password"` | `LoginView.vue:126`, `ResetPasswordView.vue:59,70` | 所有密碼欄位皆使用 `type="password"` + 正確 `autocomplete` |
| 密碼不經後端 | `blueprints/auth.py:111-119` | 後端 `/auth/login` 僅將密碼轉發給 Supabase Auth，不存儲不記錄 |
| JWT 存放 | `stores/auth.ts:14,19` | Token 在 Vue reactive state（記憶體）中，Supabase 管理持久 session |
| URL 不含敏感資料 | `router/index.ts` | 所有路由參數僅含 ID，無 email/密碼/token |
| 重設密碼連結 | `stores/auth.ts:101-107` | Supabase 處理，redirectTo 僅含 origin + path |
| Referrer-Policy | `backend/app/__init__.py:106` | SEC-1 已設定 `strict-origin-when-cross-origin` ✅ |
| SERVICE_ROLE_KEY 隔離 | `services/supabase_client.py` | 僅 server-side 使用，前端無暴露 |
| 錯誤訊息安全 | `domain/errors.py` | DB 錯誤映射為安全的用戶友善訊息 |

### ⚠️ 需修復

| 項目 | 風險等級 | 位置 | 說明 |
|------|----------|------|------|
| ~~Open Redirect~~ | ~~中~~ | ~~`LoginView.vue:87`~~ | ~~redirect 參數未驗證為相對路徑~~ ✅ 已修復 — `sanitizeRedirect()` |

---

## 三、Open Redirect 漏洞分析

### 問題描述

`LoginView.vue` 登入成功後，從 URL query 取得 `redirect` 參數直接傳給 `router.push()`：

```typescript
// LoginView.vue:87 — 目前程式碼
const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
await router.push(redirect);
```

攻擊者可構造惡意 URL：
```
https://cypherhub.com/login?redirect=https://evil.com/phishing
```

使用者登入後會被導向惡意網站（視 Vue Router 處理方式而定）。

### 影響

- 釣魚攻擊：導向仿冒登入頁面，二次竊取憑證
- 信任濫用：利用合法域名的信任度進行社工攻擊

### 相同模式出現位置

| 位置 | 程式碼 | 風險 |
|------|--------|------|
| `LoginView.vue:87` | `router.push(redirect)` | **需修復** — redirect 來自 URL query |
| `api/client.ts:39` | `window.location.href = /login?redirect=...` | 安全 — redirect 來自 `window.location.pathname`（自身路徑） |
| `EventDetailView.vue:200,231` | `query: { redirect: route.fullPath }` | 安全 — redirect 來自當前路由 |

---

## 四、開發計畫

### Task 1：修復 Open Redirect 漏洞（P0）

**修改檔案**：`frontend/src/views/LoginView.vue`

新增 redirect 參數驗證，確保僅允許相對路徑：

```typescript
function sanitizeRedirect(value: unknown): string {
  if (typeof value !== "string" || !value) return "/";
  // 僅允許以 / 開頭的相對路徑，排除 // 開頭（protocol-relative URL）
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  return "/";
}

const redirect = sanitizeRedirect(route.query.redirect);
await router.push(redirect);
```

**驗證規則**：
- 必須以 `/` 開頭（相對路徑）
- 不可以 `//` 開頭（防止 `//evil.com` protocol-relative URL）
- 非字串或空值預設為 `/`

### Task 2：後端 redirect 相關端點審查（P1）

**檢查範圍**：確認後端無任何端點接受 redirect URL 並進行重導向。

目前後端的 redirect 相關邏輯：
- ECPay callback return URL → 固定在環境變數 `ECPAY_RETURN_URL`，非用戶可控 ✅
- `FRONTEND_BASE_URL` → 環境變數，用於 email 連結 ✅

**結論**：後端無 open redirect 風險，無需修改。

### Task 3：撰寫測試（P0）

**新增檔案**：`frontend/src/utils/__tests__/sanitizeRedirect.test.ts`

測試 `sanitizeRedirect` 函式覆蓋以下案例：
- 正常相對路徑 `/events/123` → 通過
- 根路徑 `/` → 通過
- 帶 query 的路徑 `/events?q=test` → 通過
- 絕對 URL `https://evil.com` → 拒絕，回傳 `/`
- Protocol-relative `//evil.com` → 拒絕，回傳 `/`
- 空字串 → 回傳 `/`
- 非字串值 → 回傳 `/`

---

## 五、檔案變更清單

| 檔案 | 變更類型 | 說明 |
|------|----------|------|
| `frontend/src/utils/sanitizeRedirect.ts` | 新增 | redirect 參數驗證函式 |
| `frontend/src/views/LoginView.vue` | 修改 | 使用 `sanitizeRedirect` 驗證 redirect |
| `frontend/src/utils/__tests__/sanitizeRedirect.test.ts` | 新增 | 單元測試 |

**不需要 Migration**：純前端邏輯變更。
**不需要後端修改**：後端無 open redirect 風險。

---

## 六、測試計畫

### 6.1 單元測試（`sanitizeRedirect.test.ts`）

```typescript
describe("sanitizeRedirect", () => {
  // 允許的路徑
  it("allows root path", () => expect(sanitizeRedirect("/")).toBe("/"));
  it("allows relative path", () => expect(sanitizeRedirect("/events/123")).toBe("/events/123"));
  it("allows path with query", () => expect(sanitizeRedirect("/events?q=test")).toBe("/events?q=test"));
  it("allows path with hash", () => expect(sanitizeRedirect("/reset-password#token")).toBe("/reset-password#token"));

  // 拒絕的路徑
  it("rejects absolute URL", () => expect(sanitizeRedirect("https://evil.com")).toBe("/"));
  it("rejects http URL", () => expect(sanitizeRedirect("http://evil.com")).toBe("/"));
  it("rejects protocol-relative URL", () => expect(sanitizeRedirect("//evil.com")).toBe("/"));
  it("rejects javascript URL", () => expect(sanitizeRedirect("javascript:alert(1)")).toBe("/"));
  it("rejects data URL", () => expect(sanitizeRedirect("data:text/html,<h1>Hi</h1>")).toBe("/"));
  it("rejects empty string", () => expect(sanitizeRedirect("")).toBe("/"));

  // 非字串
  it("rejects null", () => expect(sanitizeRedirect(null)).toBe("/"));
  it("rejects undefined", () => expect(sanitizeRedirect(undefined)).toBe("/"));
  it("rejects number", () => expect(sanitizeRedirect(123)).toBe("/"));
});
```

### 6.2 建置驗證

```bash
cd frontend && npm run build  # TypeScript 編譯 + Vite 建置
```

### 6.3 手動驗證清單

| # | 驗證項目 | 步驟 | 預期結果 |
|---|----------|------|----------|
| 1 | 正常 redirect | 未登入 → 存取 `/events/123` → 被導向 `/login?redirect=/events/123` → 登入 | 回到 `/events/123` |
| 2 | 無 redirect | 直接存取 `/login` → 登入 | 回到 `/` |
| 3 | 惡意 redirect | 存取 `/login?redirect=https://evil.com` → 登入 | 回到 `/`（非 evil.com） |
| 4 | Protocol-relative | 存取 `/login?redirect=//evil.com` → 登入 | 回到 `/` |
| 5 | 密碼欄位遮罩 | 檢視登入頁、重設密碼頁 | 密碼以 `•••` 顯示 |
| 6 | URL 無敏感資料 | 瀏覽全站，檢查網址列 | 無 email/password/token 出現在 URL |
| 7 | Referrer-Policy | `curl -I https://api.example.com/api/v1/health` | 包含 `Referrer-Policy: strict-origin-when-cross-origin` |

---

## 七、執行順序

```
Step 1: Task 1 — 建立 sanitizeRedirect 函式 + 修改 LoginView.vue
Step 2: Task 3 — 撰寫並執行測試
Step 3: Task 2 — 後端審查確認（已在分析階段完成，僅需文件記錄）
Step 4: 建置驗證 + 文件更新
```

---

## 八、風險與注意事項

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| sanitizeRedirect 過於嚴格 | 正常的深層路徑被拒絕 | 測試覆蓋多種合法路徑格式 |
| Vue Router 行為差異 | `router.push` 對不同格式的 URL 處理方式可能不同 | 在 sanitizeRedirect 層級先過濾，不依賴 Router 行為 |
| 既有書籤/連結失效 | 不會 — 合法的相對路徑仍正常運作 | 僅拒絕非法的絕對 URL |
