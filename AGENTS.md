# AGENTS.md

## 0) Project Summary
街舞圈售票/報名平台（Accupass-like）
核心：活動 -> 報名/購票 -> 出票 -> QR 核銷 ->（後續）結算/分潤
Tech: Supabase (Postgres/Auth/Storage/Edge Functions optional) + Flask(Python) + Vue + Docker

### MVP Roadmap (scope must be enforced)
#### MVP-1：免費報名 + QR 核銷（必做）
- User: 註冊/登入/登出、公開活動列表/詳情、免費票種報名、我的票券(顯示 QR)、Email 通知(可先純 Email)
- Organizer: 申請成主辦方(可免審核)、活動建立/編輯(單一場次)、免費票種(capacity、每人限購)、名單查詢、核銷介面(手機 Web 掃 QR、一次性核銷)
- Platform: Admin 登入、基本列表（下架活動 optional）
- System: 防超賣(原子扣名額)、票券模型(ticket + QR secret 不可猜)、權限(用戶/主辦方/核銷)、重寄票券(手動)

#### MVP-2：付費購票 + 訂單狀態機 + 退款（延後到 MVP-2 才做）
- Payment: ECPay 優先、PayPal 次要；Webhook 驗證 + 冪等
- Inventory hold + timeout 釋放名額
- 訂單狀態機：created → holding → pending_payment → paid → issued → checked_in / cancelled / refunded
- 只有 paid 才出票/啟用票券
- 背景任務：未付取消、補償出票、退款流程（先做全額或主辦方核准其中一種）

#### MVP-3：平台化（多主辦方入駐 + 分潤結算 + 提款 + 營運工具）
- Organizer member roles(owner/admin/staff) + 細權限
- Settlement & payout + ledger（強烈建議）
- Audit logs、監控告警、備份策略、進階報表/匯出

### Explicit Non-Goals (do NOT implement early)
- MVP-1 不做：金流、退款、分潤、折扣碼、轉讓、候補、進階報表
- MVP-2 不做：部分退款、多樣退票規則、折扣碼、平台分潤結算自動化
- MVP-3 之後才補：完整風控、爭議款、拒付流程、成長工具整套

---

## 1) Repo Layout (must follow)
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
        orders.py              # MVP-2+
        tickets.py
        checkin.py
        admin.py
      services/
        supabase_client.py      # wrapper (NO direct supabase calls outside)
        auth_service.py
        events_service.py
        ticket_service.py
        checkin_service.py
        email_service.py
        payment_service.py      # MVP-2+
        settlement_service.py   # MVP-3+
      domain/
        schemas.py              # pydantic models (request/response)
        errors.py
      tasks/
        __init__.py
        jobs.py                 # background jobs (MVP-1 manual trigger ok)
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
    migrations/                # SQL migrations (Supabase CLI style)
    seed.sql
  README.md

---

## 2) Local Dev Commands (Mac + Docker-first)
### 2.1 One-time
- Copy env:
  - backend/.env.example -> backend/.env
  - frontend/.env.example -> frontend/.env
- Never commit any real secrets

### 2.2 Docker compose (preferred)
- Start:
  - `docker compose -f infra/docker-compose.yml up --build`
- Stop:
  - `docker compose -f infra/docker-compose.yml down`

### 2.3 Backend (non-docker option)
- `cd backend`
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`
- `flask --app app run --debug`

### 2.4 Frontend (non-docker option)
- `cd frontend`
- `npm i`
- `npm run dev`

---

## 3) Tooling Standards (must enforce)
### Python
- Python 3.12+
- Flask app factory + Blueprints
- Pydantic for request/response validation
- ruff for lint/format

Backend commands:
- Format: `ruff format .`
- Lint: `ruff check .`
- Tests: `pytest -q`

### Vue
- Vue 3 + Vite
- Pinia store
- Router guards for auth routes

Frontend commands:
- `npm run lint` (if configured)
- `npm run test` (if configured)
- `npm run build`

### Git discipline
- Small, reviewable diffs
- Each change must include:
  - What changed
  - How to run / test locally
  - Any migration steps

---

## 4) Supabase Usage Rules (critical)
### 4.1 Keys & Security
- Frontend uses ONLY: SUPABASE_URL + SUPABASE_ANON_KEY
- Backend may use:
  - SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (server-side only)
- Service role key must NEVER go to frontend, logs, or client bundles.

### 4.2 Auth model
- Supabase Auth is the source of truth for identity.
- Frontend obtains access token (JWT).
- Backend verifies token (JWKS) OR delegates token to Supabase queries.
- Backend must derive `user_id` from token, never trust client-sent user_id.

### 4.3 RLS (Row Level Security)
- All exposed tables must have RLS enabled.
- Policies enforce:
  - User can only read their own orders/tickets/registrations.
  - Organizer can only manage events they own and see attendee list of those events.
  - Check-in permissions limited to organizer members for that event (MVP-1 can simplify: organizer owner/admin can check-in).

### 4.4 Migrations
- All schema changes go through `supabase/migrations/*.sql`
- Every PR with schema changes must include:
  - migration SQL
  - policy updates
  - rollback note if needed

---

## 5) Domain Model (high-level contract)
### Entities (minimum)
- profiles: user metadata (linked to auth.users)
- organizations: organizer accounts
- organizer_members: user-role mapping (owner/admin/staff)
- events: single session event (MVP-1)
- ticket_types: capacity, per_user_limit, price (MVP-1 price=0 only)
- orders: created/holding/pending_payment/paid/issued/cancelled/refunded (MVP-2+)
- tickets (or registrations): one row per issued ticket, unique ticket_id, qr_secret, status(issued/checked_in/cancelled)

### QR design (MVP-1 must be secure)
- QR payload includes:
  - ticket_id (uuid)
  - signature / secret proof (HMAC or random qr_secret lookup)
- Never generate guessable QR codes.
- Check-in must be one-time:
  - atomic update: if status != checked_in then set checked_in + timestamp + checker_id

---

## 6) Anti-Oversell / Atomic Capacity (MVP-1 must)
Rule: capacity decrement must be atomic and race-safe.
Implementation requirement:
- Use DB-side transaction (RPC / stored procedure) to:
  - lock ticket_type row
  - verify remaining capacity and per-user limit
  - create ticket (and order if needed)
  - decrement remaining capacity (or increment sold_count)
- No “check then insert” in application code without DB lock.

---

## 7) API Design (Backend)
- Base: `/api/v1`
- JSON only
- Standard error format:
  - `{ "error": { "code": "...", "message": "...", "details": ... } }`

### Must-have endpoints (MVP-1)
Auth:
- POST `/auth/logout` (optional; frontend can clear session)
Events (public):
- GET `/events`
- GET `/events/{event_id}`
Organizer:
- POST `/organizer/apply`
- POST `/organizer/events`
- PATCH `/organizer/events/{event_id}`
- POST `/organizer/events/{event_id}/ticket-types`
- GET `/organizer/events/{event_id}/attendees?query=...`
Tickets:
- POST `/events/{event_id}/register` (free only, calls atomic RPC)
- GET `/me/tickets`
- POST `/me/tickets/{ticket_id}/resend` (manual resend)
Check-in:
- POST `/organizer/events/{event_id}/checkin/verify` (input: qr_payload)
- POST `/organizer/events/{event_id}/checkin/commit` (idempotent)

Admin (minimal):
- POST `/admin/login` (or Supabase Auth admin role)
- GET `/admin/events`
- PATCH `/admin/events/{event_id}` (optional disable)

---

## 8) Email (MVP-1 minimal)
- Use a provider abstraction in `email_service.py`
- MVP-1 allowed:
  - synchronous send on successful registration OR
  - async job queue (preferred if available)
- Must support resend endpoint (manual trigger)

---

## 9) Background Jobs (progressive)
MVP-1:
- Optional: lightweight queue (RQ/Redis) OR synchronous with retry
MVP-2:
- Required jobs:
  - cancel expired holds
  - compensate “paid but not issued”
  - webhook retry safe handling

---

## 10) Payments (MVP-2+ rules)
- Webhook must be verified cryptographically per provider spec.
- Webhook processing must be idempotent:
  - store webhook_event_id in DB and ignore duplicates
- Only paid orders can transition to issued.
- Inventory hold timeout must release capacity safely.

---

## 11) Observability / Audit (MVP-3)
- audit_logs table for admin/organizer critical actions:
  - refund, manual issue, disable event, settlement changes
- basic metrics:
  - issuance failures, check-in failures, webhook failures

---

## 12) Coding Rules for Agents (must follow)
When working on tasks:
1) Start with a short plan (files to change, migration needs, tests to add).
2) Keep diffs small and runnable.
3) Never add secrets; only update `.env.example` with placeholder keys.
4) For any feature:
   - add tests (unit + minimal integration)
   - document how to test locally
5) For any DB change:
   - add migration SQL + RLS policies
   - explain expected permissions behavior
6) For critical operations (register/check-in/payment):
   - ensure atomicity + idempotency
   - include concurrency/race tests where feasible

Definition of Done (per PR):
- `ruff check .` and `pytest -q` pass (backend)
- frontend builds without errors
- migrations applied cleanly
- no secrets committed
- README updated if new setup steps are introduced