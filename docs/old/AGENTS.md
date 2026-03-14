# AGENTS.md

## 0) 專案摘要（Project Summary）
街舞圈售票/報名平台（Accupass-like）  
核心流程：活動 → 報名/購票 → 出票 → QR 核銷 →（後續）結算/分潤  
Tech：Supabase（Postgres/Auth/Storage；Edge Functions optional）+ Flask（Python）+ Vue + Docker

### MVP Roadmap（務必嚴格控範圍）
> 原則：先跑通閉環，再做金流，再做平台化（結算/提款/治理）。  
> 禁止「順手加功能」導致 MVP 膨脹。

#### MVP-1：免費報名 + QR 核銷（必做）
- User：
  - 註冊/登入/登出（Supabase Auth）
  - 公開活動列表/詳情（單一場次）
  - 免費票種報名（capacity、每人限購）
  - 我的票券（顯示 QR）
  - Email 通知（純 Email 即可）
- Organizer：
  - 申請成主辦方（可免審核）
  - 活動建立/編輯（單一場次）
  - 免費票種管理（capacity、限購、販售時間）
  - 名單查詢
  - 核銷介面（手機 Web 掃 QR、一次性核銷）
- Platform：
  - Admin 登入
  - 基本列表（下架活動 optional）
- System：
  - 防超賣（DB 原子扣名額）
  - 票券模型（ticket + qr_secret 不可猜）
  - 權限（用戶/主辦方/核銷）
  - 重寄票券（手動）

#### MVP-2：付費購票 + 訂單狀態機 +（基礎）退款（延後到 MVP-2 才做）
- Payment：
  - ECPay 優先、PayPal 次要（可同 MVP-2 或拆成 2.5）
  - Webhook 驗證 + 冪等（重送不重複出票/記帳）
- Inventory：
  - hold + timeout 釋放名額
- 訂單狀態機：
  - created → holding → pending_payment → paid → issued → checked_in / cancelled / refunded
  - 僅 paid 才出票/啟用票券
- 背景任務（必需）：
  - 未付逾時取消 + 釋放
  - paid 但未 issued 補償
  - webhook retry safe handling
- 退款（先簡化）：
  - 全額退款 或「主辦方核准」其中一種（不要一開始就做部分退款/複雜規則）

#### MVP-3：平台化（多主辦方入駐 + 分潤結算 + 提款 + 營運工具）
- Organizer member roles（owner/admin/staff）+ 細權限（可管理/可核銷範圍）
- Settlement & payout + ledger（強烈建議，否則退款/調帳會亂）
- Audit logs、監控告警、備份策略
- 進階報表/匯出、治理工具

### Explicit Non-Goals（禁止提前）
- MVP-1 不做：金流、退款、分潤、折扣碼、轉讓、候補、進階報表、站內通知、簡訊/LINE
- MVP-2 不做：部分退款、多樣退票規則、折扣碼、平台分潤結算自動化、拒付/爭議款
- MVP-3 之後才補：完整風控規則引擎、拒付/爭議款全流程、成長工具整套、裝置登入管理、2FA

---

## 1) Repo Layout（必須遵守）
/
  backend/
    app/
      __init__.py              # app factory
      config.py
      extensions.py            # supabase client, mail, rate limit, etc.
      blueprints/
        auth.py
        events.py
        ticket_types.py
        tickets.py
        registrations.py        # MVP-1: free register endpoint
        checkin.py
        admin.py
        orders.py               # MVP-2+
        payments.py             # MVP-2+
        settlements.py          # MVP-3+
      services/
        supabase_client.py      # wrapper（禁止在 service 以外直接 call supabase）
        auth_service.py
        events_service.py
        ticket_service.py
        registration_service.py
        checkin_service.py
        email_service.py
        payment_service.py      # MVP-2+
        settlement_service.py   # MVP-3+
        audit_service.py        # MVP-3+
      domain/
        schemas.py              # pydantic models（request/response）
        errors.py               # domain errors + mapping to http
      tasks/
        __init__.py
        jobs.py                 # background jobs（MVP-1 可先手動觸發）
      tests/
    requirements.txt
    pyproject.toml              # ruff/pytest config
    .env.example
    Dockerfile
  frontend/
    src/
      api/                      # axios clients
      views/
      components/
      router/
      stores/                   # pinia
    .env.example
    Dockerfile
  infra/
    docker-compose.yml
  supabase/
    migrations/                # SQL migrations（Supabase CLI style）
    seed.sql
  README.md

---

## 2) Local Dev（Mac + Docker-first）
### 2.1 One-time
- Copy env（不要提交真實 secrets）：
  - backend/.env.example → backend/.env
  - frontend/.env.example → frontend/.env

### 2.2 Docker compose（preferred）
- Start：
  - `docker compose -f infra/docker-compose.yml up --build`
- Stop：
  - `docker compose -f infra/docker-compose.yml down`

### 2.3 Backend（non-docker option）
- `cd backend`
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`
- `flask --app app run --debug`

### 2.4 Frontend（non-docker option）
- `cd frontend`
- `npm i`
- `npm run dev`

---

## 3) Tooling Standards（必須強制）
### Python
- Python 3.12+
- Flask app factory + Blueprints
- Pydantic 驗證 request/response
- ruff lint/format
- pytest

Backend commands：
- Format：`ruff format .`
- Lint：`ruff check .`
- Tests：`pytest -q`

### Vue
- Vue 3 + Vite
- Pinia store
- Router guards（需要登入的頁面）

### Git discipline
- 小步可 review 的 diff
- 每次改動必包含：
  - 改了什麼
  - 如何本地跑/測
  - 若有 migration：如何套用/回滾說明（至少文字備註）

---

## 4) Supabase 使用規則（Critical）
### 4.1 Keys & Security
- Frontend 只用：
  - SUPABASE_URL
  - SUPABASE_ANON_KEY
- Backend 可用：
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY（僅 server-side）
- Service role key **禁止**出現在：frontend、log、client bundle、任何回傳 payload。

### 4.2 Auth model（身份真實來源）
- Supabase Auth 是 identity source of truth
- Frontend 取得 access token（JWT）
- Backend 必須：
  - 驗 JWT（JWKS）**或**
  - 將 JWT 帶入 Supabase 查詢並由 RLS 限制
- Backend 取得 `user_id` 必須從 token 解析，**禁止信任 client 傳入 user_id**

### 4.3 RLS（Row Level Security）
- 所有可被 API/前端存取的表必須開 RLS
- Policies 最小要求：
  - User：只能讀自己的 tickets/registrations（MVP-1）；MVP-2 起加 orders/payments
  - Organizer：只能管理自己 organization 的 events/ticket_types，且只能看自己活動 attendee list
  - Check-in：只有 organizer member（owner/admin/staff）可核銷該 event
  - MVP-1 可簡化：owner/staff 皆可核銷（不細分 admin）

### 4.4 Migrations（唯一合法改 schema 的方式）
- 所有 schema/policy 變更必須進 `supabase/migrations/*.sql`
- 每個 PR 若有 DB 變更，必須包含：
  - migration SQL
  - policy 更新
  - 權限行為說明（誰能讀/寫什麼）
  - 若需要：回滾備註（文字即可）

---

## 5) Domain Model（High-level Contract）
### Entities（minimum）
- profiles：使用者 metadata（link 到 auth.users）
- organizations：主辦方帳戶（organizer）
- organizer_members：user-role mapping（owner/admin/staff）
- events：單一場次活動（MVP-1）
- ticket_types：capacity、per_user_limit、price（MVP-1 price=0 only）
- tickets（or registrations）：一張票一列（issued/checked_in/cancelled）
  - ticket_id（uuid）
  - qr_secret（random，不可猜）
  - status
  - checked_in_at、checker_id
- orders（MVP-2+）
- payments（MVP-2+）
- settlements / payouts / ledger / audit_logs（MVP-3+）

### QR 設計（MVP-1 必須安全）
- QR payload 必含：
  - ticket_id（uuid）
  - proof（以下二擇一）
    - random qr_secret（查表比對）
    - 或 HMAC(ticket_id, server_secret)
- 禁止可猜 QR（例如自增 id、短碼無簽名）
- 核銷必須 one-time 且原子：
  - atomic update：若 status != checked_in 才能設為 checked_in + timestamp + checker_id

---

## 6) 防超賣 / 原子扣名額（MVP-1 必做）
規則：扣量必須 race-safe（DB 層保證）。  
禁止做法：app code 先查 remaining 再 insert（沒有鎖會超賣）。

Implementation requirement：
- 使用 DB-side transaction（建議 RPC / stored procedure）：
  1) lock ticket_type row（FOR UPDATE）
  2) 驗證 remaining/capacity 與 per-user limit（同一 user 對同 ticket_type 的已持有數量）
  3) 建 ticket（MVP-1 可不建立 order）
  4) 更新 sold_count / remaining_count（擇一，必須同交易）
- 回傳：ticket_id + qr payload（或只回 ticket_id，qr 由前端組裝但 proof 必安全）

---

## 7) API 設計（Backend）
- Base：`/api/v1`
- JSON only
- Auth：使用 `Authorization: Bearer <SUPABASE_ACCESS_TOKEN>`
- Standard error format：
  - `{ "error": { "code": "...", "message": "...", "details": ... } }`

### MVP-1 Must-have endpoints
Auth：
- POST `/auth/logout`（optional；前端清 session 即可）

Events（public）：
- GET `/events`
- GET `/events/{event_id}`

Organizer：
- POST `/organizer/apply`
- POST `/organizer/events`
- PATCH `/organizer/events/{event_id}`
- POST `/organizer/events/{event_id}/ticket-types`
- GET `/organizer/events/{event_id}/attendees?query=...`

Registration / Tickets：
- POST `/events/{event_id}/register`（free only；呼叫 atomic RPC）
- GET `/me/tickets`
- POST `/me/tickets/{ticket_id}/resend`（手動重寄 email）

Check-in：
- POST `/organizer/events/{event_id}/checkin/verify`（input：qr_payload；回傳可否核銷與票券摘要）
- POST `/organizer/events/{event_id}/checkin/commit`（idempotent；原子更新票券狀態）

Admin（minimal）：
- GET `/admin/events`
- PATCH `/admin/events/{event_id}`（optional：disable/down）

### MVP-2+ 追加（不得提前）
- Orders：`/orders/*`
- Payments：`/payments/*` + provider webhooks
- Refund：`/refunds/*`（先全退或核准制）

---

## 8) Email（MVP-1 minimal）
- `email_service.py` 必須做 provider abstraction（可先 stub/local）
- MVP-1 可接受：
  - 報名成功同步寄信（最簡）或
  - background job（較佳）
- 必須支援 resend endpoint（手動觸發）
- Email 內容最小：活動名、時間地點、票券 QR（或 link）

---

## 9) Background Jobs（Progressive）
MVP-1：
- 可選：輕量 queue（RQ/Redis）或同步 + retry（可接受）
MVP-2：
- 必做 jobs：
  - cancel expired holds
  - compensate “paid but not issued”
  - webhook retry safe handling
MVP-3：
- settlement batch、reminder、audit/metrics aggregation 等

---

## 10) Payments（MVP-2+ rules）
- Webhook 必須按 provider 規格做加密/簽章驗證（不可只信任 payload）
- Webhook 處理必須冪等：
  - 存 webhook_event_id 並忽略重複
- 僅 paid 可轉 issued
- hold timeout 必須安全釋放名額

---

## 11) Observability / Audit（MVP-3）
- audit_logs table：記錄 admin/organizer 的 critical actions
  - refund、manual issue、disable event、settlement changes、payout actions
- metrics（最小）：
  - issuance failures、check-in failures、webhook failures

---

## 12) Coding Rules for Agents（必須遵守）
When working on tasks：
1) 先寫短 plan（要改哪些檔、需不需要 migration、要補哪些 tests）
2) diff 小且可跑
3) 絕不加入 secrets；只改 `.env.example` 放 placeholder
4) 每個 feature：
   - 加 tests（unit + 最小 integration）
   - 寫清楚本地如何測
5) 每個 DB 變更：
   - migration SQL + RLS policies
   - 說明預期權限行為
6) 對 critical operations（register/check-in/payment）：
   - 確保 atomicity + idempotency
   - 能做就補 concurrency/race tests（threads/processes）

Definition of Done（per PR）：
- `ruff check .` 與 `pytest -q` pass（backend）
- frontend build 無錯
- migrations 可乾淨套用
- 無 secrets
- README 若新增 setup 步驟必更新