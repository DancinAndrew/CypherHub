# CypherHub 開發路線圖

> 整合自 AGENTS.md、ChatGPT-CypherHubCypherHub.md、note.md、GroovePass 藍圖  
> 原則：**可驗證、可執行**，每個項目都有明確的 Done 條件與驗收方式。

---

## 專案總覽

| 來源 | 內容 |
|------|------|
| **AGENTS.md** | 專案規範、Repo 結構、API 規格、Supabase 規則、防超賣、Non-Goals |
| **ChatGPT-CypherHubCypherHub.md** | MVP 進度、已完成/未完成清單、技術速查 |
| **note.md** | M1/M2/M3 細項拆解、RBAC、功能邊界 |
| **GroovePass 藍圖** | Phase 分組、Definition of Done、金流與庫存安全細節 |

---

## 階段一覽

| 階段 | 範圍 | 狀態 |
|------|------|------|
| **MVP-1.0** | 核心閉環（Auth + Events + 報名 + QR） | ✅ 完成 |
| **MVP-1.1** | 活動篩選（舞風/類型） | ✅ 完成 |
| **MVP-1.2** | 活動 metadata、私密備註 | ✅ 完成 |
| **MVP-1.3** | 自訂報名表單 | ✅ 完成 |
| **MVP-1.4** | 主辦方多頁流程 | ✅ 完成 |
| **MVP-1.5** | MVP-1 缺口補齊 | ⬜ 未做 |
| **MVP-2.1** | 訂單與 hold 機制 | ⬜ 未做 |
| **MVP-2.2** | 金流（ECPay） | ⬜ 未做 |
| **MVP-2.3** | 訂單狀態機 + 出票 | ⬜ 未做 |
| **MVP-2.4** | 庫存安全與背景任務（Phase 3） | ⬜ 未做 |
| **MVP-2.5** | 報名表單擴充（Phase 4.1） | ⬜ 未做 |
| **MVP-2.6** | 基礎退款（Phase 4.2） | ⬜ 未做 |
| **MVP-3.1** | 主辦方成員細權限 | ⬜ 未做 |
| **MVP-3.2** | 主辦方入駐審核 | ⬜ 未做 |
| **MVP-3.3** | 結算與提款 | ⬜ 未做 |
| **MVP-3.4** | 平台治理與 Audit | ⬜ 未做 |

---

# MVP-1 詳細規格

## MVP-1.0 核心閉環 ✅

**目標**：活動 → 報名 → 出票 → QR 核銷 完整跑通。

### 1.0.1 使用者註冊 / 登入 / 登出

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 註冊 | Email + 密碼，Supabase Auth | 可註冊新帳號並登入 |
| 登入 | Email + 密碼 | 登入後可存取 `/tickets` |
| 登出 | 清除 session | 登出後 `/tickets` redirect 到 `/login` |
| Email 驗證 | 可選（建議驗證不強制） | 註冊後可收信確認 |

**驗收**：未登入造訪 `/tickets` → 導向 `/login?redirect=/tickets`；登入後回到 `/tickets`。

---

### 1.0.2 公開活動列表與詳情

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| GET /events | 只回 published 活動 | `curl /api/v1/events` 有資料 |
| GET /events/:id | 活動詳情含 ticket_types | 活動頁顯示時間、地點、票種 |
| 訪客可看 | 不需登入 | 未登入可開 `/events/:id` |

**驗收**：首頁與活動詳情不需登入即可瀏覽。

---

### 1.0.3 免費報名

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 需登入 | 未登入 → redirect login | 按報名鈕時導向登入 |
| POST /events/:id/register | 呼叫 register_free RPC | 報名成功回傳 ticket |
| 防超賣 | DB 原子扣量（FOR UPDATE） | 併發報名不超賣 |
| 每人限購 | per_user_limit 檢查 | 超過 limit 回 PER_USER_LIMIT_EXCEEDED |

**驗收**：同一 user 對同一 ticket_type 超過限購時 API 回 400。

---

### 1.0.4 我的票券與 QR

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| GET /me/tickets | 只回該 user 的票 | RLS 生效 |
| QR payload | `{ticket_id, qr_secret}` JSON | 前端顯示 QR，核銷時可掃 |
| 票券唯一 | qr_secret 不可猜 | 每張票不同 qr_secret |

**驗收**：登入後 `/tickets` 顯示票券與 QR，Copy Payload 可複製。

---

### 1.0.5 主辦方申請與活動建立

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| POST /organizer/apply | 建立 org + owner 成員 | 申請後有 org_id |
| POST /organizer/events | 建立活動 | 可建立 published 活動 |
| POST /organizer/events/:id/ticket-types | 建立票種 | 可設 capacity、per_user_limit |

**驗收**：主辦方可建立活動與票種，首頁可見該活動。

---

### 1.0.6 QR 核銷

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| Verify | 檢查票是否有效、未核銷 | valid=true, can_checkin=true |
| Commit | 原子更新 status=checked_in | 第一次 ok=true, already_checked_in=false |
| 冪等 | 重複 commit | 第二次 ok=true, already_checked_in=true |
| 權限 | 僅 organizer member | 非成員 Verify 回 FORBIDDEN |

**驗收**：主辦方掃 QR → Verify → Commit；再 Commit 同一張票 → already_checked_in=true。

---

## MVP-1.1 活動篩選 ✅

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| dance_styles | 舞風篩選 | GET /events?styles=hiphop,popping |
| event_types | 活動類型篩選 | GET /events?types=cypher,battle |
| 前端 UI | 篩選按鈕 | HomeView 可勾選篩選 |

**驗收**：切換篩選後列表變化正確。

---

## MVP-1.2 活動 Metadata 與私密備註 ✅

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| registration_start_at/end_at | 報名時間 | 活動詳情顯示 |
| map_url, contact_email/phone | 聯絡與地圖 | 活動詳情顯示 |
| socials, schedule | 社群與流程 | 活動詳情顯示 |
| internal_note | 主辦方私密備註 | Guest 看不到；主辦方編輯時可見 |

**驗收**：Guest 開活動頁無 internal_note；主辦方載入活動可編輯 internal_note。

---

## MVP-1.3 自訂報名表單 ✅

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| event_forms 表 | event-level / ticket-type-level | 可建立表單 |
| DynamicForm | 依 schema 動態渲染 | 選票種後顯示表單欄位 |
| answers 存檔 | ticket_form_responses | 主辦方 attendees 可看 answers |

**驗收**：主辦方設表單 → 用戶報名填欄位 → 主辦方名單可見 answers。

---

## MVP-1.4 主辦方多頁流程 ✅

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| /organizer | 主辦方首頁 | 可選 Apply / Events / Forms |
| /organizer/apply | 申請主辦方 | 獨立頁 |
| /organizer/events | 活動列表與建立 | 獨立頁 |
| /organizer/forms | Form Builder | 獨立頁 |
| /organizer/checkin/:eventId | 核銷 | 可掃碼或手動輸入 |

**驗收**：主辦方導覽可從首頁到各子頁。

---

## MVP-1.5 MVP-1 收尾與穩定化 (Phase 1: Polish) ⬜

> **GroovePass Phase 1**：補齊遺漏的基礎體驗，為後續金流打底。

以下為規格中應有但尚未實作，**可驗證、可執行**。依 GroovePass 藍圖分為三組：

### 1.5 帳號與通知基礎（Phase 1.1）

#### 1.5.1 忘記密碼 / 重設密碼

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 忘記密碼連結 | 登入頁「忘記密碼」 | 點擊導向 Supabase password reset |
| 重設密碼頁 | 或 Supabase 內建連結 | 收信後可設新密碼 |
| 依賴 | Supabase Auth `resetPasswordForEmail` | 需設定 Site URL / Redirect |

**Done 條件**：登入頁有「忘記密碼」→ 輸入 email → 收信 → 點連結可重設密碼。

#### 1.5.1b 個人資料編輯

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| profiles 表 | 已有 display_name, avatar_url, phone 等 | - |
| 前端 | /profile 或設定頁 | 可編輯暱稱、手機、社群連結 |
| 頭像 | 選填，Storage 上傳 | 可選做或延後 |

**Done 條件**：登入用戶可編輯 display_name 並保存。

#### 1.5.1c Email 寄送服務串接

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| email_service | 從 stub 改為串接 Resend/SendGrid/SES | 實際可寄信 |
| 報名成功通知 | 報名成功後自動觸發，內容含 QR | 報名後收信 |

**Done 條件**：報名成功後收信，內容含活動與票券資訊。

---

### 1.5.2 視覺與主辦方擴充（Phase 1.2）

#### 1.5.2a 活動圖片管理

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 主辦方後台 | 建立/編輯活動時可上傳圖片至 Storage | 上傳後寫入 event_media |
| 活動詳情頁 | 前端實作圖片輪播 UI | 有圖時顯示輪播 |
| Storage policy | RLS 限制 organizer 可寫 | - |

**Done 條件**：主辦方可上傳活動圖片，活動詳情顯示輪播。

#### 1.5.2b 主辦方資訊與其他活動

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 活動詳情 | 顯示主辦方名稱、簡介 | 有 org 基本資訊 |
| 其他活動 | 同主辦方其他 published 活動 | 可點進其他活動 |

**Done 條件**：活動詳情頁有主辦方區塊，並列出該主辦方其他活動。

#### 1.5.2c 主辦方代參加者重寄票券

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| API | POST /organizer/events/:id/attendees/:ticket_id/resend | 主辦方觸發 |
| 權限 | 僅 organizer member | RLS/service 檢查 |

**Done 條件**：主辦方在名單中可對某張票觸發重寄。

#### 1.5.2d 核銷統計 Dashboard

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 前端 | 核銷頁顯示已入場/未入場、按票種 | 有數字與列表 |
| 資料 | attendees API 已有 status | 前端彙總顯示 |

**Done 條件**：核銷頁顯示「已入場 N / 未入場 M」及按票種統計。

---

### 1.5.3 平台治理基礎（Phase 1.3）

#### 1.5.3a 後台前端介面

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| /admin 路由 | Admin 專用頁 | allowlist 用戶可進 |
| 活動列表 | GET /admin/events | 顯示全站活動 |

**Done 條件**：Admin 可進入 /admin 並看到活動列表。

#### 1.5.3b 下架活動 API

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| API | PATCH /admin/events/:id，實作 status=disabled | 目前回 501 需改為實作 |
| 前端 | 下架按鈕 | 點擊後活動不再公開 |

**Done 條件**：Admin 可下架活動，下架後 GET /events 不回該活動。

#### 1.5.3c Rate Limiting

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| extensions | 已有 stub，接上 flask-limiter 或類似 | 實際生效 |
| 限制 | 登入、報名、核銷等 | 超限回 429 |

**Done 條件**：短時間大量請求登入/報名時回 429。

---

# MVP-2 詳細規格

> **GroovePass Phase 2–4**：嚴格禁止複雜退款或折扣碼。專注訂單狀態機與綠界串接。

## MVP-2.1 訂單系統與庫存保留 (Phase 2 + 3.1) ⬜

### 2.1.1 DB 與模型

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| orders 表 | order_id, user_id, status, total_cents 等 | migration |
| order_items 表 | order_id, ticket_type_id, quantity, price_cents | migration |
| payments 表 | order_id, provider, external_id, amount, status | migration |

**Done 條件**：migrations 可套用，RLS 設定完成。

---

### 2.1.2 Hold 與逾時

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 選票種 → 建立 order | status=holding | 不付款不入庫 |
| hold 扣名額 | 原子扣 capacity（或 hold_count） | 同 ticket_type 邏輯 |
| hold_timeout | 例如 15 分鐘 | 逾時自動取消並釋放 |
| 釋放 | 更新 sold_count / hold_count | 名額可再賣 |

**Done 條件**：Hold 建立後不付款，逾時後名額釋放，他人可再買。

---

## MVP-2.2 綠界金流 ECPay (Phase 2.2) ⬜

### 2.2.1 結帳流程與 Webhook

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 建立付款 | 導向 ECPay 金流頁 | 可完成測試付款 |
| Webhook | 接收付款結果 | 驗簽、冪等處理 |
| webhook_event_id | 去重 | 重送不重複出票 |

**Done 條件**：前端結帳頁 → 產生綠界訂單與 Form 參數 → 跳轉付款 → Webhook 驗簽、冪等處理、記錄 webhook_event_id；僅 paid 觸發出票。

---

### 2.2.2 訂單狀態機

| 狀態流 | 說明 |
|--------|------|
| created | 訂單建立 |
| holding | 名額保留中 |
| pending_payment | 已導向付款 |
| paid | 付款成功（Webhook 確認） |
| issued | 已出票 |
| cancelled | 逾時或手動取消 |
| refunded | 已退款 |

**Done 條件**：僅 `paid` 可轉 `issued`；狀態流符合規格。

---

## MVP-2.3 出票與補償 ⬜

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| paid → issued | Webhook 收到 paid 後建立 tickets | 同 register_free 邏輯 |
| 補償任務 | paid 但未 issued 可重跑 | 背景 job 或手動觸發 |
| 冪等 | 已 issued 不再建立 | 重跑安全 |

**Done 條件**：付款成功後自動出票；補償 job 可處理漏單。

---

## MVP-2.4 庫存安全與背景任務 (Phase 3) ⬜

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 逾時釋放 | holding 逾時 → cancelled + 釋放名額 | 定時 job 掃描 |
| 補償出票 | paid 但未 issued 自動補償 | 背景任務或手動觸發 |
| Webhook 重試 | provider 重送時冪等，不重複出票 | 同筆回呼只處理一次 |
| 防超賣測試 | concurrency/race 測試 | pytest 併發搶票情境，DB transaction 正確鎖定 |

**Done 條件**：RQ/Redis 或類似 queue；上述 job 可執行；有併發測試。

---

## MVP-2.5 報名表單擴充 (Phase 4.1) ⬜

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 新欄位型別 | 下拉、單選、多選、日期 | DynamicForm 支援 |
| 票種綁定 | 不同票種可設不同表單欄位 | event_forms 已有 ticket_type_id |
| 名單匯出 | 主辦方匯出參加者（含 answers）為 CSV | GET 或 POST 產生 CSV |

**Done 條件**：主辦方可匯出 CSV；表單支援更多欄位型別。

---

## MVP-2.6 基礎退款 (Phase 4.2) ⬜

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 全額退款 | 或主辦方核准其中一種 | 先選一種實作 |
| 退款狀態 | requested / refunded / failed | 表與 API |
| 退款完成 | 呼叫金流退款 API | 成功後更新狀態 |
| 退款通知 | 退款完成後 Email | - |

**Done 條件**：可發起退款，主辦方或平台核准後執行，狀態與通知正確。

---

# MVP-3 詳細規格

## MVP-3.1 主辦方成員細權限 ⬜

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| owner / admin / staff | 角色細分 | organizer_members.role |
| admin | 可管理活動，不可改收款 | - |
| staff | 可核銷指定活動 | 可限制活動範圍 |
| 權限檢查 | API 與 RLS | 依角色限制操作 |

**Done 條件**：staff 只能核銷、不能建立活動；admin 可管理不能改結算。

---

## MVP-3.2 主辦方入駐審核 ⬜

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 申請狀態 | pending / approved / rejected | - |
| Admin 審核 | 通過/退件 | Admin 可操作 |
| 通過後 | 可建立活動 | - |
| 收款資訊 | 銀行帳戶等 | 審核時或通過後填寫 |

**Done 條件**：申請後需 Admin 核准才能建立活動。

---

## MVP-3.3 結算與提款 ⬜

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| settlements 表 | 週期、金額、平台費、淨額 | - |
| ledger_entries | 每筆交易分錄 | - |
| payout_requests | 提款申請 | requested / approved / paid / failed |
| 平台抽成 | 可設定比例 | - |

**Done 條件**：可產生結算批次，主辦方可申請提款，Admin 可審核。

---

## MVP-3.4 平台治理與 Audit（Phase 7） ⬜

> **GroovePass Phase 7**：營運治理與審計。

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| audit_logs | 退款、補票、結算、提款、下架等關鍵操作 | 重要操作有紀錄 |
| 異常告警 Dashboard | 付款成功未出票、核銷失敗率異常 | 後台監控面板 |
| 全站訂單總覽 | Admin 可查全站訂單、付款、退款、Webhook | 後台介面 |
| 手動補票 (Comp) | 主辦方/Admin 手動發放公關票，強制寫入 Audit | 有 Comp 按鈕且 audit 有紀錄 |
| Admin 治理 | 活動下架、主辦方封鎖 | - |

**Done 條件**：Critical 操作寫入 audit_logs；Admin 有全站查詢與 Comp 功能。

---

# Explicit Non-Goals（禁止提前）

| 階段 | 不做 |
|------|------|
| MVP-1 | 金流、退款、分潤、折扣碼、轉讓、候補、進階報表、站內通知、簡訊/LINE |
| MVP-2 | 部分退款、複雜退票規則、折扣碼、平台分潤自動化、拒付/爭議款 |
| MVP-3 之後 | 風控規則引擎、拒付全流程、成長工具、裝置登入管理、2FA |

---

# Phase 8：Definition of Done（每個 Phase 的 PR 標準）

> **GroovePass Phase 8**：每個 Phase 的 PR 必須嚴格遵守以下條件才可合併。

| 類別 | 條件 |
|------|------|
| **DB 變更** | 必須包含 Migration SQL 與對應的 RLS policies，並備註預期權限行為 |
| **測試覆蓋** | `pytest -q` 必須通過；金流與核銷相關 API 必備 Unit & Integration Test |
| **程式碼品質** | 後端通過 `ruff check .` 與 `ruff format .`；前端無 Build 錯誤 |
| **安全規範** | 嚴禁將 Secrets（如 SUPABASE_SERVICE_ROLE_KEY）寫入前端或 Git；僅修改 `.env.example` |

---

# 建議執行順序

1. **補齊 MVP-1.5**（擇一或依序）  
   - 1.5.1 帳號與通知：Email 串接、忘記密碼、個人資料  
   - 1.5.2 視覺與主辦方：圖片上傳/輪播、主辦方代寄、核銷統計  
   - 1.5.3 平台治理：Admin 前端、下架活動、Rate limiting  

2. **MVP-2** 依序  
   - 2.1 訂單與 hold → 2.2 ECPay → 2.3 出票 → 2.4 背景任務 → 2.5 表單擴充 → 2.6 退款  

3. **MVP-3** 依序  
   - 3.1 成員權限 → 3.2 審核 → 3.3 結算提款 → 3.4 Audit 與治理  

---

# 參考文件

- [AGENTS.md](../AGENTS.md) - 專案規範、API、Supabase、防超賣
- [ChatGPT-CypherHubCypherHub.md](../ChatGPT-CypherHubCypherHub.md) - 進度總覽
- [note.md](../note.md) - M1/M2/M3 細項
- [verification-report.md](./verification-report.md) - 功能驗證對照
