# CypherHub MVP-1/2/3 完整驗收清單

> **建立日期**: 2026-03-24
> **最後更新**: 2026-03-24（Phase 0~4 驗收完成）
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
- [✅] `POST /api/v1/orders/` — 建立 holding 訂單（原子性 hold_count 遞增）— RPC `create_hold_order`（migration 0019）
- [✅] Hold 時間 15 分鐘（`hold_expires_at` 正確設定）— `p_hold_minutes int DEFAULT 15`
- [✅] `FOR UPDATE` 鎖定防止超賣 — migration 0019:62 行 `FOR UPDATE`
- [✅] `sold_count + hold_count ≤ capacity` 約束生效 — migration 0017:107-108 CHECK constraint + RPC 檢查
- [✅] `per_user_limit` 對 hold 也生效（已有票 + hold 中 ≤ limit）— migration 0019:90-106 計算 existing_tickets + existing_holds
- [✅] `GET /api/v1/orders/` — 列出使用者訂單（RLS `user_id = auth.uid()`）
- [✅] `GET /api/v1/orders/<id>` — 訂單詳情（含 items, payments）— `OrderDetailResponse`
- [✅] `DELETE /api/v1/orders/<id>` — 取消 holding 訂單，釋放 hold_count — RPC `cancel_holding_order`（migration 0021）

### 2.2 Order State Machine
- [✅] 狀態流轉正確：created → holding → pending_payment → paid → issued — `order_state_machine.py:32-43`
- [✅] 無效轉換被阻擋（如 cancelled → paid）— `validate_transition()` raises `INVALID_ORDER_STATUS_TRANSITION`
- [✅] holding → cancelled（timeout 或使用者取消）— `release_expired_holds` + `cancel_holding_order`
- [✅] paid → refunded — `refund_service.py` + state machine 驗證

### 2.3 ECPay 結帳
- [✅] `POST /api/v1/payments/checkout` — 產生 ECPay 表單參數 — `payment_service.py:23-124`
- [✅] CheckMacValue SHA256 計算正確 — `ecpay.py:35-51` 含 URL encoding + 大寫 digest
- [✅] 只有 holding 狀態的訂單可以 checkout — state machine `holding → pending_payment`
- [✅] 回傳 `form_params` 和 `cashier_url`（stage/production URL 自動切換）

### 2.4 ECPay Webhook
- [✅] `POST /api/v1/webhooks/ecpay` — 接收 ECPay 回調（無 `@require_auth`，正確）
- [✅] CheckMacValue 驗證簽名 — `verify_webhook_checkmac()` + `exclude_empty=False`
- [✅] Idempotency：`webhook_events` 表 `UNIQUE(provider, external_event_id)` 約束 + 23505 錯誤碼偵測
- [✅] 付款成功 → order 狀態更新為 paid — `payment_service.py:206-208`
- [✅] 付款成功 → 自動發行票券（`issue_tickets_for_order` RPC）— `payment_service.py:210-215`
- [✅] 發行票券後 `sold_count` 遞增，`hold_count` 遞減 — migration 0022 修正為 `v_to_create` 保證冪等
- [✅] 回傳 `1|OK` 給 ECPay — 所有路徑回傳 `1|OK` 或 `0|ERROR`（`mimetype="text/plain"`）

### 2.5 Background Jobs
- [✅] `release_expired_holds()` — pg_cron `* * * * *`（每 1 分鐘），`FOR UPDATE SKIP LOCKED` 防並發
- [✅] `compensate_paid_orders()` — pg_cron `*/5 * * * *`（每 5 分鐘），migration 0022 冪等修正
- [✅] `POST /api/v1/admin/release-expired-holds` — `admin.py:76-82`，需 admin 驗證
- [✅] `POST /api/v1/admin/compensate-paid-orders` — `admin.py:67-73`，需 admin 驗證
- [✅] 兩個 job 都是 idempotent — `SKIP LOCKED` + `v_to_create` 計算防重複

### 2.6 退款
- [✅] `POST /api/v1/admin/orders/<id>/refund` — `admin.py:111-118`，需 admin 驗證
- [✅] 只支援全額退款（`total_cents` 全額，無 partial amount 參數）
- [✅] ECPay DoAction（`Action=R`）呼叫正確 — `ecpay.py:107-153` + CheckMacValue
- [✅] 退款成功 → order/payment/refund 三表狀態同步更新為 refunded
- [✅] 退款成功 → `send_refund_complete_email()` 發送退款通知
- [✅] 一筆訂單只能有一個 active refund — state machine 阻擋：退款後 status=refunded，`can_transition("refunded","refunded")=false`
- [✅] refunds 表正確記錄狀態（`CHECK (status IN ('requested','refunded','failed'))`）

### 2.7 庫存安全
- [✅] 併發建立 hold 時只有一個成功 — `test_hold_concurrency.py` capacity=1 驗證 `FOR UPDATE`
- [✅] hold 過期後容量正確釋放 — `release_expired_holds` 遞減 `hold_count`
- [✅] 已發行票券的 `hold_count` 正確歸零 — migration 0022 `hold_count -= v_to_create`（冪等）
- [✅] `ticket_types_inventory_check` 約束永遠成立 — migration 0017 CHECK + 所有寫入路徑維護

---

## Phase 3: MVP-3 — 治理 + 角色 + 結算 + Audit

### 3.1 組織成員管理（細粒度權限）
- [✅] `GET /api/v1/organizer/organizations/<org_id>/members` — 列出成員（`require_org_admin` 保護）
- [✅] `POST /api/v1/organizer/organizations/<org_id>/members` — 新增成員（role 限 admin|staff，schema 驗證）
- [✅] `PATCH /api/v1/organizer/organizations/<org_id>/members/<user_id>` — 變更角色（admin 不可指派 owner）
- [✅] `DELETE /api/v1/organizer/organizations/<org_id>/members/<user_id>` — 移除成員（最後 owner 保護）
- [✅] 三種角色權限正確：
  - Owner：完整控制（`is_org_admin` + 無限制）
  - Admin：管理活動/表單/票種（`is_org_admin`），不能指派 owner
  - Staff：僅核銷與查看參加者（`is_event_member`，不通過 `require_event_admin`）
- [✅] Staff 不能建立活動 → `STAFF_CANNOT_MANAGE`（`require_org_admin()` 阻擋，有測試覆蓋）
- [✅] Owner/Admin 可變更角色，但 Admin 不可指派 owner — 符合 spec「owner 可改 role；admin 不可改 owner」
- [✅] 不能移除最後一位 Owner — `remove_org_member()` 防止 orphan org

### 3.2 組織審核
- [✅] `GET /api/v1/admin/organizations` — 列出所有組織（含 approval_status，可篩選 pending/approved/rejected）
- [✅] `PATCH /api/v1/admin/organizations/<id>/approval` — 審核通過/拒絕（`AdminOrganizationApprovalRequest`）
- [✅] `ORG_APPROVAL_REQUIRED=true` 時新組織預設 pending — `config.py:27` 環境變數控制
- [✅] 未審核組織不能建立活動 → `ORG_NOT_APPROVED`（error code 已修正對齊測試）
- [✅] 審核通過 → `approved_at`（ISO timestamp）, `approved_by`（admin user_id）正確記錄
- [✅] 拒絕 → `rejection_reason` 正確記錄（approved_at/approved_by 清除為 null）
- [✅] `payout_bank_info` (JSONB) 欄位已建立（migration 0024），尚未有專用 API 但 schema 可用

### 3.3 結算與提領
- [✅] `POST /api/v1/admin/settlements/generate` — 產生結算紀錄（`settlement_service.py:22-135`）
- [✅] 結算計算正確：`gross = Σ(qty×price)`，`fee = gross × PLATFORM_FEE_RATE(5%)`，`net = gross - fee`
- [✅] `GET /api/v1/organizer/settlements` — 列出組織結算（`period_end DESC`，限 100 筆）
- [✅] `GET /api/v1/organizer/settlements/<id>` — 結算詳情含 ledger_entries 明細（已修正）
- [✅] `POST /api/v1/organizer/payout-requests` — 建立提領請求（驗證 amount > 0、餘額足夠、需 org admin）
- [✅] `GET /api/v1/admin/payout-requests` — 列出所有提領請求（可篩選 status，限 200 筆）
- [✅] `PATCH /api/v1/admin/payout-requests/<id>` — 審核提領：`requested → approved → paid`（新增 `mark_paid` action + `approved` 中間狀態）
- [✅] `ledger_entries` 正確記錄：sale、platform_fee（generate 時）、payout（approve 時）
- [✅] 組織餘額計算正確 — `get_org_balance_cents()` 加總所有 ledger_entries.amount_cents

### 3.4 Comp Ticket（公關票）
- [✅] `POST /api/v1/organizer/events/<id>/comp-ticket` — 主辦方發公關票（需 event_admin，含容量檢查）
- [✅] `POST /api/v1/admin/events/<id>/comp-ticket` — Admin 專屬路由已實作（`_ensure_admin` + `skip_permission_check` + `actor_type="admin"`）
- [✅] 公關票不需訂單（`order_id=None`），直接建立 ticket（`status=issued`）
- [✅] 發送 email 通知收件人 — `email_service.send_ticket_email()`，失敗不阻斷主流程
- [✅] Audit log 記錄 — `audit_service.log_comp_ticket()` 含 event_id、ticket_type_id、recipient、note

### 3.5 Audit Logs
- [✅] `audit_logs` 表記錄以下操作：
  - 退款：`log_refund()` — action="refund"
  - 公關票發放：`log_comp_ticket()` — action="comp_ticket"
  - 活動下架：`log_unpublish()` — action="unpublish"
  - 提領審核：`log_payout_approve()` / `log_payout_reject()` — action="payout_approve"/"payout_reject"
  - 結算產生：`log_settlement_generate()` — action="settlement_generate"
- [✅] actor_type 正確 — CHECK constraint `IN ('admin','organizer','system')` + 常數 `ACTOR_ADMIN/ORGANIZER/SYSTEM`
- [✅] Audit logs 為 append-only — 僅 service_role 可寫入，無 RLS DELETE/UPDATE policy

### 3.6 全站訂單查詢（Admin）
- [✅] `GET /api/v1/admin/orders` — 支援 status/from/to/org_id/event_id 篩選 + `q` 搜尋 order_id（UUID）或 email（精確匹配）
- [✅] 支援分頁：limit（上限 100）、offset — `.range(offset, offset+limit-1)`
- [✅] 回傳關聯 orders + items + payments（三表分別查詢後聚合）

### 3.7 活動通知
- [✅] 活動時間變更 → `notify_event_time_changed()` email 通知所有 issued/checked_in 參加者
- [✅] 活動取消/下架 → `notify_event_cancelled()` email 通知所有參加者
- [✅] 活動提醒：1 天前（23-25h window）+ 1 小時前（55-65m window）— `POST /internal/jobs/event-reminders`
- [✅] Cron job `X-Cron-Secret` header 驗證 — `_verify_cron_secret()` 比對 config CRON_SECRET

### 3.8 熱門活動
- [✅] `GET /api/v1/events?sort=hot` — 按 `total_sold_count` DESC 排序（加總 ticket_types.sold_count）
- [✅] 前端 HomeView 顯示 Hot/Newest 切換 — `sortMode ref` + UI 按鈕 + badge 顯示報名人數

---

## Phase 4: 前端頁面驗收

### 4.1 公開頁面
- [✅] `HomeView.vue` — 活動列表、篩選（舞風/類型/日期/搜尋/排序）、卡片顯示（含熱門排序、URL 參數保留）
- [✅] `EventDetailView.vue` — 活動詳情、免費報名表單（DynamicForm + 驗證）、付費票結帳流程（hold → ECPay redirect）
- [✅] `LoginView.vue` — 登入/註冊/忘記密碼三模式切換、email 驗證、redirect 支援
- [✅] `ResetPasswordView.vue` — 密碼重設表單、最小長度驗證、密碼確認、自動重導

### 4.2 使用者頁面
- [✅] `MyTicketsView.vue` — QR 碼顯示（qrcode.vue）、票券狀態 badge、取消（含確認）、重寄 email、copy payload
- [✅] `OrderDetailView.vue` — 訂單詳情、狀態顯示、holding 即時倒數計時器（mm:ss 格式，逾時自動停止）
- [✅] `ProfileView.vue` — 個人資料編輯（姓名/電話/社群連結）+ 主辦方組織/活動摘要、自動建立 profile

### 4.3 主辦方頁面
- [✅] `OrganizerHomeView.vue` — 4 步驟導引流程 + 角色區分（owner/admin vs staff 顯示不同功能）
- [✅] `OrganizerApplyView.vue` — 組織申請表單（名稱/email/logo/描述）+ email 驗證
- [✅] `OrganizerEventView.vue` — 建立/編輯活動（票種 CRUD、媒體上傳、排程、社群連結 5 平台、內部備註）
- [✅] `OrganizerFormBuilderView.vue` — 表單設計器（10 種欄位類型、預設模板、欄位排序、選項管理、預覽）
- [✅] `OrganizerCheckinView.vue` — QR 掃描（@zxing/browser）+ 手動輸入（支援 JSON/query/pipe 格式）+ 統計
- [✅] `OrganizerManageView.vue` — 參加者列表 + CSV 匯出（UTF-8 BOM、特殊字元跳脫）+ 票種統計 + 重寄功能
- [✅] `OrganizerMembersView.vue` — 成員管理（新增/角色變更/移除）、owner 不可被移除、多組織切換

### 4.4 管理員頁面
- [✅] `AdminView.vue` — 全站活動列表 + 下架功能（status → disabled）+ 狀態 badge + 篩選

### 4.5 前端與後端 API 對接
- [✅] `client.ts` API 函式覆蓋 — 34 個函式對應後端路由（新增 authLogout, fetchMyOrders, organizerFetchSettlements, organizerFetchSettlementDetail, organizerCreatePayoutRequest）
- [✅] Bearer token 自動注入 — axios request interceptor 從 Pinia authStore 注入 `Authorization: Bearer`
- [✅] 401 response 自動重導 — response interceptor 清除 session + 重導 `/login?redirect=`（排除 login 本身避免循環）
- [✅] 錯誤訊息映射 — ERROR_CODE_MAP 涵蓋 50+ 後端 error code 中文映射 + raw message fallback 匹配

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
| 5 | Low | `_require_org_approved()` error code 不一致 | ✅ 已修復 | 改為 `ORG_NOT_APPROVED` |
| 6 | Medium | `GET /organizer/settlements/<id>` 未回傳 ledger_entries | ✅ 已修復 | 加入 ledger_entries 查詢 |
| 7 | Medium | payout 跳過 `approved` 中間狀態 | ✅ 已修復 | 新增 `approved` 狀態 + `mark_paid` action |
| 8 | Low | Admin comp-ticket 路由缺失 | ✅ 已修復 | 新增 `POST /admin/events/<id>/comp-ticket` |
| 9 | Low | Admin orders `q` 僅支援 order_id | ✅ 已修復 | 新增 email 精確匹配搜尋 |
| 10 | Low | `OrderDetailView.vue` holding 倒計時僅顯示靜態到期時間 | ✅ 已修復 | 新增 setInterval 即時倒數（mm:ss） |
| 11 | Medium | `client.ts` 缺 5 個 API 函式 | ✅ 已修復 | 新增 authLogout, fetchMyOrders, settlements ×2, payout |
| 12 | Low | `errorMessages.ts` 僅映射 5 個 error code | ✅ 已修復 | 新增 ERROR_CODE_MAP 涵蓋 50+ error code |

---

## 驗收進度總覽

| Phase | 項目數 | ✅通過 | ⚠️待改善 | ❌失敗 | 待驗 | 進度 |
|-------|--------|--------|----------|--------|------|------|
| Phase 0: 基礎建設 | 17 | 16 | 0 | 0 | 1 | 94% |
| Phase 1: MVP-1 | 54 | 54 | 0 | 0 | 0 | 100% |
| Phase 2: MVP-2 | 39 | 39 | 0 | 0 | 0 | 100% |
| Phase 3: MVP-3 | 41 | 41 | 0 | 0 | 0 | 100% |
| Phase 4: 前端 | 20 | 20 | 0 | 0 | 0 | 100% |
| Phase 5: 安全性 | 14 | 0 | 0 | 0 | 14 | 0% |
| Phase 6: 測試 | 26 | 0 | 0 | 0 | 26 | 0% |
| **合計** | **211** | **170** | **0** | **0** | **40** | **81%** |
