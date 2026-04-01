# Google OAuth 登入開發計畫

> **功能目標**：使用者可透過 Google 帳號一鍵登入 CypherHub，同時自動取得 Gmail 作為系統 email，減少手動註冊的門檻。

---

## 1. 可行性分析

### 1.1 Gmail 取得方式

| 方式 | 說明 | 結論 |
|------|------|------|
| **Google OAuth (Supabase 內建)** | OAuth 預設 scope 包含 `email`，Google 回傳的 email 自動寫入 `auth.users.email` | **採用** |
| Google People API | 額外 API 呼叫取得 email | 不需要，OAuth 已提供 |
| 使用者手動填寫 | 註冊後請使用者輸入 Gmail | 不需要，OAuth 已提供 |

**結論**：Google OAuth 登入時，Supabase 自動將 Google email 存入 `auth.users.email`，與現有 email/password 使用者完全一致。**不需要額外的 API 呼叫或權限申請**。

### 1.2 Supabase 支援度

Supabase Auth 原生支援 Google OAuth（PKCE flow），前端僅需呼叫 `supabase.auth.signInWithOAuth({ provider: 'google' })`，不需修改 backend JWT 驗證邏輯。

### 1.3 對現有系統的影響

| 面向 | 影響 |
|------|------|
| `auth.users` 表 | 新增 Google identity，email 自動填入，無需 migration |
| `profiles` 表 | 現有 auto-create 邏輯已支援（首次訪問 profile 頁自動建立） |
| JWT 驗證 (`require_auth`) | **零改動**，Google 使用者的 JWT 格式與 email 使用者完全相同 |
| RLS Policies | **零改動**，`auth.uid()` 對所有 provider 一致 |
| 前端 API client | **零改動**，Bearer token 機制不變 |

---

## 2. 功能範圍（Scope）

### In-Scope

| 面向 | 功能 |
|------|------|
| 使用者 | 登入頁顯示「使用 Google 登入」按鈕 |
| 使用者 | 點擊後跳轉 Google 授權頁面，授權後自動登入並回到原頁面 |
| 使用者 | 首次 Google 登入自動建立帳號（Supabase 自動處理） |
| 使用者 | Google 登入後取得的 email 自動作為系統 email |
| 系統 | 處理 OAuth callback redirect（Supabase SDK 自動處理） |
| 系統 | 支援既有 email/password 使用者改用 Google 登入（同 email 自動 link） |
| UI | Google 按鈕符合 [Google Brand Guidelines](https://developers.google.com/identity/branding-guidelines) |

### Out-of-Scope（本次不做）

- 其他 OAuth Provider（Facebook、Apple、GitHub 等）
- 帳號解綁 / 取消 Google 連結
- Google 日曆整合、Google Contacts 等額外 API
- 強制 Google 登入（email/password 登入仍保留）

---

## 3. 技術方案

### 3.1 整體架構

```
使用者 → [Google 登入按鈕] → supabase.auth.signInWithOAuth({ provider: 'google' })
    → Google OAuth 授權頁
    → 授權成功 → redirect 回 CypherHub (callback URL)
    → Supabase SDK 自動處理 token exchange
    → onAuthStateChange 觸發 → session/user 更新
    → 自動跳轉到原頁面
```

### 3.2 前端實作

#### 3.2.1 Auth Store 新增 `signInWithGoogle()`

**檔案**：`frontend/src/stores/auth.ts`

```typescript
async function signInWithGoogle(): Promise<void> {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  });
  if (error) throw error;
  // OAuth 是 redirect flow，不需要手動 refreshSession
  // onAuthStateChange listener 會自動處理 session 更新
}
```

#### 3.2.2 OAuth Callback 路由

**新增檔案**：`frontend/src/views/AuthCallbackView.vue`

用途：處理 Google OAuth redirect 回來後的 token exchange。

```
路由：/auth/callback
邏輯：
1. 頁面載入 → 顯示 loading spinner
2. Supabase SDK 自動從 URL hash/query 解析 token
3. onAuthStateChange 觸發 SIGNED_IN event
4. 讀取 localStorage 或 query param 中的 redirect 目標
5. 跳轉到原頁面（或首頁）
```

#### 3.2.3 登入頁 UI 修改

**檔案**：`frontend/src/views/LoginView.vue`

在現有 email/password 表單上方或下方加入：

```
─────── 或 ───────
[G] 使用 Google 登入
```

- 按鈕樣式遵循 Google Brand Guidelines（白底 + Google logo + 文字）
- 按鈕在 loading 時 disabled
- 錯誤訊息共用現有 errorMessage 機制

#### 3.2.4 Router 新增

**檔案**：`frontend/src/router/index.ts`

```typescript
{
  path: '/auth/callback',
  name: 'auth-callback',
  component: () => import('../views/AuthCallbackView.vue'),
  meta: { requiresAuth: false },
}
```

### 3.3 後端改動

**後端不需要改動。** 原因：

1. Google 使用者的 JWT 與 email 使用者的 JWT 格式完全相同
2. `require_auth` decorator 透過 `supabase_client.get_user(jwt)` 驗證，對所有 provider 一致
3. `g.user_id` 提取邏輯不受影響
4. 不需要新增 API endpoint

### 3.4 Supabase Dashboard 設定（手動）

> 以下為必要的 Dashboard 設定，非程式碼變更。

#### Step 1：啟用 Google Provider

1. Supabase Dashboard → Authentication → Providers → Google
2. 開啟 Enable Google provider
3. 填入 Google OAuth Client ID 和 Client Secret

#### Step 2：Google Cloud Console 設定

1. [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. 建立 OAuth 2.0 Client ID（Web application 類型）
3. Authorized JavaScript origins：
   - `http://localhost:5173`（開發）
   - `https://你的正式網域`（正式）
4. Authorized redirect URIs：
   - `https://<your-supabase-project>.supabase.co/auth/v1/callback`
   - （Supabase 會在 Dashboard 顯示正確的 redirect URI）
5. OAuth consent screen：
   - App name: CypherHub
   - Scopes: `email`, `profile`（預設）
   - User type: External（若要公開）

#### Step 3：Supabase Redirect URLs

1. Supabase Dashboard → Authentication → URL Configuration
2. Redirect URLs 新增：
   - `http://localhost:5173/auth/callback`（開發）
   - `https://你的正式網域/auth/callback`（正式）

### 3.5 Profile 自動建立

現有邏輯（`ProfileView.vue` 中的 `loadOrCreateProfile`）已處理：
- 若 `profiles` 表無該 user 的資料，自動用 email prefix 建立 `display_name`
- Google 使用者首次登入後訪問 profile 頁即自動建立

**優化（可選）**：可從 Google 回傳的 `user_metadata` 取得使用者名稱和頭像：

```typescript
// user.user_metadata 包含 Google 回傳的資訊
const metadata = user.user_metadata;
// metadata.full_name → "王小明"
// metadata.avatar_url → Google 頭像 URL
// metadata.email → Gmail
```

可在自動建立 profile 時使用這些資料，提供更好的初始體驗。

---

## 4. 帳號整合策略

### 4.1 同 Email 場景

| 場景 | Supabase 行為 | 備註 |
|------|--------------|------|
| 新 email，首次 Google 登入 | 自動建立新帳號 | 正常流程 |
| 已有 email/password 帳號，用同 email Google 登入 | 自動 link 到同一帳號 | 需確認 Supabase 設定 |
| 已有 Google 帳號，再用 email/password 註冊同 email | 自動 link | 同上 |

### 4.2 Supabase 設定

Dashboard → Authentication → General：
- **Enable automatic linking**：建議開啟（同 email 自動合併帳號）
- 若關閉，同 email 不同 provider 會建立獨立帳號（不建議）

---

## 5. 安全性考量

| 項目 | 說明 | 處置 |
|------|------|------|
| PKCE Flow | Supabase JS SDK 預設使用 PKCE，防止 authorization code 被攔截 | 自動，無需額外設定 |
| State Parameter | Supabase 自動加入 state 參數防 CSRF | 自動 |
| Redirect URI 限制 | 僅允許白名單中的 redirect URL | 在 Supabase Dashboard 設定 |
| Google Client Secret | 僅存在 Supabase Dashboard，不進入程式碼 | 無需環境變數 |
| Token 儲存 | Supabase SDK 使用 localStorage（與現有機制一致） | 現有機制 |
| 權限最小化 | 僅申請 `email` + `profile` scope | Google Console 設定 |

---

## 6. 實作步驟

### Phase 1：Supabase & Google 設定（手動操作）

- [ ] Google Cloud Console 建立 OAuth 2.0 Client ID
- [ ] 設定 OAuth consent screen（app name、scopes、redirect URIs）
- [ ] Supabase Dashboard 啟用 Google Provider，填入 Client ID & Secret
- [ ] Supabase Dashboard 新增 Redirect URLs（開發 + 正式環境）
- [ ] 確認 Supabase 的 automatic linking 設定

### Phase 2：前端實作

- [ ] `auth.ts` store 新增 `signInWithGoogle()` method
- [ ] 新增 `AuthCallbackView.vue`（OAuth callback 頁面）
- [ ] `router/index.ts` 新增 `/auth/callback` 路由
- [ ] `LoginView.vue` 加入 Google 登入按鈕（含 Google icon）
- [ ] 處理 OAuth 錯誤顯示（如使用者取消授權）
- [ ] `ProfileView.vue` 優化：首次建立 profile 時帶入 Google `user_metadata`（full_name、avatar_url）

### Phase 3：測試

- [ ] **手動測試（開發環境）**
  - 新使用者 Google 登入 → 自動建立帳號 → session 正常
  - Google 登入後訪問 profile → 自動建立 profile，display_name/avatar 帶入
  - 已有 email/password 帳號 → 同 email Google 登入 → 帳號 link 正常
  - Google 登入後存取受保護 API → JWT 驗證正常
  - Google 登入後 signOut → session 清除正常
  - 使用者取消 Google 授權 → 正確顯示錯誤訊息
  - Mobile responsive 顯示正常
- [ ] **前端 unit test**
  - `signInWithGoogle()` 呼叫 `supabase.auth.signInWithOAuth` with correct params
  - `AuthCallbackView` 正確處理 redirect
  - Login 頁面 Google 按鈕渲染 + click handler
- [ ] **後端 test（確認無需改動）**
  - 現有 `test_auth_login.py` 仍全部通過
  - 使用 Google provider 的 JWT 通過 `require_auth` 驗證（mock 測試）
- [ ] **E2E 測試（可選）**
  - 完整 Google OAuth flow（需 test Google account）

### Phase 4：驗證 & 上線

- [ ] `cd frontend && npm run build` 通過
- [ ] `cd backend && ruff check . && pytest -q` 通過（確認無 regression）
- [ ] 正式環境 Google Cloud Console 設定正式網域
- [ ] 正式環境 Supabase Dashboard 設定正式 redirect URL
- [ ] Google OAuth consent screen 審核（若需公開）
- [ ] 上線後驗證：正式環境 Google 登入 flow 正常

---

## 7. 需要修改的檔案清單

| 檔案 | 變更類型 | 說明 |
|------|---------|------|
| `frontend/src/stores/auth.ts` | 修改 | 新增 `signInWithGoogle()` |
| `frontend/src/views/LoginView.vue` | 修改 | 加入 Google 登入按鈕 + UI |
| `frontend/src/views/AuthCallbackView.vue` | **新增** | OAuth callback 處理頁面 |
| `frontend/src/router/index.ts` | 修改 | 新增 `/auth/callback` 路由 |
| `frontend/src/views/ProfileView.vue` | 修改（可選） | 首次建立 profile 帶入 Google metadata |
| `frontend/src/utils/errorMessages.ts` | 修改（可選） | 新增 OAuth 相關錯誤訊息 |

**不需修改**：
- 所有 backend 檔案（`auth.py`、`auth_service.py`、`supabase_client.py`）
- Database migration（Supabase Auth 自動處理）
- RLS policies

---

## 8. 風險與注意事項

| 風險 | 嚴重度 | 緩解措施 |
|------|--------|---------|
| Google OAuth consent screen 審核耗時 | 低 | 測試階段用 "Testing" 模式（限 100 test users），正式上線再提交審核 |
| 使用者用不同 email 的 Google 帳號登入 | 低 | Supabase 視為不同使用者，行為正確 |
| localStorage token 被清除 | 低 | 與現有行為一致，使用者重新登入即可 |
| Supabase Realtime / 其他功能與 Google JWT 不相容 | 極低 | Supabase 所有功能對 provider 一視同仁 |
| Google API 變更 | 極低 | Supabase 團隊維護 provider 整合 |

---

## 9. 時程依賴

```
Phase 1（設定）──→ Phase 2（實作）──→ Phase 3（測試）──→ Phase 4（上線）
   │                                                         │
   └─ 需 Google Cloud Console 存取權                         └─ 需正式網域
```

Phase 1 是 blocker，必須先完成 Google Cloud Console 和 Supabase Dashboard 設定，才能開始前端開發。
