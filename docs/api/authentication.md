# 認證與權限機制

> 本文件說明 CypherHub 的完整認證流程、Token 管理策略、以及四層權限模型。
> 對應原始碼：`backend/app/services/auth_service.py`、`backend/app/blueprints/auth.py`、`frontend/src/stores/auth.ts`。

---

## 一、認證架構總覽

```
┌────────────┐        ┌────────────────┐        ┌──────────────┐
│  Frontend  │──JWT──▶│  Flask Backend │──JWT──▶│  Supabase    │
│  (Vue 3)   │◀──────│  (API Server)  │◀──────│  (Auth + DB) │
└────────────┘        └────────────────┘        └──────────────┘
```

- **身份提供者（IdP）**：Supabase Auth（基於 GoTrue）
- **Token 格式**：JWT（JSON Web Token），由 Supabase 簽發
- **傳遞方式**：HTTP `Authorization: Bearer <access_token>`
- **驗證方式**：Backend 呼叫 `supabase.auth.get_user(jwt)` 驗證 token 有效性

---

## 二、登入流程

### 2.1 標準登入（Email + Password）

```
Frontend                    Backend                     Supabase
   │                          │                            │
   │  POST /api/v1/auth/login │                            │
   │  { email, password }     │                            │
   │─────────────────────────▶│                            │
   │                          │  sign_in_with_password()   │
   │                          │───────────────────────────▶│
   │                          │  { access_token,           │
   │                          │    refresh_token, user }   │
   │                          │◀───────────────────────────│
   │  { access_token,         │                            │
   │    refresh_token, user } │                            │
   │◀─────────────────────────│                            │
   │                          │                            │
   │  supabase.auth.setSession({ access_token,             │
   │                              refresh_token })         │
   │──────────────────────────────────────────────────────▶│
   │                                                       │
```

**為什麼不直接用 Supabase Client 登入？**

登入經由 Backend proxy（`POST /api/v1/auth/login`），原因：
1. Backend 可施加 **Rate Limiting**（10 req/min），防暴力破解
2. 統一錯誤格式為 `AppError` 標準回應
3. 未來可擴充登入前後邏輯（如 audit log、登入通知）

### 2.2 Login API

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "mypassword"
}
```

**成功回應（200）**：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "v1.MjA1YzNm...",
  "expires_in": 3600,
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "aud": "authenticated",
    "role": "authenticated"
  }
}
```

**Rate Limit**：`10 per minute`（超過回傳 429）

### 2.3 註冊

註冊直接透過前端 Supabase Client：

```typescript
// frontend/src/stores/auth.ts
const { data, error } = await supabase.auth.signUp({ email, password });
```

- 若 Supabase Dashboard 啟用 Email Confirmation，`data.session` 為 `null`，使用者需先驗證信箱
- 驗證後前端呼叫 `refreshSession()` 取得 session

### 2.4 忘記密碼

```typescript
await supabase.auth.resetPasswordForEmail(email, {
  redirectTo: `${window.location.origin}/reset-password`
});
```

使用者點擊信中連結後導向 `/reset-password`，再呼叫：

```typescript
await supabase.auth.updateUser({ password: newPassword });
```

> `redirectTo` 需在 Supabase Dashboard → Auth → URL Configuration → Redirect URLs 中設定。

---

## 三、Token 管理

### 3.1 Token 結構

Supabase JWT payload 包含：

| 欄位 | 說明 |
|------|------|
| `sub` | 使用者 UUID（即 `auth.users.id`） |
| `email` | 使用者信箱 |
| `aud` | 固定 `"authenticated"` |
| `role` | 固定 `"authenticated"`（Supabase 層級，非業務角色） |
| `exp` | 到期時間（Unix timestamp） |
| `iat` | 簽發時間 |

### 3.2 Token 生命週期

| Token | 預設有效期 | 用途 |
|-------|-----------|------|
| `access_token` | 1 小時（3600s） | API 請求認證 |
| `refresh_token` | 長期（由 Supabase 管理） | 換發新 access_token |

### 3.3 自動 Refresh

前端透過 Supabase JS Client 的 `onAuthStateChange` 自動處理 token refresh：

```typescript
// frontend/src/stores/auth.ts
supabase.auth.onAuthStateChange((_event, nextSession) => {
  session.value = nextSession;       // 自動更新 token
  user.value = nextSession?.user ?? null;
});
```

Supabase Client 會在 `access_token` 即將過期時自動使用 `refresh_token` 換發新 token。前端不需手動處理。

### 3.4 前端 Interceptor 自動帶 Token

```typescript
// frontend/src/api/client.ts
client.interceptors.request.use((config) => {
  const authStore = useAuthStore(pinia);
  const token = authStore.accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

所有 API 請求自動從 auth store 取 `accessToken` 並帶入 `Authorization` header。

### 3.5 401 自動登出

```typescript
// frontend/src/api/client.ts — response interceptor
if (err.response?.status === 401) {
  // 登入請求的 401 不導向（讓 LoginView 顯示錯誤）
  if (!isLoginRequest) {
    authStore.clearSession();
    window.location.href = `/login?redirect=${encodeURIComponent(path)}`;
  }
}
```

非登入請求收到 401 時，自動清除 session 並導向登入頁（保留原路徑作 redirect）。

---

## 四、Backend 認證機制

### 4.1 `@require_auth` Decorator

所有需登入的 API 端點使用 `@require_auth`：

```python
# backend/app/services/auth_service.py
@wraps(func)
def wrapped(*args, **kwargs):
    # 1. 從 header 取 JWT
    auth_header = request.headers.get("Authorization", "")
    jwt = auth_header.replace("Bearer ", "", 1).strip()

    # 2. 向 Supabase 驗證 token（supabase.auth.get_user）
    user = supabase_client.get_user(jwt)

    # 3. 將使用者資訊存入 Flask g 物件
    g.jwt = jwt            # 原始 JWT（供後續 Supabase 查詢使用）
    g.user = user          # 完整 user dict
    g.user_id = str(user_id)  # 使用者 UUID

    return func(*args, **kwargs)
```

### 4.2 Flask `g` 物件中的欄位

通過 `@require_auth` 後，以下欄位可在 blueprint/service 中使用：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `g.jwt` | `str` | 原始 access_token，傳給 `supabase_client.authed_client(jwt)` 執行帶身份的 DB 查詢 |
| `g.user` | `dict` | Supabase user 物件（含 `id`、`email`、`aud`、`identities` 等） |
| `g.user_id` | `str` | 使用者 UUID（從 `user["id"]` 或 `user["sub"]` 取得） |

> **安全原則**：`user_id` 永遠從 JWT 解析，**禁止**信任 client 傳入的 `user_id`。

### 4.3 Supabase Client 三種模式

```python
# backend/app/services/supabase_client.py

# 1. 公開操作（無身份）— 用於登入、公開活動列表
client = supabase_client.public_client()

# 2. 帶使用者身份 — 受 RLS 約束，最常用
client = supabase_client.authed_client(jwt)

# 3. Service Role — 繞過 RLS，僅限 server-side 內部操作
client = supabase_client.service_role_client()
```

| 模式 | 使用場景 | RLS |
|------|----------|-----|
| `public_client()` | 登入、公開列表 | 套用 anon 政策 |
| `authed_client(jwt)` | 使用者操作（CRUD） | 套用 authenticated 政策 |
| `service_role_client()` | 背景任務、Admin 操作、Email 查詢 | **繞過** RLS |

> **安全原則**：`SERVICE_ROLE_KEY` 禁止出現在 frontend、log、API response 中。

---

## 五、四層權限模型

CypherHub 有四個權限層級，由低到高：

```
Public（未登入）
  └── Authenticated（已登入使用者）
        └── Organizer（主辦方成員：owner / admin / staff）
              └── Platform Admin（平台管理員）
```

### 5.1 Public — 未登入

無需 `@require_auth`，可存取：
- `GET /api/v1/events` — 活動列表
- `GET /api/v1/events/:id` — 活動詳情
- `POST /api/v1/auth/login` — 登入
- `POST /api/v1/webhooks/ecpay` — ECPay 回呼（透過 CheckMacValue 驗證）

### 5.2 Authenticated — 已登入使用者

使用 `@require_auth`，可存取：
- `GET /api/v1/me/tickets` — 我的票券
- `POST /api/v1/registrations` — 報名/購票
- `GET /api/v1/orders/:id` — 訂單詳情
- `GET /api/v1/me/profile` — 個人資料
- 等所有需登入的端點

### 5.3 Organizer — 主辦方成員

在 `@require_auth` 之上，額外透過 `organizer_members` 表檢查：

| 角色 | 可執行操作 | 檢查方式 |
|------|-----------|----------|
| **owner** | 全部（含成員管理、轉讓擁有權） | `_get_org_role()` 回傳 `"owner"` |
| **admin** | 建立/編輯活動、票種、表單、查看名單、核銷、管理 staff | `require_org_admin()` 允許 `owner` + `admin` |
| **staff** | 僅核銷、查看名單 | `require_event_member()` 允許所有角色 |

**權限檢查函式**（在 `events_service.py`）：

```python
# 任何成員皆可（owner/admin/staff）
events_service.require_event_member(jwt, event_id, user_id)

# 僅 owner + admin（staff 會拋 STAFF_CANNOT_MANAGE）
events_service.require_org_admin(jwt, org_id, user_id)

# 僅 owner + admin，且透過 event_id 反查 org
events_service.require_event_admin(jwt, event_id, user_id)
```

**額外限制**：
- MVP-3.2 入駐審核：`_require_org_approved()` 確認 `approval_status = 'approved'` 才可建活動
- owner 不可刪除自己（若為唯一 owner）
- admin 不可修改 owner 的 role

### 5.4 Platform Admin — 平台管理員

所有 `/api/v1/admin/*` 端點，透過 `_ensure_admin()` 檢查：

```python
# backend/app/blueprints/admin.py
def _ensure_admin():
    allowlist = current_app.config.get("ADMIN_ALLOWLIST", set())
    user_id = str(g.user_id)
    user_email = (g.user or {}).get("email", "")
    # user_id 或 email 在 allowlist 中即為 Admin
    if user_id not in allowlist and user_email not in allowlist:
        raise AppError(code="FORBIDDEN", ...)
```

- **設定方式**：環境變數 `ADMIN_ALLOWLIST`，逗號分隔 user_id 或 email
- **例如**：`ADMIN_ALLOWLIST=admin@example.com,550e8400-e29b-41d4-a716-446655440000`
- Admin 可執行：全站活動管理、組織審核、訂單查詢、退款、結算、補償、Comp 票、Audit 查看

---

## 六、認證相關 Error Codes

| Code | HTTP | 觸發場景 |
|------|------|----------|
| `AUTH_REQUIRED` | 401 | 未帶 `Authorization` header 或 token 為空 |
| `AUTH_INVALID` | 401 | Token 過期或無效（Supabase 驗證失敗） |
| `AUTH_FAILED` | 400 | 登入失敗（帳密錯誤、無 session） |
| `AUTH_SERVICE_ERROR` | 502 | 無法連線 Supabase Auth 服務 |
| `FORBIDDEN` | 403 | 無權限（非 Admin、非組織成員、RLS 阻擋） |
| `STAFF_CANNOT_MANAGE` | 403 | Staff 嘗試執行 owner/admin 才有的操作 |
| `ORG_NOT_APPROVED` | 403 | 組織尚未通過審核，不可建活動 |
| `CONFIG_ERROR` | 500 | `SUPABASE_URL` 或 `SUPABASE_ANON_KEY` 未設定 |

---

## 七、前端路由守衛

```typescript
// frontend/src/router/index.ts
router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia);

  // 首次載入時初始化 session
  if (!authStore.initialized) {
    await authStore.refreshSession();
  }

  // 需登入但未登入 → 導向 /login
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  // 已登入但訪問 /login → 導向首頁
  if (to.name === "login" && authStore.isAuthenticated) {
    return { name: "home" };
  }
});
```

需登入的路由在 route meta 中設定 `requiresAuth: true`。

---

## 八、安全重點摘要

| 原則 | 說明 |
|------|------|
| JWT 來源唯一 | 所有 `user_id` 從 JWT 解析，禁止信任 client body |
| SERVICE_ROLE_KEY 保護 | 僅存在 backend `.env`，禁止出現在 frontend / log / response |
| Rate Limiting | 登入 10 req/min，防暴力破解 |
| RLS 強制 | 所有表開啟 RLS，`authed_client(jwt)` 受 RLS 約束 |
| Token 自動 Refresh | Supabase Client 自動處理，前端無需手動 |
| 401 自動清除 | 非登入請求收到 401 時清除本地 session 並導向登入頁 |
