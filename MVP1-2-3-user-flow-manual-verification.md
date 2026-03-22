 # MVP-1~MVP-3 User Flow 手動驗證（端到端）

 > 目的：用「實際使用者的操作路徑」逐段打穿所有 MVP-1～MVP-3 功能，確認無邏輯漏洞、權限錯誤、狀態機錯轉、通知/金流/結算流程可用。
 >
 > 產出日期：2026-03-20
 >
 > 標註規則：完成後把 `[ ]` 改成 `[x]`。

 ---

 ## 0) 前置確認：你的 MVP 是否已實作完成？

 你現在的狀態可以視為：
 - ✅ MVP-1：程式 + DB + 手動驗證清單已存在（`mvp1-*`），功能閉環完整
 - ✅ MVP-2：程式 + DB + 單元測試已通過；ECPay 端到端、Hold 逾時、補償手動觸發仍需你在環境中跑一次確認
 - ✅ MVP-3：程式 + DB + 單元測試已通過；主辦方細權限、入駐審核、結算/提款、Audit、熱門/提醒/異動通知仍需手動驗證/確認通知是否真的寄出（看你的 `RESEND_API_KEY`）

 ---

 ## 1) 環境準備（同時覆蓋 MVP-1/2/3）

 - [ ] 1.1 啟動 Supabase（local）
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```
 - [ ] 1.2 套用 migrations（若你要乾淨重跑，建議 reset）
   ```bash
   supabase db reset
   ```
 - [ ] 1.3 啟動後端
   ```bash
   cd backend && pip install -r requirements.txt && flask run
   ```
 - [ ] 1.4 啟動前端
   ```bash
   cd frontend && npm install && npm run dev
   ```
 - [ ] 1.5 設定 `.env`
   - `backend/.env`：`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `ADMIN_ALLOWLIST`
   - `backend/.env`（MVP-2/3）：`ORG_APPROVAL_REQUIRED`、`PLATFORM_FEE_RATE`、`CRON_SECRET`
   - `backend/.env`（MVP-2）：ECPay 測試用 key：`ECPAY_MERCHANT_ID / ECPAY_HASH_KEY / ECPAY_HASH_IV / ECPAY_RETURN_URL / ECPAY_STAGE`
   - `frontend/.env`：`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
   - `backend/.env`（通知）：`RESEND_API_KEY`（有就驗證「真的有寄信」，沒有就驗證「後端有正確 stub/log」）

 ---

 ## 2) 測試帳號與資料（建議固定做一套，之後全照這套）

 你至少需要以下角色帳號（同一人也可以替換，但為了測權限建議分開）：
 - Guest：未登入
 - User（參加者）：登入一個帳號
 - Organizer Owner（主辦方擁有者）：登入一個帳號
 - Organizer Staff（主辦方工作人員，MVP-3.1 測用）：登入一個帳號
 - Platform Admin（MVP-1.5 + MVP-3.3 + MVP-3.4 測用）：登入一個帳號（在 `ADMIN_ALLOWLIST`）

 測試活動準備（建議 organizer owner 建 3～4 個 event）：
 - [ ] 2.1 建立 `Event A`：`status=published`，未開始/未結束（start/end 都在未來）
   - 票種：至少 1 張免費票（price=0）+ 至少 1 張付費票（price>0）
   - capacity/per_user_limit 設定好，用來驗超賣/限購（例如 capacity=1, per_user_limit=1）
 - [ ] 2.2 建立 `Event B`：`status=draft`（首頁/列表不可見）
 - [ ] 2.3 建立 `Event C`：`status=ended` 或 `status=cancelled`（不可再報名、不可核銷）
 - [ ] 2.4（可選）建立 `Event D`：`status=published`，用來測 Admin disable=disabled（下架）

 ---

 ## 3) Guest User Flow（MVP-1.0～1.5 + UX）

 - [ ] 3.1 開啟首頁（未登入）看到活動列表（僅 published）
 - [ ] 3.2 點任一活動進詳情頁，看到時間/地點/票種/描述
 - [ ] 3.3 對比「主辦方私密備註」：Guest 模式下詳情頁不應出現 internal note
 - [ ] 3.4 活動篩選（MVP-1.1）
   - [ ] 使用 styles/types 篩選，列表正確變化
   - [ ] （可選 API）`GET /api/v1/events?styles=...&types=...` 回傳符合條件
 - [ ] 3.5 進階搜尋/日期（若 UI 有做；至少 API 要通）
   - [ ] `GET /api/v1/events?q=...` 可回符合活動
   - [ ] `GET /api/v1/events?from=...&to=...` 回符合日期範圍
 - [ ] 3.6 活動詳情「分享活動」按鈕可複製永久 URL，貼到新分頁可開到同活動
 - [ ] 3.7 活動詳情「導航」按鈕（若活動有 map_url 或 lat/lng）能打開 Google Maps（外鏈正確）

 ---

 ## 4) User（參加者）User Flow：篩選 → 報名免費票 → 取得 QR（MVP-1）

 - [ ] 4.1 登入 User 帳號
 - [ ] 4.2 回首頁，用篩選（styles/types）找 `Event A`
 - [ ] 4.3 打開 `Event A` 詳情頁
 - [ ] 4.4 在免費票種完成報名（`/events/:eventId/register` 呼叫後成功）
 - [ ] 4.5 報名成功後轉到 /tickets（或你系統的「我的票券」）
 - [ ] 4.6 確認票券 QR 與 payload 可用
   - [ ] QR payload 內包含 `ticket_id` + `qr_secret`
   - [ ] 同一活動多張票時 `qr_secret` 不應重複
 - [ ] 4.7 限購測試（MVP-1.0/1.5 防呆）
   - [ ] 同一帳號同一 ticket type 超過 `per_user_limit` → 應回 400（error code：`PER_USER_LIMIT_EXCEEDED` 或 UI 顯示錯誤）
 - [ ] 4.8 狀態限制測試（MVP-1.5/1.5.3a）
   - [ ] 對 `Event B(draft)` 報名應拒絕（UI 或 API 錯誤碼）
   - [ ] 對 `Event C(ended/cancelled)` 報名應拒絕

 ---

 ## 5) Organizer Owner Flow：申請組織 → 創建活動 → 更新活動 → 建票種 → 表單 → 名單（MVP-1 + MVP-1.3 + MVP-3.1 前置）

 - [ ] 5.1 Organizer Owner 登入
 - [ ] 5.2 進 `/organizer/apply` 申請主辦方（建立 org）
 - [ ] 5.3 進 `/organizer/events/create` 建立 `Event A`：
   - [ ] status 設為 `published`
   - [ ] 設定 title/start_at/end_at/location/contact 等 metadata
 - [ ] 5.4 更新活動（測 MVP-1.5.2g/狀態限制）
   - [ ] 針對 published 活動的敏感欄位修改：必須有警告或限制
   - [ ] 對已售出票種：capacity < sold_count 應阻擋
   - [ ] 對 sold_count > 0 的票種刪除按鈕應 disabled 或回拒絕
 - [ ] 5.5 在活動頁/票種區建立 ticket type（capacity、per_user_limit、price/free）
 - [ ] 5.6 自訂報名表單（MVP-1.3）
   - [ ] 進 `/organizer/forms` 建立表單（至少 1 個欄位：dropdown 或 multi_select 或 date）
   - [ ] 綁定表單到對應 ticket type 或 event-level
   - [ ] 用 User 報名後確認表單欄位在報名頁顯示且 answers 被存起來
   - [ ] 回 `/organizer/manage` → `Attendees` 確認 answers 顯示正確
 - [ ] 5.7 管理名單與重寄（MVP-1.5.2c）
   - [ ] 在 Manage → Attendees 找到某張票，點「重寄票券」
   - [ ] 期待：後端觸發 resend；有 `RESEND_API_KEY` 時應真的收到信（沒有 key 則至少 log stub 有出）
 - [ ] 5.8 核銷統計 Dashboard（MVP-1.5.2d）
   - [ ] Manage → 選活動：顯示已入場/未入場 + 按票種統計

 ---

 ## 6) Organizer Owner Flow：核銷 verify + commit（MVP-1.0/1.0.6）

 - [ ] 6.1 進 `/organizer/checkin/:eventId`（或 checkin 頁）
 - [ ] 6.2 用 User 的 ticket payload 進行 Verify
   - [ ] 首次 Verify 回 `valid=true`、`can_checkin=true`
 - [ ] 6.3 Commit 第一次核銷
   - [ ] 回 `ok=true`、`already_checked_in=false`
 - [ ] 6.4 對同一張票再 Commit
   - [ ] 回 `ok=true`、`already_checked_in=true`
 - [ ] 6.5 負向測試：非主辦方成員核銷
   - [ ] 對同活動用另一個非 organizer 帳號 Verify，應回 FORBIDDEN
 - [ ] 6.6 狀態限制測試
   - [ ] 對 `Event C(ended/cancelled)` 核銷應阻擋（valid=false 或 can_checkin=false）

 ---

 ## 7) Organizer Staff Flow（MVP-3.1 細權限）

 - [ ] 7.1 由 Owner/admin 把某帳號加入成 `staff`（成員管理 API 或 UI）
 - [ ] 7.2 Staff 登入後進 `/organizer`
   - [ ] 僅看到「核銷」「名單」類入口
   - [ ] 不應看到「建立活動」「票種管理」「成員管理」入口
 - [ ] 7.3 Staff 呼叫/操作：
   - [ ] 不可 `POST /organizer/events`
   - [ ] 不可 `POST/PATCH /organizer/events/:id/ticket-types`
   - [ ] 可進行 verify + commit 核銷

 ---

 ## 8) MVP-2 付費購票與訂單狀態機（ECPay + Hold + 補償）

 ### 8.1 付費票購買 → Webhook → 出票（重點）
 - [ ] 8.1.1 準備：`ECPAY_RETURN_URL` 指到你的 ngrok HTTPS URL
 - [ ] 8.1.2 用 User 報名/購買 `Event A` 的付費票
 - [ ] 8.1.3 完成 ECPay 測試付款（測試卡號）
 - [ ] 8.1.4 等 webhook 回呼完成後：
   - [ ] order 從 `paid` → `issued`
   - [ ] tickets 已建立
   - [ ] `/tickets` 顯示該付費票券 QR

 ### 8.2 Hold 逾時釋放（名額可再賣）
 - [ ] 8.2.1 建立一筆付費票 `holding`：建立 order 後不要完成付款
 - [ ] 8.2.2 等 hold 超過逾時（可用 admin 觸發 release）
 - [ ] 8.2.3 呼叫 `POST /api/v1/admin/release-expired-holds`（Admin token）
 - [ ] 8.2.4 檢查：
   - [ ] 原 order → `cancelled`
   - [ ] 對應 ticket_type 的 hold_count 釋放
   - [ ] 其他 User 可再次 hold/購買（不應永遠 sold_out）

 ### 8.3 補償出票（paid 但未 issued）
 - [ ] 8.3.1 使用 admin API 觸發 `POST /api/v1/admin/compensate-paid-orders`
 - [ ] 8.3.2 期待：
   - [ ] 有缺漏時建立 tickets、order → issued
   - [ ] 沒缺漏時應回 0 且不破壞狀態
   - [ ] 重跑冪等，不重複建立 tickets

 ---

 ## 9) MVP-2.6 基礎退款（Admin 退款）

 - [ ] 9.1 找一筆已建立付費票的 order（paid/issued）
 - [ ] 9.2 Admin 呼叫退款接口：`POST /api/v1/admin/orders/:id/refund`
 - [ ] 9.3 期待：
   - [ ] refunds 表有新紀錄（requested → refunded/failed）
   - [ ] order/payment 狀態同步更新
   - [ ] 退款完成後（若有 Resend key）應收到 refund 完成通知
 - [ ] 9.4 核銷限制測試（退款後票應不可再核銷或至少核銷有效性應被阻擋）

 ---

 ## 10) MVP-3 佈建與治理（入駐審核 + 結算提款 + Audit + App 通知）

 ### 10.1 入駐審核（MVP-3.2）
 - [ ] 10.1.1 設定 `ORG_APPROVAL_REQUIRED=True`
 - [ ] 10.1.2 用新帳號申請 organizer → org 應為 `pending`
 - [ ] 10.1.3 pending org 嘗試建立活動：應回 ORG_NOT_APPROVED/403
 - [ ] 10.1.4 Admin 審核通過：`PATCH /admin/organizations/:id/approval` status=approved
 - [ ] 10.1.5 審核通過後可建立活動
 - [ ] 10.1.6 Admin 審核退件：status=rejected + rejection_reason
 - [ ] 10.1.7 rejected org 嘗試建立活動：應回拒絕

 ### 10.2 結算與提款（MVP-3.3）
 - [ ] 10.2.1 Admin 產生結算：`POST /api/v1/admin/settlements/generate`
 - [ ] 10.2.2 Organizer 檢查：`GET /api/v1/organizer/settlements` 有自己的批次
 - [ ] 10.2.3 Organizer 申請提款：`POST /api/v1/organizer/payout-requests`
 - [ ] 10.2.4 Admin 審核提款：`PATCH /api/v1/admin/payout-requests/:id` status=approved
 - [ ] 10.2.5 再次核准已 approved 的 request：應冪等或回明確拒絕

 ### 10.3 Audit logs 與 Admin 全站訂單（MVP-3.4）
 - [ ] 10.3.1 Audit 表：確認 `audit_logs` 存在
 - [ ] 10.3.2 Comp ticket：
   - [ ] Owner 或 Admin 呼叫 `POST /api/v1/organizer/events/:id/comp-ticket`
   - [ ] 檢查 audit_logs 出現 action=comp_ticket（resource_type=ticket）
 - [ ] 10.3.3 下架活動：
   - [ ] Admin 呼叫 `PATCH /admin/events/:id` status=disabled
   - [ ] 前端首頁不再顯示，且不可報名/不可核銷
   - [ ] audit_logs 出現 unpublish/unpublish_like action
 - [ ] 10.3.4 Admin 全站訂單總覽：
   - [ ] `GET /api/v1/admin/orders` 分頁與 filters 正確（至少確認 orders + payments/refunds 在同筆可追）

 ### 10.4 熱門/提醒/異動通知（MVP-3.5）
 - [ ] 10.4.1 熱門排序：首頁或 `GET /api/v1/events?sort=hot` 顯示 total_sold_count、排序合理
 - [ ] 10.4.2 活動提醒 job：
   - [ ] `POST /internal/jobs/event-reminders` 無 header → 401
   - [ ] header 錯 secret → 401
   - [ ] header 正確 secret → 200 回傳 `{1_day, 1_hour}`
   - [ ] 有 `RESEND_API_KEY` 時確認寄信；沒有時確認 log 有寫入
 - [ ] 10.4.3 活動異動/取消通知：
   - [ ] Admin 下架/取消活動後，參加者收到取消信
   - [ ] 主辦方修改 start_at/end_at 後，參加者收到異動信

 ---

 ## 11) 橫向檢查（一定要做，避免「流程通過但有風險」）

 - [ ] 11.1 Rate limit：對 login/register/checkin 建立超限請求，確認回 429 且錯誤碼/訊息一致
 - [ ] 11.2 權限：Staff 不可管理活動/票種/成員；Organizer 只能管理自己的 org
 - [ ] 11.3 API 錯誤格式：確認錯誤回 `{ "error": { "code", "message", "details" } }`（至少抽樣 10 次）
 - [ ] 11.4 冪等：重送 webhook、重跑 compensate、重複 commit 核銷均不產生重複資料

 ---

 ## 12) 最終簽核（你填這裡就是完成驗收的證據）

 - [ ] MVP-1：所有勾核項目已完成
 - [ ] MVP-2：付費 ECPay、Hold 逾時、補償、退款（若你測退款）已完成
 - [ ] MVP-3：入駐審核、結算提款、Audit、提醒/通知已完成

 記錄：
 - 日期：
 - 執行者：
 - 備註（例如：ECPay 用測試環境付款、通知因未設 RESEND 只能驗 log）：

