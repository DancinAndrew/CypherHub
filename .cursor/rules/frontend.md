# CypherHub Frontend 開發規範

> 適用範圍：`frontend/` 目錄（Vue 3 + Vite + TypeScript + TailwindCSS + Pinia）  
> 請嚴格遵守，確保與後端 API、Supabase Auth 整合一致。

---

## 一、開發流程守則

### 1.1 任務前必做

1. **先寫短 plan**：要改哪些檔案、是否需調整 API client、router、store
2. **確認 RBAC**：該頁面需 Guest / User / Organizer / Admin 何種權限
3. **diff 小且可跑**：每次改動可獨立驗證，`npm run build` 無錯

### 1.2 任務後必做

1. **本地驗證**：`npm run dev` 啟動後手動跑一遍流程
2. **Build 驗證**：`npm run build` 必須通過
3. **無 secrets**：絕不將 `SUPABASE_SERVICE_ROLE_KEY`、`sb_secret_` 等寫入前端

---

## 二、技術棧與目錄結構

### 2.1 技術棧

| 項目 | 規格 |
|------|------|
| 框架 | Vue 3 (Composition API) |
| 建置 | Vite |
| 語言 | TypeScript |
| 狀態 | Pinia |
| 路由 | Vue Router 4 |
| 樣式 | TailwindCSS |
| HTTP | Axios（`src/api/client.ts`）|
| Auth | Supabase JS Client（`src/api/supabase.ts`）|

### 2.2 目錄結構（必須遵守）

```
frontend/src/
├── api/           # axios clients、supabase client
│   ├── client.ts  # 後端 API 呼叫、型別定義
│   └── supabase.ts
├── components/    # 可重用元件
├── constants/     # 常數（如 taxonomy）
├── router/        # 路由定義
├── stores/        # Pinia stores
├── utils/         # 工具函數（如 errorMessages）
├── views/         # 頁面元件
│   └── organizer/ # 主辦方相關子頁
├── App.vue
├── main.ts
└── style.css
```

### 2.3 路由命名與結構

- 路徑使用 kebab-case：`/organizer/checkin/:eventId`
- `name` 使用 PascalCase 或 kebab：`event-detail`、`organizer-event-edit`
- 需登入頁面必須設定 `meta: { requiresAuth: true }`
- 登入後導向：`redirect` query 保留原目標路徑

---

## 三、Auth 與 API 整合

### 3.1 Supabase 使用規則

- **前端只用**：`SUPABASE_URL`、`SUPABASE_ANON_KEY`（或 `VITE_SUPABASE_*`）
- **禁止**：`SUPABASE_SERVICE_ROLE_KEY`、`sb_secret_` 出現於前端
- 登入後 JWT 透過 `Authorization: Bearer <token>` 帶給後端

### 3.2 API Client 規範

- 所有後端呼叫透過 `src/api/client.ts`
- 使用 `import.meta.env.VITE_API_BASE_URL`（預設 `http://localhost:8000`）
- Request interceptor 自動附加 `Authorization: Bearer ${token}`（來自 Pinia auth store）
- 型別定義與 API 回傳一致，避免 `any`

### 3.3 錯誤處理

- 使用 `utils/errorMessages.ts` 的 `toApiErrorMessage`、`toAuthErrorMessage`
- 標準錯誤格式：`{ "error": { "code": "...", "message": "...", "details": ... } }`
- 登入過期時：清除 session、導向 `/login?redirect=<current path>`

---

## 四、Pinia Store 規範

### 4.1 Auth Store

- `useAuthStore` 管理：`session`、`user`、`initialized`
- `accessToken`：computed，供 API client 使用
- `refreshSession()`：初始化與路由 guard 時呼叫
- `signIn` / `signUp` / `signOut`：調用 Supabase Auth

### 4.2 其他 Store

- 若需跨頁共用資料（如 organizer orgId），使用 Pinia store
- 避免在元件內直接呼叫 Supabase；經由 API client 或 store 封裝

---

## 五、Router Guard 規範

### 5.1 必須實作

```typescript
router.beforeEach(async (to) => {
  // 1. 確保 auth store 已初始化（refreshSession）
  // 2. meta.requiresAuth 且未登入 → redirect 到 /login?redirect=...
  // 3. 已登入造訪 /login → redirect 到 home
  return true;
});
```

### 5.2 RBAC 對應

| 路徑 | 需登入 | 角色 |
|------|--------|------|
| `/`、`/events/:id` | 否 | Guest 可看 |
| `/tickets` | 是 | User |
| `/organizer/*` | 是 | Organizer member |
| `/admin/*` | 是 | Admin（allowlist）|

---

## 六、元件與 View 規範

### 6.1 命名

- View：`XxxView.vue`（如 `EventDetailView.vue`）
- Component：`PascalCase.vue`（如 `DynamicForm.vue`）
- 目錄：`views/organizer/` 存放主辦方子頁

### 6.2 結構

- 使用 `<script setup lang="ts">`
- 型別明確，避免 `any`
- 表單驗證在前端做基本檢查，後端為最終權威

### 6.3 表單與動態表單

- `DynamicForm.vue` 依 JSON schema 動態渲染
- 支援 `text`、`number`、`phone`、`checkbox` 等（見 `FormFieldType`）
- `v-model` 綁定 `formAnswers: Record<string, unknown>`

---

## 七、樣式規範

### 7.1 TailwindCSS

- 優先使用 utility classes
- 共通用式可放 `style.css` 或元件內 `<style scoped>`
- 顏色/間距與設計系統一致（如 `brand-600`、`slate-800`）

### 7.2 響應式

- 活動列表、表單需支援 mobile（主辦方核銷為手機 Web）

---

## 八、Definition of Done

每次改動完成前，必須：

1. **Lint/Build**：`npm run build` 無錯
2. **手動驗證**：關鍵流程跑過（登入、報名、核銷等）
3. **無 console.error** 殘留（除必要 log）
4. **無 secrets**：檢查無 `service_role`、`sb_secret_` 等
5. **API 錯誤處理**：網路錯誤、401、4xx 有適當提示

---

## 九、參考

- 開發藍圖：`docs/develop.md`
- 本地/雲端切換：`docs/local-cloud-switch.md`
- 後端規範：`.cursor/rules/backend.md`
