# CypherHub MVP-1/2/3 完整驗收清單

> **建立日期**: 2026-03-24
> **最後更新**: 2026-03-24（Phase 0 + Phase 1 驗收完成）
> **目的**: 逐項驗證 MVP-1~3 所有功能是否正確實作、可運行、無缺陷
> **更新規則**: 每完成一個驗收項目，立即更新本文件狀態

## 狀態圖示

| 圖示 | 意義 |
|------|------|
| `[ ]` | 待驗收 |
| `[✅]` | 驗收通過 |
| `[⚠️]` | 部分通過，有待改善 |
| `[❌]` | 驗收失敗，需修復 |
| `[🔧]` | 已修復，等待重新驗收 |
| `[N/A]` | 不適用（Non-Goal 或不在範圍內） |

---

## Phase 0: 基礎建設驗收

### 0.1 開發環境
- [✅] `uv run ruff check .` — 零 lint 錯誤
- [✅] `uv run ruff format --check .` — 格式完全一致（修復 21 檔案後通過）
- [✅] `uv run pytest -q -m "not integration"` — 92 passed, 4 deselected (integration)
- [✅] `cd frontend && npm run build` — TypeScript + Vite 編譯成功
- [✅] `.env.example` 存在且包含所有必要 key（backend + frontend）
- [✅] `.gitignore` 正確排除 `.env`、`node_modules`、`.venv`、`__pycache__`

### 0.2 資料庫 Migrations
- [✅] 0001~0027 migration 檔案全部存在（27 檔確認）
- [ ] Migration 可順序套用（`supabase db reset` 不報錯）— 需本地 Supabase 環境驗證
- [✅] 所有表都啟用 RLS（migration 0002 確認）
- [✅] 必要 enum 類型存在：`organizer_role`, `event_status`, `ticket_status`, `order_status`, `payment_status`, `dance_style`, `event_type`
- [✅] 所有 RPC 函式存在：`register_free_v2`, `verify_ticket_qr`, `commit_checkin`, `cancel_ticket`, `create_hold_order`, `issue_tickets_for_order`, `cancel_holding_order`, `release_expired_holds`, `compensate_paid_orders`
- [✅] Helper 函式存在：`is_org_member`, `is_org_admin`, `is_event_member`, `is_event_admin`

### 0.3 專案結構
- [✅] Flask factory (`__init__.py`) 註冊所有 13 個 blueprints
- [✅] 所有 service 檔案存在且可 import（16 service files）
- [✅] Health check endpoint `GET /api/v1/health` 回傳 200

---

## Phase 1: MVP-1 — 免費報名 + QR 核銷

### 1.1 使用者認證
- [✅] `POST /api/v1/auth/login` — email + password 登入成功（Supabase Auth，email 正規化 strip+lower）
- [✅] `POST /api/v1/auth/login` — 錯誤密碼回傳 400 AUTH_FAILED
- [✅] `POST /api/v1/auth/login` — Rate limit 10/min 生效（`@rate_limiter.limit("10 per minute")`）
- [✅] JWT 解析正確，`g.user_id` 可用（auth_service.py handles `id` + `sub` fields）
- [✅] `@require_auth` 裝飾器阻擋無 token 請求 → 401 AUTH_REQUIRED
- [✅] `@require_auth` 阻擋過期/無效 token → 401 AUTH_INVALID

### 1.2 活動列表與詳情（公開）
- [✅] `GET /api/v1/events` — 只回傳 `published` 狀態活動（`eq("status", "published")`）
- [✅] `GET /api/v1/events` — 不需登入即可存取
- [✅] `GET /api/v1/events?styles=hiphop,popping` — 舞風篩選正確（array overlap filter）
- [✅] `GET /api/v1/events?types=cypher,battle` — 活動類型篩選正確
- [✅] `GET /api/v1/events?q=keyword` — 關鍵字搜尋（ILIKE on title, short_desc, location_name, location_address）
- [✅] `GET /api/v1/events?from=2026-01-01&to=2026-12-31` — 日期範圍篩選（gte/lte on start_at）
- [✅] `GET /api/v1/events?sort=hot` — 熱門排序（按 sold_count 總和，`_fetch_total_sold_per_event`）
- [✅] `GET /api/v1/events?sort=start_at` — 時間排序（預設 asc）
- [✅] `GET /api/v1/events/<id>` — 回傳完整活動詳情（含 ticket_types, organizer, media, other_events）
- [✅] `GET /api/v1/events/<id>` — 不存在的 event_id 回傳 404 EVENT_NOT_FOUND
- [✅] `GET /api/v1/events/<id>/forms` — 回傳正確的表單 schema

### 1.3 免費報名
- [✅] `POST /api/v1/events/<id>/register` — 需要登入（無 token → 401）
- [✅] `POST /api/v1/events/<id>/register` — 免費票正常報名，回傳 ticket 含 qr_secret
- [✅] 報名後 `sold_count` 正確遞增（RPC 內 `FOR UPDATE` 鎖定後 increment）
- [✅] `per_user_limit` 限制生效（RPC 檢查 existing tickets count）
- [✅] 容量已滿 → 錯誤 SOLD_OUT（RPC capacity check）
- [✅] Race-safe：RPC 使用 `FOR UPDATE` 鎖定（migration 0011）
- [✅] Rate limit 20/min 生效（`@rate_limiter.limit("20 per minute")`）
- [✅] 未 published 的活動無法報名（RPC 檢查 event_status）
- [✅] 報名成功後發送 email 通知（non-blocking, try/except 不阻擋回應）
- [✅] 含表單的報名：`register_free_v2` RPC 正確儲存 form_responses

### 1.4 我的票券
- [✅] `GET /api/v1/me/tickets` — 只回傳自己的票券（RLS + authed_client）
- [✅] 票券包含 `qr_secret` 供 QR 碼使用
- [✅] `DELETE /api/v1/me/tickets/<id>` — 取消票券，`sold_count` 遞減（RPC `cancel_ticket` 使用 `GREATEST(0, sold_count-1)`）
- [✅] `POST /api/v1/me/tickets/<id>/resend` — 重寄票券 email

### 1.5 主辦方申請與活動管理
- [✅] `POST /api/v1/organizer/apply` — 建立組織（自動成為 owner）
- [✅] 組織建立時自動插入 `organizer_members` (trigger: `trg_org_insert_member`，`ON CONFLICT DO NOTHING`)
- [✅] `POST /api/v1/organizer/events` — 建立活動（draft 狀態）
- [✅] `PATCH /api/v1/organizer/events/<id>` — 更新活動資訊（含時間變更通知）
- [✅] `GET /api/v1/organizer/events/<id>` — 取得主辦方活動詳情
- [✅] `PATCH /api/v1/organizer/events/<id>/internal-note` — 設定內部備註
- [✅] 活動狀態流轉：draft → published → ended / cancelled / disabled
- [✅] Staff 角色無法建立/編輯活動 → STAFF_CANNOT_MANAGE（測試驗證）

### 1.6 票種管理
- [✅] `POST /api/v1/organizer/events/<id>/ticket-types` — 建立票種
- [✅] `PATCH /api/v1/organizer/events/<id>/ticket-types/<tt_id>` — 更新票種（含 capacity ≥ sold_count 驗證）
- [✅] `DELETE /api/v1/organizer/events/<id>/ticket-types/<tt_id>` — 刪除票種（sold_count > 0 阻擋）
- [✅] 票種包含：name, description, price_cents, capacity, per_user_limit, sale_start_at, sale_end_at, is_active

### 1.7 表單系統
- [✅] `POST /api/v1/organizer/events/<id>/forms` — 建立/更新表單 schema（require_event_admin 保護）
- [✅] `GET /api/v1/organizer/events/<id>/forms` — 列出活動表單
- [✅] 支援欄位類型：text, number, email, phone, url, single_select, multi_select, dropdown, date, checkbox（10 種）
- [✅] 票種級別表單綁定（ticket_type_id 可選，含 event_id 匹配驗證）
- [✅] 表單 schema 驗證正確（unique keys, snake_case, select 需有 options）

### 1.8 QR 核銷
- [✅] `POST /api/v1/organizer/events/<id>/checkin/verify` — 驗證 QR 不做 commit
- [✅] `POST /api/v1/organizer/events/<id>/checkin/commit` — 原子性標記 checked_in
- [✅] 重複 commit → idempotent（回傳 `already_checked_in: true`）
- [✅] 非主辦方成員 → FORBIDDEN（RPC 內 `is_event_member` 檢查）
- [✅] QR secret 不匹配 → QR_MISMATCH
- [✅] 已取消票券無法核銷 → INVALID_STATUS
- [✅] 已結束/取消/下架活動無法核銷（migration 0015 guard）
- [✅] Rate limit 60/min 生效（verify + commit 皆有）
- [✅] 核銷統計：前端 OrganizerCheckinView 顯示 total/checked_in 分類統計

### 1.9 參加者管理
- [✅] `GET /api/v1/organizer/events/<id>/attendees` — 列出參加者（含表單回答）— 已加 `require_event_member()` defense-in-depth
- [✅] `POST /api/v1/organizer/events/<id>/attendees/<ticket_id>/resend` — 重寄票券 — 已加 `require_event_member()` defense-in-depth
- [✅] 搜尋功能（query param）

### 1.10 活動媒體
- [✅] `POST /api/v1/organizer/events/<id>/media` — 上傳圖片（≤5MB）
- [✅] 支援 image/jpeg, image/png, image/webp, image/gif（migration 0014）
- [✅] Storage bucket `event-media` 公開可讀（migration 0016）

### 1.11 使用者 Profile
- [✅] `GET /api/v1/me/organizer-summary` — 回傳使用者的組織與活動摘要
- [✅] Profile 更新：display_name, phone, social_links（透過 Supabase Auth client）

### 1.12 管理員基礎
- [✅] `GET /api/v1/admin/events` — 列出所有活動（含 draft/disabled）
- [✅] `PATCH /api/v1/admin/events/<id>` — 下架活動（status=disabled）
- [✅] Admin 驗證：只允許 `ADMIN_ALLOWLIST` 內的使用者（user_id + email 雙重檢查）

---

## Phase 2: MVP-2 — 付費票 + ECPay + 訂單

### 2.1 訂單建立與 Hold
- [ ] `POST /api/v1/orders/` — 建立 holding 訂單（原子性 hold_count 遞增）
- [ ] Hold 時間 15 分鐘（`hold_expires_at` 正確設定）
- [ ] `FOR UPDATE` 鎖定防止超賣
- [ ] `sold_count + hold_count ≤ capacity` 約束生效
- [ ] `per_user_limit` 對 hold 也生效（已有票 + hold 中 ≤ limit）
- [ ] `GET /api/v1/orders/` — 列出使用者訂單
- [ ] `GET /api/v1/orders/<id>` — 訂單詳情（含 items, payments）
- [ ] `DELETE /api/v1/orders/<id>` — 取消 holding 訂單，釋放 hold_count

### 2.2 Order State Machine
- [ ] 狀態流轉正確：created → holding → pending_payment → paid → issued
- [ ] 無效轉換被阻擋（如 cancelled → paid）
- [ ] holding → cancelled（timeout 或使用者取消）
- [ ] paid → refunded

### 2.3 ECPay 結帳
- [ ] `POST /api/v1/payments/checkout` — 產生 ECPay 表單參數
- [ ] CheckMacValue SHA256 計算正確
- [ ] 只有 holding 狀態的訂單可以 checkout
- [ ] 回傳 `form_params` 和 `cashier_url`

### 2.4 ECPay Webhook
- [ ] `POST /api/v1/webhooks/ecpay` — 接收 ECPay 回調
- [ ] CheckMacValue 驗證簽名
- [ ] Idempotency：相同 `MerchantTradeNo` 不會重複處理（UNIQUE 約束）
- [ ] 付款成功 → order 狀態更新為 paid
- [ ] 付款成功 → 自動發行票券（`issue_tickets_for_order` RPC）
- [ ] 發行票券後 `sold_count` 遞增，`hold_count` 遞減
- [ ] 回傳 `1|OK` 給 ECPay

### 2.5 Background Jobs
- [ ] `release_expired_holds()` — 過期 hold 自動釋放（pg_cron 每 1 分鐘）
- [ ] `compensate_paid_orders()` — 已付款但未發票的訂單自動補發（pg_cron 每 5 分鐘）
- [ ] `POST /api/v1/admin/release-expired-holds` — 手動觸發 hold 釋放
- [ ] `POST /api/v1/admin/compensate-paid-orders` — 手動觸發補發
- [ ] 兩個 job 都是 idempotent

### 2.6 退款
- [ ] `POST /api/v1/admin/orders/<id>/refund` — 發起全額退款
- [ ] 只支援全額退款（無部分退款）
- [ ] ECPay DoAction（Action=R）呼叫正確
- [ ] 退款成功 → order 狀態更新為 refunded
- [ ] 退款成功 → 發送 email 通知
- [ ] 一筆訂單只能有一個 active refund
- [ ] refunds 表正確記錄狀態（requested/refunded/failed）

### 2.7 庫存安全
- [ ] 併發建立 hold 時只有一個成功（last capacity 場景）
- [ ] hold 過期後容量正確釋放
- [ ] 已發行票券的 hold_count 正確歸零
- [ ] `ticket_types_inventory_check` 約束永遠成立

---

## Phase 3: MVP-3 — 治理 + 角色 + 結算 + Audit

### 3.1 組織成員管理（細粒度權限）
- [ ] `GET /api/v1/organizer/organizations/<org_id>/members` — 列出成員
- [ ] `POST /api/v1/organizer/organizations/<org_id>/members` — 新增成員
- [ ] `PATCH /api/v1/organizer/organizations/<org_id>/members/<user_id>` — 變更角色
- [ ] `DELETE /api/v1/organizer/organizations/<org_id>/members/<user_id>` — 移除成員
- [ ] 三種角色權限正確：
  - Owner：完整控制
  - Admin：管理活動/表單/票種，不能改結算
  - Staff：僅核銷與查看參加者
- [ ] Staff 不能建立活動 → STAFF_CANNOT_MANAGE
- [ ] 只有 Owner 可以變更角色
- [ ] 不能移除 Owner

### 3.2 組織審核
- [ ] `GET /api/v1/admin/organizations` — 列出所有組織（含 approval_status）
- [ ] `PATCH /api/v1/admin/organizations/<id>/approval` — 審核通過/拒絕
- [ ] `ORG_APPROVAL_REQUIRED=true` 時新組織預設 pending
- [ ] 未審核組織不能建立活動 → ORG_NOT_APPROVED
- [ ] 審核通過 → `approved_at`, `approved_by` 正確記錄
- [ ] 拒絕 → `rejection_reason` 正確記錄
- [ ] `payout_bank_info` (JSONB) 可儲存銀行資訊

### 3.3 結算與提領
- [ ] `POST /api/v1/admin/settlements/generate` — 產生結算紀錄
- [ ] 結算計算：gross_cents, platform_fee_cents (PLATFORM_FEE_RATE), net_cents
- [ ] `GET /api/v1/organizer/settlements` — 列出組織結算
- [ ] `GET /api/v1/organizer/settlements/<id>` — 結算詳情（含 ledger entries）
- [ ] `POST /api/v1/organizer/payout-requests` — 建立提領請求
- [ ] `GET /api/v1/admin/payout-requests` — 列出所有提領請求
- [ ] `PATCH /api/v1/admin/payout-requests/<id>` — 審核提領（approve/reject/paid/failed）
- [ ] `ledger_entries` 正確記錄：sale, refund, platform_fee, payout
- [ ] 組織餘額計算正確（`get_org_balance_cents`）

### 3.4 Comp Ticket（公關票）
- [ ] `POST /api/v1/organizer/events/<id>/comp-ticket` — 主辦方發公關票
- [ ] `POST /api/v1/admin/events/<id>/comp-ticket` — Admin 發公關票（如存在）
- [ ] 公關票不需訂單，直接建立 ticket（status=issued）
- [ ] 發送 email 通知收件人
- [ ] Audit log 記錄

### 3.5 Audit Logs
- [ ] `audit_logs` 表記錄以下操作：
  - 退款（initiated, completed, failed）
  - 公關票發放
  - 活動下架（admin unpublish）
  - 提領審核（approve/reject）
  - 結算產生
- [ ] actor_type 正確（admin/organizer/system）
- [ ] Audit logs 為 append-only（不可刪除）

### 3.6 全站訂單查詢（Admin）
- [ ] `GET /api/v1/admin/orders` — 支援篩選：status, from, to, org_id, event_id, q（搜尋 email/ticket_id）
- [ ] 支援分頁：limit, offset
- [ ] 回傳關聯 payments 與 refunds

### 3.7 活動通知
- [ ] 活動時間變更 → email 通知所有參加者（`notify_event_time_changed`）
- [ ] 活動取消/下架 → email 通知所有參加者（`notify_event_cancelled`）
- [ ] 活動提醒：1 天前 + 1 小時前（`POST /internal/jobs/event-reminders`）
- [ ] Cron job 需要 `X-Cron-Secret` header 驗證

### 3.8 熱門活動
- [ ] `GET /api/v1/events?sort=hot` — 按 total_sold_count 排序
- [ ] 前端 HomeView 顯示 Hot/Newest 切換

---

## Phase 4: 前端頁面驗收

### 4.1 公開頁面
- [ ] `HomeView.vue` — 活動列表、篩選（舞風/類型/日期/搜尋/排序）、卡片顯示
- [ ] `EventDetailView.vue` — 活動詳情、免費報名表單、付費票結帳流程
- [ ] `LoginView.vue` — 登入/註冊/忘記密碼三模式
- [ ] `ResetPasswordView.vue` — 密碼重設功能

### 4.2 使用者頁面
- [ ] `MyTicketsView.vue` — QR 碼顯示、票券狀態、取消、重寄
- [ ] `OrderDetailView.vue` — 訂單詳情、holding 倒計時、狀態顯示
- [ ] `ProfileView.vue` — 個人資料編輯 + 主辦方摘要

### 4.3 主辦方頁面
- [ ] `OrganizerHomeView.vue` — 導引流程（4 步驟）
- [ ] `OrganizerApplyView.vue` — 申請組織
- [ ] `OrganizerEventView.vue` — 建立/編輯活動（含票種、媒體、排程、社群連結）
- [ ] `OrganizerFormBuilderView.vue` — 表單設計器（9 種欄位、模板、預覽）
- [ ] `OrganizerCheckinView.vue` — QR 掃描 + 手動輸入核銷
- [ ] `OrganizerManageView.vue` — 參加者列表 + CSV 匯出 + 統計
- [ ] `OrganizerMembersView.vue` — 成員管理（新增/角色變更/移除）

### 4.4 管理員頁面
- [ ] `AdminView.vue` — 全站活動列表 + 下架功能

### 4.5 前端與後端 API 對接
- [ ] `client.ts` 中所有 API function 都有對應的 backend endpoint
- [ ] Bearer token 自動注入（axios interceptor）
- [ ] 401 response 自動重導到 login 頁
- [ ] 錯誤訊息映射正確（`errorMessages.ts`）

---

## Phase 5: 安全性與跨功能驗收

### 5.1 認證安全
- [ ] `user_id` 從 JWT 解析，不信任 client 傳入
- [ ] `SERVICE_ROLE_KEY` 不出現在 frontend/log/response
- [ ] `.env` 不在 git 中
- [ ] Rate limiting 生效（auth: 10/min, register: 20/min, checkin: 60/min）

### 5.2 資料安全
- [ ] RLS 全表啟用
- [ ] 使用者只能看自己的 tickets/orders
- [ ] 主辦方只能管理自己組織的活動
- [ ] Admin API 需要 allowlist 驗證

### 5.3 注入防護
- [ ] SQL：全部使用 Supabase SDK（參數化查詢）
- [ ] XSS：無 `v-html` 直接渲染使用者內容
- [ ] CSRF：使用 Bearer token（非 cookie session）
- [ ] Input validation：Pydantic schemas 驗證所有輸入

### 5.4 錯誤處理
- [ ] `AppError` 統一格式：`{ error: { code, message, details } }`
- [ ] 404 handler 正確
- [ ] 405 handler 正確
- [ ] 429 Rate limit handler 正確（含 Retry-After header）
- [ ] 500 handler 不洩漏 stack trace（`FLASK_DEBUG=0`）

---

## Phase 6: 測試覆蓋率驗收

### 6.1 現有測試
- [ ] 所有 unit tests 通過（`pytest -q -m "not integration"`）
- [ ] 測試數量 ≥ 90
- [ ] 無 skipped tests（除非有合理原因）

### 6.2 關鍵路徑測試覆蓋
- [ ] Order state machine 測試
- [ ] Payment service 測試（checkout, webhook, CheckMacValue）
- [ ] Compensation 測試
- [ ] Hold creation + oversell prevention 測試
- [ ] Rate limiting 測試
- [ ] Auth 測試
- [ ] Staff permission 測試（MVP-3）
- [ ] Organizer approval 測試（MVP-3）
- [ ] Settlement 計算測試（MVP-3）
- [ ] Audit log 測試（MVP-3）
- [ ] Form validation 測試
- [ ] Email service 測試
- [ ] Event notification 測試

### 6.3 缺少的測試（待補強）
- [ ] ECPay CheckMacValue 邊界值測試
- [ ] Webhook 簽名驗證失敗場景測試
- [ ] 退款 API 端到端測試
- [ ] Comp ticket 建立測試
- [ ] Settlement generation 端到端測試
- [ ] Payout request approve/reject 測試
- [ ] Admin orders 查詢篩選測試
- [ ] Event time change notification 測試
- [ ] Event cancellation notification 測試
- [ ] Profile update 測試

---

## 已發現問題追蹤

| # | 嚴重度 | 問題描述 | 狀態 | 修復 commit |
|---|--------|---------|------|-------------|
| 1 | Low | `list_attendees` blueprint 缺顯式權限檢查 | ✅ 已修復 | 加入 `require_event_member()` |
| 2 | Low | `resend_attendee_ticket` blueprint 缺顯式權限檢查 | ✅ 已修復 | 加入 `require_event_member()` |
| 3 | Trivial | `cancel_ticket()` service 接受未使用的 `user_id` 參數 | ✅ 已修復 | 移除多餘參數 |
| 4 | Low | 21 個 Python 檔案格式不一致 | ✅ 已修復 | ruff format 自動修正 |

---

## 驗收進度總覽

| Phase | 項目數 | ✅通過 | ⚠️待改善 | ❌失敗 | 待驗 | 進度 |
|-------|--------|--------|----------|--------|------|------|
| Phase 0: 基礎建設 | 17 | 16 | 0 | 0 | 1 | 94% |
| Phase 1: MVP-1 | 54 | 54 | 0 | 0 | 0 | 100% |
| Phase 2: MVP-2 | 30 | 0 | 0 | 0 | 30 | 0% |
| Phase 3: MVP-3 | 37 | 0 | 0 | 0 | 37 | 0% |
| Phase 4: 前端 | 20 | 0 | 0 | 0 | 20 | 0% |
| Phase 5: 安全性 | 14 | 0 | 0 | 0 | 14 | 0% |
| Phase 6: 測試 | 26 | 0 | 0 | 0 | 26 | 0% |
| **合計** | **198** | **70** | **0** | **0** | **128** | **35%** |
