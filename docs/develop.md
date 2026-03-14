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
| **MVP-2.7** | 次要金流 PayPal（可選） | ⬜ 未做 |
| **MVP-3.1** | 主辦方成員細權限 | ⬜ 未做 |
| **MVP-3.2** | 主辦方入駐審核 | ⬜ 未做 |
| **MVP-3.3** | 結算與提款 | ⬜ 未做 |
| **MVP-3.4** | 平台治理與 Audit | ⬜ 未做 |
| **SEC-1** | 傳輸與端點安全（HTTPS、CORS、Headers） | ⬜ 未做 |
| **SEC-2** | 身份與資料保護（帳密、URL、敏感資料） | ⬜ 未做 |
| **SEC-3** | 注入與攻擊防護（SQL、XSS、CSRF、Rate limit） | ⬜ 未做 |
| **SEC-4** | Secrets 與部署檢查（環境變數、錯誤、日誌） | ⬜ 未做 |

---

## 開發環境

| 操作 | 指令 | 說明 |
|------|------|------|
| 切換本地 Supabase | `./scripts/use-local-supabase.sh` | 複製 `.env.local.example` → `.env`，連本地 DB |
| 切換雲端 Supabase | `./scripts/use-cloud-supabase.sh` | 複製 `.env.cloud.example` → `.env`，連 Cloud |
| 套用 migrations（本地） | `supabase db reset` | 依序套用 migrations 與 seed |
| 套用 migrations（雲端） | `./scripts/push-to-cloud.sh` | `supabase db push` 到 Cloud |
| Cloud 種子資料 | `python scripts/seed-cloud-test-data.py` | 需已填入 Cloud 的 `SUPABASE_SERVICE_ROLE_KEY` |

詳見 [local-cloud-switch.md](./local-cloud-switch.md)。

---

## 推薦套件與工具（對照 [Tools.md](./Tools.md)）

> 能用現成套件/服務就不手刻，以下對應 [docs/Tools.md](./Tools.md) 工具選單與 CypherHub 功能。

### Tools.md 工具 → 功能對照（建議採用）

| 工具 | 用途 | 對應 develop 項目 | 備註 |
|------|------|------------------|------|
| **Resend** | 交易型郵件（報名確認、重寄票、驗證信） | 1.5.1c Email 寄送 | 已列在 backend requirements，直接串接取代 stub |
| **Sentry** | 錯誤追蹤（前/後端 exception、source map） | 上線前建議 | 可選；MVP-1.5 或 MVP-2 前接入 |
| **flask-limiter** | API 頻率限制 | 1.5.3d Rate Limiting | 後端加 `flask-limiter`，配合 Redis 或 memory |
| **Stripe** | 金流（信用卡、webhook、refund） | MVP-2.2 付費票 | 若不做台灣綠界可優先 Stripe；台灣線下/ATM 則 ECPay |
| **UptimeRobot** | HTTP/ping 監控、故障告警 | 部署後 | 監控 API 與前端可用性 |
| **Vercel** | 前端/全端部署、Preview 分支 | 部署 | 適合 Vue/Vite 靜態站 |
| **Cloudflare** | DNS、CDN、DDoS、SSL | 部署 | 網域解析與快取 |
| **PostHog** | 產品分析、事件、Session 錄影、Feature flags | 可選 | 開源可自架；MVP-3 或上線後 |
| **Namecheap** | 網域註冊與 DNS | 上線 | 與 Cloudflare 擇一或並用 |
| **Clerk** | Auth（登入/OAuth/2FA） | 非必 | 目前用 Supabase Auth，僅在要替換時考慮 |
| **Pinecone / FAISS** | 向量搜尋、相似推薦 | 進階 | 活動推薦、搜尋優化等；MVP-3 之後 |

### 不建議重造輪子的項目

- **忘記/重設密碼**：Supabase Auth 內建 `resetPasswordForEmail`，不需額外套件。
- **Email 寄送**：用 Resend（已納入專案），不要手刻 SMTP。
- **活動圖片**：Supabase Storage + RLS，不需另建圖床。
- **Rate limiting**：用 `flask-limiter`，不要自己計數。

---

## 未實作功能 — 建議套件／平台／開源

> 以下對應 develop 未做項目，可用現成套件或開源方案取代/加速實作。

| 功能區塊 | develop 章節 | 建議方案 | 說明 |
|----------|--------------|----------|------|
| **背景任務（hold 逾時、補償出票）** | MVP-2.1 / 2.4 | **Redis + RQ** 或 **Celery**；或 **Supabase pg_cron + Edge Functions** | RQ 輕量、Celery 功能多；若全在 Supabase 可考慮 pg_cron 定時掃 + Edge 出票 |
| **金流** | MVP-2.2 / 2.7 | **ECPay**（台灣）、**Stripe**（國際）、**PayPal**（可選） | 見 Tools.md；Webhook 驗簽與冪等需自實作，無現成「整包」可取代 |
| **訂單狀態機** | MVP-2.2 / 2.3 | 自實作 | 可參考 **python-statemachine** 或 **transitions** 做狀態轉換與守衛 |
| **報名表單擴充（下拉/單選/多選/日期）** | MVP-2.5 | 擴充現有 DynamicForm schema | 不需新套件，在既有 JSON schema 加 type + options |
| **名單匯出 CSV** | MVP-2.5 | 後端 `csv` 標準庫或 **pandas** | 簡單用 `csv.writer`；要 Excel 可 **openpyxl** |
| **退款** | MVP-2.6 | 金流商 API（ECPay/Stripe refund） | 無獨立開源「退款服務」，依既有金流 API 實作 |
| **結算與提款** | MVP-3.3 | **Stripe Connect**（若用 Stripe）或自建 ledger | 分潤/提款多數自建；Stripe Connect 可處理「主辦方收款與平台抽成」 |
| **Audit 日誌** | MVP-3.4 | **Supabase Audit**（pg 擴展）、或自建 `audit_logs` 表 | 關鍵操作寫入 audit 表；進階可查 **pgAudit** |
| **進階搜尋（全文/日期）** | 1.5.2e | **Postgres full-text search**（`tsvector`） | 先不引入 Elasticsearch；日期篩選用 `start_at` 區間即可 |
| **異常告警 / Dashboard** | MVP-3.4 | **Sentry**（錯誤）、**UptimeRobot**（可用性）、**Grafana + Prometheus**（自架） | 小規模 Sentry + UptimeRobot 即可 |
| **主辦方細權限（RBAC）** | MVP-3.1 | 自實作 + RLS | 角色已在 domain 定義，用 `organizer_members.role` + RLS policy 即可，無需引入 Casbin 等 |

### 開源專案參考（可研究、不一定要用）

- **ticketing**：各語言都有開源售票（如 [Attendize](https://github.com/attendize/attendize) PHP），多數偏重活動報名與金流，可參考流程與狀態設計，不建議直接取代現有 stack。
- **Stripe 範例**：[stripe-payments-demo](https://github.com/stripe-samples) 可參考 webhook、idempotency、refund 流程。
- **任務佇列**：[RQ (Redis Queue)](https://github.com/rq/rq)、[Celery](https://docs.celeryq.dev/)。

---

### 本地開發啟動指令（來自 AGENTS.md）

| 情境 | 指令 |
|------|------|
| **Docker Compose（推薦）** | `docker compose -f infra/docker-compose.yml up --build` |
| 停止 | `docker compose -f infra/docker-compose.yml down` |
| **Backend 本機** | `cd backend` → `python -m venv .venv && source .venv/bin/activate` → `pip install -r requirements.txt` → `flask --app app run --debug` |
| **Frontend 本機** | `cd frontend` → `npm i` → `npm run dev` |

---

# MVP-1 已完成功能對照表

> 供新開發者快速掌握既有實作位置，避免重複開發。

| 功能 | 實作位置 | API / 檔案 |
|------|----------|------------|
| 註冊 / 登入 / 登出 | Supabase Auth | `LoginView.vue`、`stores/auth.ts` |
| 活動列表（篩選） | 首頁 | `HomeView.vue`、`GET /api/v1/events?styles=&types=` |
| 活動詳情 | 活動頁 | `EventDetailView.vue`、`GET /api/v1/events/:id` |
| 免費報名（防超賣） | register_free_v2 RPC | `POST /api/v1/events/:id/register`、`0003/0011` migrations |
| 動態報名表單 | Form Builder | `DynamicForm.vue`、`event_forms`、`register_free_v2` |
| 我的票券 + QR | 票券頁 | `MyTicketsView.vue`、`GET /api/v1/me/tickets` |
| 主辦方申請 | Organizer | `POST /api/v1/organizer/apply`、`OrganizerApplyView.vue` |
| 活動建立 / 編輯 | Organizer | `OrganizerEventView.vue`、POST·PATCH `/organizer/events` |
| 票種管理 | Organizer | `POST /organizer/events/:id/ticket-types` |
| 活動 metadata / 私密備註 | 活動管理 | `0007/0008` migrations、internal-note API |
| 名單查詢（含 answers） | Attendees | `GET /organizer/events/:id/attendees` |
| QR 核銷（掃碼 + 手動） | 核銷頁 | `OrganizerCheckinView.vue`、verify + commit API |
| Admin 活動列表 | Admin | `GET /admin/events`、allowlist 驗證 |

**DB 原子性**：`register_free_v2` 使用 `FOR UPDATE` 鎖定 ticket_type，防止超賣。**QR 安全性**：payload 含 `ticket_id` + 隨機 `qr_secret`（`encode(gen_random_bytes(16), 'hex')`），查表比對；可選 HMAC(ticket_id, server_secret)。禁止可猜 id、自增 id、短碼無簽名。

---

## 系統架構與規範（來自 AGENTS.md）

- **API 路由**：Base `/api/v1`，JSON only，Auth 用 `Authorization: Bearer <SUPABASE_ACCESS_TOKEN>`
- **後端目錄**：`backend/app/blueprints/`（auth、events、registrations、checkin、admin 等）、`services/`、`domain/`
- **JWT 驗證**：Backend 必須驗 JWT（JWKS）或將 JWT 帶入 Supabase；`user_id` 僅從 token 解析，**禁止信任 client 傳入**
- **錯誤格式**：`{ "error": { "code": "...", "message": "...", "details": ... } }`

### 完整 RBAC（角色與權限，來自 note.md）

| 角色 | 檢視邊界 | 可執行操作 |
|------|----------|------------|
| **Guest（訪客）** | 活動列表、活動詳情（published） | 無；需登入才能報名 |
| **User（一般使用者）** | 自己 tickets、profiles、orders（MVP-2） | 報名、看票券、重寄自己的票 |
| **Organizer Owner** | 自己 org 的 events、ticket_types、attendees | 建立/編輯活動、票種、表單、核銷、代寄票券 |
| **Organizer Admin** | 同 Owner，不可改收款 | 管理活動、不可改結算設定 |
| **Staff** | 被授權的活動名單 | 僅核銷、查看該活動 attendee；付費票未付款不可核銷 |
| **Admin** | 全站活動、主辦方、訂單、金流 | 審核、下架、封鎖、結算、調帳 |

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

**實作備註**：重設密碼信中的連結會導向前端 `/reset-password`。請在 Supabase Dashboard → Authentication → URL Configuration → Redirect URLs 加入 `http://localhost:5173/reset-password`（及正式環境網址）。

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

#### 1.5.2e 進階搜尋與篩選（來自 note.md）

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 關鍵字搜尋 | 活動名/主辦方/地點（LIKE 或全文） | GET /events?q=... |
| 日期篩選 | 指定日期區間 | GET /events?from=&to= |
| 地區篩選 | 依 location / region | 可選，依 taxonomy |
| 票價篩選 | 免費/付費 | MVP-1 僅免費；MVP-2 可加 |

**Done 條件**：活動列表支援關鍵字搜尋；日期篩選可選實作。

#### 1.5.2f 活動分享連結

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 永久網址 | `/events/:eventId` 可分享 | 複製連結可開啟活動詳情 |
| 前端 | 活動詳情頁「分享」按鈕 | 複製 URL 或產生短網址 |

**Done 條件**：活動詳情頁有分享按鈕，可複製活動永久網址。

#### 1.5.2g 活動編輯限制（主辦方防呆）

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 已上架活動 | 對已 published 活動，某些欄位編輯時需警告或限制 | 如時間、票種已售出後不可隨意改 |
| 警告 | 修改敏感欄位時彈出確認 | 前端實作 |
| 限制 | 已售出票種不可刪除或改 capacity 小於已售 | API 與 RLS |

**Done 條件**：主辦方編輯已上架活動時，敏感欄位有警告或限制。

---

### 1.5.3 平台治理基礎（Phase 1.3）

#### 1.5.3a 活動狀態機完整流轉

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 狀態流 | 草稿 (Draft) → 上架 (Published) → 結束/取消 (Ended/Cancelled) | events.status enum |
| 草稿 | 建立時可選 draft，GET /events 不回草稿 | 僅主辦方可見 |
| 上架 | draft → published，公開可見 | 首頁與詳情可見 |
| 結束/取消 | 活動後設 ended，或手動 cancelled | 已結束/取消的活動不可報名、不可核銷 |
| 下架 | status=disabled 或 cancelled | GET /events 只回 published |

**Done 條件**：主辦方可建立草稿、上架、標記結束；已取消活動不可核銷；下架後不再出現在公開列表。

#### 1.5.3b 後台前端介面

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| /admin 路由 | Admin 專用頁 | allowlist 用戶可進 |
| 活動列表 | GET /admin/events | 顯示全站活動 |

**Done 條件**：Admin 可進入 /admin 並看到活動列表。

#### 1.5.3c 下架活動 API

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| API | PATCH /admin/events/:id，實作 status=disabled | 目前回 501 需改為實作 |
| 前端 | 下架按鈕 | 點擊後活動不再公開 |

**Done 條件**：Admin 可下架活動，下架後 GET /events 不回該活動。

#### 1.5.3d Rate Limiting

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| extensions | 已有 stub，接上 flask-limiter 或類似 | 實際生效 |
| 限制 | 登入、報名、核銷等 | 超限回 429 |
| 註 | MVP-2 Phase 3 需再擴展：下單、付款、核銷、登入 | note.md 系統層 |

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

## MVP-2.7 次要金流 PayPal（可選）⬜

> **來源**：AGENTS.md、note.md。綠界優先，PayPal 可於 MVP-2.5 或 MVP-3 擴充。

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| PayPal 串接 | 與 ECPay 並存，依付款方式選擇 | 可選 PayPal 完成付費購票 |
| Webhook | 驗簽、冪等、webhook_event_id 去重 | 同 ECPay 規範 |
| 預留 | payment_service 設計時預留 provider 抽象 | 便於新增金流 |

**Done 條件**：可選 PayPal 付款；或至少架構預留、文件標註擴充點。

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
| **平台進階治理設定** | 退款規則模板、Email 通知模板管理 | Admin 後台可設定 |
| | 黑名單/限購規則（進階：封鎖 user/email/ip） | 可選，note.md 3.5 |
| **進階分析報表** | 銷售概覽（總收入、票數） | 主辦方報表 |
| | 時間序列（每小時/每日售票） | 圖表或 CSV |
| | 匯出報表 | 銷售/核銷/名單 |
| **進階財務比對** | 交易對帳差異比對（金流記錄 vs 平台 ledger） | Admin 後台，note.md 3.3 可選 |

**Done 條件**：Critical 操作寫入 audit_logs；Admin 有全站查詢與 Comp；平台設定與進階報表可選實作。

---

## MVP-3.5 使用者端擴充（來自 note.md M3）⬜

> M3 規劃中面向使用者的功能，可選實作。

| 項目 | 說明 | 驗證方式 |
|------|------|----------|
| 熱門活動列表 | 活動列表「熱門」標籤或排序（定義熱門規則） | 首頁可顯示熱門 |
| 活動提醒 Email | 前一天/前一小時提醒 | 背景 job 發送 |
| 活動異動/取消通知 | 活動時間變更或取消時 Email 通知參加者 | 異動時觸發 |

**Done 條件**：上述功能可選實作；若實作需有對應 API 與 job。

---

# Phase SEC：上線前資安驗證

> 上線前必須完成的資安檢查。依序驗證各項，並勾選 Done 條件。建議在 MVP-1.5 補齊後、正式對外前執行。

## 專案目前資安狀態（摘要）

| 項目 | 現況 | 說明 |
|------|------|------|
| **傳輸加密** | 本地 HTTP，上線需 HTTPS | 生產環境必須 HTTPS；Supabase 連線本身為 HTTPS |
| **帳密** | 密碼欄位 `type="password"` | Supabase Auth 處理，不經 CypherHub backend |
| **URL 敏感資料** | 重設密碼 token 在 hash | Supabase 標準流程，一次性 token；需避免將 email/token 寫入一般 query |
| **SQL Injection** | 使用 Supabase client + RPC | 參數化查詢；無手寫 raw SQL 串接使用者輸入 |
| **XSS** | Vue 預設 escape | 需審查 `v-html`、`innerHTML`、動態插入 |
| **CSRF** | API 用 Bearer token | 非 cookie-based，典型 CSRF 風險較低 |
| **Rate limiting** | 未實作 | 登入、報名、核銷等高風險 endpoint 建議加限流 |
| **Secrets** | .env 在 .gitignore | 需確認無 key 寫入程式碼、log、前端 bundle |

---

## SEC-1：傳輸與端點安全 ⬜

| 項目 | 說明 | 驗證方式 | 現況 |
|------|------|----------|------|
| **HTTPS** | 生產環境全站 HTTPS | 瀏覽器無混合內容警告；API 與 Supabase 皆走 `https://` | 上線前設 |
| **HSTS** | 強制 HTTPS（Strict-Transport-Security） | 回傳 header 含 `Strict-Transport-Security` | 未設 |
| **CORS** | 限制允許來源 | `CORS_ORIGINS` 僅允許已知 domain，禁止 `*` | 已有 CORS |
| **API Base URL** | 前端呼叫後端用環境變數 | `VITE_API_BASE_URL` 指向正確 API | ✓ |
| **Supabase URL** | 生產用 Cloud 正式 URL | 非 `127.0.0.1`、非 localhost | 上線前設 |

**Done 條件**：生產環境全程 HTTPS；CORS 僅允許白名單；必要時加上 HSTS header（可由反向代理設定）。

---

## SEC-2：身份與資料保護 ⬜

| 項目 | 說明 | 驗證方式 | 現況 |
|------|------|----------|------|
| **密碼欄位** | 登入/註冊/重設密碼使用 `type="password"` | 檢視 LoginView、ResetPasswordView | ✓ |
| **密碼不經後端** | 登入註冊由 Supabase Auth 處理 | 後端無接收密碼的 endpoint | ✓ |
| **JWT 存放** | Token 在記憶體或 localStorage，非 cookie（可選） | 不將 token 放於易被 XSS 讀取的 cookie | ✓ |
| **URL 不含敏感資料** | Email、密碼、完整 token 不出現在 query string | 審查 router、redirect、連結 | 需檢查 |
| **重設密碼連結** | Supabase 重設連結會帶 hash 參數 | 為一次性，使用後失效；避免 log 或轉寄 | ✓ |
| **Referrer-Policy** | 避免敏感路徑外洩至第三方 | 可設 `Referrer-Policy: strict-origin-when-cross-origin` | 未設 |

**Done 條件**：密碼不經手刻 API；URL 與 redirect 不含 email/密碼/token（重設密碼 hash 除外）；必要時加上 Referrer-Policy。

---

## SEC-3：注入與攻擊防護 ⬜

| 項目 | 說明 | 驗證方式 | 現況 |
|------|------|----------|------|
| **SQL Injection** | 所有 DB 查詢使用參數化 | 使用 Supabase client、RPC 參數，無 raw SQL 串接輸入 | ✓ |
| **XSS** | 使用者輸入輸出時 escape | 避免 `v-html` 渲染未淨化內容；動態插入需 sanitize | 需審查 |
| **CSRF** | API 非 cookie session | Bearer token 在 header；表單 POST 用 JSON | ✓ |
| **輸入驗證** | 後端 Pydantic schema 驗證 | UUID、字串長度、enum 等 | ✓ |
| **IDOR** | 不可跨用戶/活動操作 | RLS + `user_id` 來自 JWT，不信任 client 傳入 | ✓ |
| **Rate limiting** | 登入、報名、核銷等限流 | `flask-limiter` 或類似；防暴力破解、濫用 | 未做 |

**Done 條件**：無 raw SQL 串接；前端無 unsafe `v-html` 渲染使用者內容；登入/報名/核銷等 endpoint 加上 rate limit。

---

## SEC-4：Secrets 與部署檢查 ⬜

| 項目 | 說明 | 驗證方式 | 現況 |
|------|------|----------|------|
| **Secrets 不進 Git** | `.env`、`.env.cloud`、`.env.local` 在 .gitignore | `git status` 無上述檔；`.env.example` 僅 placeholder | ✓ |
| **後端無 SERVICE_ROLE 外洩** | 僅 server-side 使用 | 前端 bundle、API 回傳、log 皆無 | ✓ |
| **錯誤訊息** | 500 不回傳 stack trace、SQL、路徑 | 生產環境 `FLASK_DEBUG=0`；回傳通用訊息 | 上線前確認 |
| **Log** | 不 log 密碼、完整 token、信用卡 | 審查 `current_app.logger`、第三方 log 整合 | 需審查 |
| **環境變數** | 生產用獨立 keys | 與開發/測試環境分離 | 上線前設 |

**Done 條件**：無 secret 寫入程式碼或 Git；生產錯誤訊息不洩漏內部資訊；log 不含敏感資料。

---

## SEC 建議執行順序

1. **SEC-4**（Secrets 與部署）— 先確保無外洩  
2. **SEC-3**（注入與攻擊）— 補 rate limiting，審查 XSS  
3. **SEC-2**（身份與資料）— 檢查 URL、redirect  
4. **SEC-1**（傳輸與端點）— 上線前設定 HTTPS、CORS、HSTS  

---

## SEC 檢查清單（上線前逐項勾選）

- [ ] 生產環境全程 HTTPS
- [ ] CORS 僅允許白名單 domain
- [ ] 密碼欄位為 `type="password"`，無 log
- [ ] URL 與 redirect 不含 email/密碼/完整 token
- [ ] 無 raw SQL 串接使用者輸入
- [ ] 前端無 unsafe `v-html` 渲染使用者輸入
- [ ] 登入/報名/核銷 API 有 rate limit
- [ ] `.env` 等含 key 的檔案皆在 .gitignore
- [ ] 生產 `FLASK_DEBUG=0`，錯誤不洩漏 stack/SQL
- [ ] Log 不含密碼、完整 token、信用卡號

---

# Explicit Non-Goals（禁止提前）

> **來源**：AGENTS.md。防止開發範圍蔓延，以下項目不得提前納入。

| 階段 | 不做 |
|------|------|
| **MVP-1** | 金流、退款、分潤、折扣碼、轉讓、候補、進階報表、站內通知、簡訊/LINE |
| **MVP-2** | 部分退款、複雜退票規則、折扣碼、平台分潤自動化、拒付/爭議款 |
| **MVP-3 之後** | 風控規則引擎、拒付全流程、成長工具、裝置登入管理、2FA |

**全階段禁止**（AGENTS.md Explicit Non-Goals）：

- 簡訊 / LINE Notify / 站內通知（MVP-1 不做；MVP-2 僅 Email）
- 2FA、裝置登入管理（session 列表 / 踢除）
- 候補機制、座位劃位、票券轉讓
- 報名表單「檔案上傳欄位」
- 活動複製（可選延後）
- 正式電子發票整合（第三方發票服務）
- 內容檢舉中心（完整工單流）

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

4. **上線前：Phase SEC 資安驗證**（見 [Phase SEC](#phase-sec上線前資安驗證)）  
   - SEC-4 → SEC-3 → SEC-2 → SEC-1，完成檢查清單後再對外開放  

---

# 附錄 A：Repo Layout（完整目錄結構，來自 AGENTS.md）

```
/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # app factory
│   │   ├── config.py
│   │   ├── extensions.py        # supabase client, mail, rate limit
│   │   ├── blueprints/          # auth, events, registrations, checkin, admin, orders, payments, settlements
│   │   ├── services/            # supabase_client, auth_service, events_service, registration_service, checkin_service, email_service, payment_service, settlement_service, audit_service
│   │   ├── domain/              # schemas.py, errors.py
│   │   ├── tasks/               # jobs.py
│   │   └── tests/
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                 # axios clients
│   │   ├── views/
│   │   ├── components/
│   │   ├── router/
│   │   └── stores/              # pinia
│   ├── .env.example
│   └── Dockerfile
├── infra/
│   └── docker-compose.yml
├── supabase/
│   ├── migrations/
│   └── seed.sql
└── scripts/
```

---

# 附錄 B：Domain Model（實體定義，來自 AGENTS.md）

| 實體 | 說明 |
|------|------|
| **profiles** | 使用者 metadata（link auth.users）：display_name, avatar_url, phone, social_links |
| **organizations** | 主辦方帳戶：name, owner_user_id |
| **organizer_members** | user-role 對應：org_id, user_id, role (owner/admin/staff) |
| **events** | 單一場次活動：org_id, title, start_at, end_at, status, ... |
| **ticket_types** | capacity, per_user_limit, price（MVP-1 price=0 only）|
| **tickets** | 一張票一列：ticket_id, qr_secret, status (issued/checked_in/cancelled), checked_in_at, checker_id |
| **orders** | MVP-2+ |
| **payments** | MVP-2+ |
| **settlements / payouts / ledger / audit_logs** | MVP-3+ |

---

# 附錄 C：AI 開發者協作規範（來自 AGENTS.md §12）

執行任務時：

1. **先寫短 plan**：要改哪些檔、需不需要 migration、要補哪些 tests
2. **diff 小且可跑**：每次改動可獨立驗證
3. **絕不加入 secrets**：只改 `.env.example` 放 placeholder
4. **每個 feature**：加 tests（unit + 最小 integration）、寫清楚本地如何測
5. **每個 DB 變更**：migration SQL + RLS policies、說明預期權限行為
6. **critical operations**（register/check-in/payment）：確保 atomicity + idempotency；盡量補 concurrency/race tests

---

# 附錄 D：技術速查總表（來自 ChatGPT-CypherHubCypherHub.md）

**前端路由：**

| 路徑 | 說明 |
|------|------|
| `/` | 活動列表 |
| `/events/:eventId` | 活動詳情 |
| `/login` | 登入 |
| `/tickets` | 我的票券（需登入） |
| `/organizer` | 主辦方管理 |
| `/organizer/apply` | 申請主辦方 |
| `/organizer/events` | 活動列表與建立 |
| `/organizer/forms` | Form Builder |
| `/organizer/checkin/:eventId` | 核銷 |

**後端 API（`/api/v1` 前綴）：**

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/events` | 活動列表 |
| GET | `/events/:id` | 活動詳情 |
| GET | `/events/:id/forms` | 取得報名表單 |
| POST | `/events/:id/register` | 報名（需登入） |
| GET | `/me/tickets` | 我的票券（需登入） |
| POST | `/me/tickets/:id/resend` | 重寄票券（需登入） |
| POST | `/organizer/apply` | 申請主辦方（需登入） |
| POST | `/organizer/events` | 建立活動 |
| PATCH | `/organizer/events/:id` | 編輯活動 |
| GET | `/organizer/events/:id` | 主辦方活動詳情 |
| PATCH | `/organizer/events/:id/internal-note` | 設定私密備註 |
| GET·POST | `/organizer/events/:id/forms` | 報名表單 |
| POST | `/organizer/events/:id/ticket-types` | 建立票種 |
| GET | `/organizer/events/:id/attendees` | 名單查詢 |
| POST | `/organizer/events/:id/checkin/verify` | 驗票 |
| POST | `/organizer/events/:id/checkin/commit` | 核銷 |
| GET | `/admin/events` | Admin 活動列表（allowlist） |

**DB migrations（依序）：**

- `0001_mvp1_init.sql`：profiles、organizations、events、ticket_types、tickets
- `0002_mvp1_rls.sql`：RLS policies
- `0003_mvp1_rpc.sql`：register_free、checkin RPC
- `0004`～`0005`：patch
- `0006_mvp11_event_taxonomy.sql`：dance_styles、event_types
- `0007_mvp15a_event_metadata.sql`：活動 metadata
- `0008_mvp15a_event_internal_notes.sql`：internal notes
- `0009`～`0011`：forms 表 + register_free_v2

---

# 參考文件

- [AGENTS.md](../AGENTS.md) - 專案規範、API、Supabase、防超賣
- [Tools.md](./Tools.md) - 工具選單（金流、郵件、監控、部署等）
- [ChatGPT-CypherHubCypherHub.md](../ChatGPT-CypherHubCypherHub.md) - 進度總覽
- [note.md](../note.md) - M1/M2/M3 細項
- [verification-report.md](./verification-report.md) - 功能驗證對照
