# CypherHub - 街舞活動整合平台 (The Street Dance Event Platform)

專為街舞圈打造的活動資訊整合與售票平台（街舞版 Accupass）。

---

# CypherHub (MVP-1 Scaffold + DB + API/UI Flow)

本 repo 目前是「可啟動的開發骨架」：
- Backend：Flask app factory + API blueprints stubs + pytest/ruff
- Frontend：Vue 3 + Vite + TypeScript + TailwindCSS + Router + Pinia
- Infra：Docker Compose（backend + frontend）
- Supabase：MVP-1 schema + RLS + atomic RPC migrations

此 repo 目前已串上 MVP-1 關鍵閉環（活動列表/詳情、免費報名、我的票券 QR、主辦核銷 verify+commit）。
並已加上 MVP-1.5-A 活動 metadata 擴充（報名時間/聯絡社群/流程）與 organizer 私密備註（獨立表 + RLS）。
也已加上 MVP-1.5-B 主辦方自訂報名表單（Form Builder JSON schema）、報名 answers 存檔，以及 organizer attendees 查看 answers。

此 repo 仍**不包含** MVP-2/MVP-3（orders/payments/refunds/settlement/payout/ledger/audit_logs）。

## Quickstart (Docker-first)

### 方案 A：本地 Supabase（推薦）

1. 執行設定腳本（啟動 Supabase + 寫入 .env keys）：

```bash
./scripts/setup-local-supabase.sh
```

2. 套用 DB migrations：

```bash
supabase db reset
```

3. 啟動專案：

```bash
docker compose -f infra/docker-compose.yml up --build
```

4. 驗證：
- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/v1/health
- Supabase Studio: http://127.0.0.1:54323（建立測試用戶、檢視資料）

### 方案 B：雲端 Supabase

1. 複製環境變數範本並填入雲端專案的 URL 與 keys：

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# 編輯 .env 填入 SUPABASE_URL、SUPABASE_ANON_KEY、SUPABASE_SERVICE_ROLE_KEY、VITE_SUPABASE_* 
```

2. 啟動：

```bash
docker compose -f infra/docker-compose.yml up --build
```

3. 驗證：
- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/v1/health

## Thread 3 MVP-1 驗收流程（Docker + UI + API）

### 0) 驗收前置（env）

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`backend/.env` 至少填：
- `SUPABASE_URL=...`
- `SUPABASE_ANON_KEY=...`
- `CORS_ORIGINS=http://localhost:5173`
- `ADMIN_ALLOWLIST=...`（可選）

`frontend/.env` 至少填：
- `VITE_API_BASE_URL=http://localhost:8000`
- `VITE_SUPABASE_URL=...`
- `VITE_SUPABASE_ANON_KEY=...`

安全要求：
- 前端禁止使用 `sb_secret` / `service_role`
- 不要提交 `.env`

### 1) 啟動服務（Docker）

```bash
docker compose -f infra/docker-compose.yml up --build
```

另開 terminal 驗 health：

```bash
curl -s http://localhost:8000/api/v1/health
```

預期至少包含：

```json
{"status":"ok"}
```

前端網址：`http://localhost:5173`

### 2) 若 events 為空，先建測試資料

若 `GET /api/v1/events` 回 `{"items":[]}`，請在前端用 Organizer 頁（目前路由是 `/organizer`）建立：
1. Apply organizer
2. Create event（`status=published`，`start_at/end_at` 為未來時間）
3. Create ticket type（免費，`capacity > 0`，`per_user_limit >= 1`）

建立後回首頁確認活動可見。

### 3) UI 閉環驗收（必做）

1. Guest：首頁看到 published 活動，點進活動詳情可見票種
2. User：到 `/login` 登入後，回活動詳情按 `Register (Free)`
3. My Tickets：到 `/tickets` 可見票券與 QR
4. QR payload 格式（JSON 字串）：
   - `{"ticket_id":"...","qr_secret":"..."}`
5. Organizer check-in：到 `/organizer/checkin/{event_id}` 輸入 `ticket_id + qr_secret`
6. Verify 預期：`valid=true`、`can_checkin=true`、`status=issued`
7. Commit 第一次預期：`ok=true`、`already_checked_in=false`
8. Commit 第二次預期：`ok=true`、`already_checked_in=true`（idempotent）

### 3.1 Thread 4 掃碼核銷（手機）

1. 到 `/organizer/checkin/{event_id}`（需登入 organizer member）
2. 切到「掃碼模式」並點 `Start Scan`
3. 允許相機權限，將 `/tickets` 頁上的 QR 對準鏡頭
4. 掃到後預期：
   - 自動停止掃描
   - 自動填入 `ticket_id` / `qr_secret`
   - 自動執行 Verify
5. 按 `Commit Check-in`
   - 第一次：`ok=true`, `already_checked_in=false`
   - 第二次：`ok=true`, `already_checked_in=true`

QR payload 支援格式：
- JSON：`{"ticket_id":"...","qr_secret":"..."}`
- querystring（可選）：`ticket_id=...&qr_secret=...`
- pipe（可選）：`<ticket_id>|<qr_secret>`

若相機權限被拒：
- 會顯示提示，改用手動輸入模式完成核銷。
- `/tickets` 提供 `Copy Payload` 按鈕，可快速貼到核銷頁。

### 3.2 Thread 6 MVP-1.5-A（活動資訊完善 + 私密備註）

1. Organizer 到 `/organizer` 建立或載入活動（`Load Event`）。
2. 在 Create/Update 區塊填寫：
   - `registration_start_at` / `registration_end_at`
   - `map_url`
   - `contact_email` / `contact_phone`
   - `socials`（IG/FB/YouTube/LINE/Website）
   - `eligibility` / `event_language`
   - `checkin_open_at` / `checkin_note`
   - `schedule`（JSON array）
3. 在 `Internal Note` 欄位填寫主辦方私密備註並送出。
4. Guest 打開活動詳情頁（`/events/{event_id}`）：
   - 應看到上述公開欄位（報名時間、聯絡、社群、流程等）。
   - 不會看到 `internal_note`。
5. Organizer 使用 `GET /api/v1/organizer/events/{event_id}` 讀取編輯資料時可看到 `internal_note`。

#### Thread 6 手動驗收步驟

1. 套用 migrations：
   - `supabase db push --dry-run`
   - `supabase db push`
2. 啟動服務：`docker compose -f infra/docker-compose.yml up --build`
3. Organizer 登入後在 `/organizer` 建立活動，填入報名時間、聯絡、社群、流程與 internal note。
4. Guest 開啟同活動 `/events/{event_id}`，確認公開 metadata 都可見。
5. Organizer 再次進 `/organizer` 載入該活動，確認可以讀寫 internal note。
6. Guest 再次查看活動頁，確認不會出現 internal note。

### 3.3 Thread 7 MVP-1.5-B（報名表單 / Form Builder）

1. Organizer 到 `/organizer`，在 `Form Builder (JSON Schema)` 區塊設定：
   - `event_id`
   - `ticket_type_id`（可留空，代表 event-level form）
   - 表單 JSON schema
2. 儲存後，User 到活動詳情頁選票種。
3. 前端會呼叫 `GET /api/v1/events/{event_id}/forms?ticket_type_id=...` 並動態渲染欄位。
4. User 填完必填欄位後送出報名。
5. 報名成功後，票券會正常出現在 `/tickets`。
6. Organizer 回 `/organizer` 的 `Attendees List` 載入同 event，可看到 `answers` JSON。

#### 表單 schema 範例

```json
{
  "version": 1,
  "fields": [
    {
      "key": "full_name",
      "label": "姓名",
      "type": "text",
      "required": true,
      "placeholder": "請輸入姓名",
      "help_text": "請填寫真實姓名",
      "options": []
    },
    {
      "key": "phone",
      "label": "聯絡電話",
      "type": "phone",
      "required": true,
      "placeholder": "0900-000-000",
      "help_text": "活動聯絡使用",
      "options": []
    },
    {
      "key": "agree_media",
      "label": "同意活動影像紀錄",
      "type": "checkbox",
      "required": true,
      "placeholder": "我同意主辦方於活動現場拍攝與使用活動紀錄",
      "help_text": "必填同意條款",
      "options": []
    }
  ]
}
```

### 4) API / 權限驗收（必做）

未帶 token 呼叫受保護 API：

```bash
curl -i http://localhost:8000/api/v1/me/tickets
```

預期：
- HTTP `401`
- body 為標準錯誤格式：

```json
{"error":{"code":"...","message":"...","details":...}}
```

帶 token 讀我的票券（`<ACCESS_TOKEN>` 由前端登入後取得）：

```bash
curl -s -H "Authorization: Bearer <ACCESS_TOKEN>" \
  http://localhost:8000/api/v1/me/tickets
```

預期：HTTP `200`，且只回該 user 的 tickets（RLS 生效）。

錯誤情境至少測 1 個：
- `per_user_limit=1` 時同 user 第二次 register 應失敗（400/409）
- 或 capacity 滿時應 `SOLD_OUT`

活動篩選（MVP-1.1）：

```bash
curl -s "http://localhost:8000/api/v1/events?styles=hiphop,popping&types=cypher,battle"
```

語意：
- `styles`：`dance_styles` 任一重疊（overlap）即符合
- `types`：`event_types` 任一重疊（overlap）即符合

### 5) 測試/建置指令（必做）

```bash
docker compose -f infra/docker-compose.yml run --rm backend ruff check .
docker compose -f infra/docker-compose.yml run --rm backend pytest -q
docker compose -f infra/docker-compose.yml run --rm frontend sh -lc "npm install && npm run build"
```

### 6) 範圍與安全檢查（必做）

```bash
git status
git grep -n "sb_secret_" .
git grep -n "SUPABASE_ACCESS_TOKEN" .
```

預期：
- 無新增 MVP-2/3 功能（orders/payments/refunds/settlements/ledger/audit_logs）
- repo 不含真實 key/token（僅 `.env.example` placeholder）

## Non-Docker Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Lint / Test

### Backend

```bash
cd backend
ruff format .
ruff check .
pytest -q
```

若本機 Python 不是 3.12，建議直接用 Docker 跑：

```bash
docker compose -f infra/docker-compose.yml run --rm backend ruff check .
docker compose -f infra/docker-compose.yml run --rm backend pytest -q
```

### Frontend

```bash
cd frontend
npm run dev
npm run build
```

Docker build 驗證：

```bash
docker compose -f infra/docker-compose.yml run --rm frontend sh -lc "npm install && npm run build"
```

API smoke test：

```bash
curl -sS http://localhost:8000/api/v1/health
curl -sS http://localhost:8000/api/v1/events
curl -sS http://localhost:8000/api/v1/me/tickets
```

## Environment Variables

請只使用範本檔案並填入你自己的本機值：
- backend: `backend/.env.example`
- frontend: `frontend/.env.example`

注意：請勿提交任何真實 secrets。repo 僅保留 `.env.example` placeholder。

## Supabase Migrations (MVP-1)

Migrations:
- `supabase/migrations/0001_mvp1_init.sql`
- `supabase/migrations/0002_mvp1_rls.sql`
- `supabase/migrations/0003_mvp1_rpc.sql`
- `supabase/migrations/0004_mvp1_patch_drift.sql`
- `supabase/migrations/0005_mvp1_patch_register_pgcrypto_search_path.sql`
- `supabase/migrations/0006_mvp11_event_taxonomy.sql`
- `supabase/migrations/0007_mvp15a_event_metadata.sql`
- `supabase/migrations/0008_mvp15a_event_internal_notes.sql`
- `supabase/migrations/0009_mvp15b_forms_tables.sql`
- `supabase/migrations/0010_mvp15b_forms_rls.sql`
- `supabase/migrations/0011_mvp15b_register_free_v2_rpc.sql`

### 套用方式（local Supabase）

```bash
supabase start
supabase db reset
```

`supabase db reset` 會依序套用 migration（0001 -> 0002 -> 0003 -> 0004 -> 0005 -> 0006 -> 0007 -> 0008 -> 0009 -> 0010 -> 0011）與 `supabase/seed.sql`。

### DB migrations（cloud）

先確認已安裝 CLI（或使用 `npx --yes supabase`）：

```bash
supabase login
supabase link --project-ref mcqpgnavygeuylisjllr
supabase db push --dry-run
supabase db push
supabase migration list
```

安全提醒：
- 不要使用 `supabase db reset --linked`（會重置遠端資料庫）。
- `SUPABASE_ACCESS_TOKEN` 只用本機環境變數，不要寫入檔案、不要 commit 到 repo。

### 套用方式（Supabase SQL Editor）

請依序貼上執行：
1. `0001_mvp1_init.sql`
2. `0002_mvp1_rls.sql`
3. `0003_mvp1_rpc.sql`
4. `0004_mvp1_patch_drift.sql`
5. `0005_mvp1_patch_register_pgcrypto_search_path.sql`
6. `0006_mvp11_event_taxonomy.sql`
7. `0007_mvp15a_event_metadata.sql`
8. `0008_mvp15a_event_internal_notes.sql`
9. `0009_mvp15b_forms_tables.sql`
10. `0010_mvp15b_forms_rls.sql`
11. `0011_mvp15b_register_free_v2_rpc.sql`

順序不可顛倒（RLS 依賴 tables；RPC 依賴 tables 與 helper functions）。  
若 CLI 登入/token 卡住，SQL Editor 是官方可行 fallback。

### Thread 6 migrations（cloud）

```bash
supabase db push --dry-run
supabase db push
```

預期 dry-run 摘要：
- `ALTER TABLE public.events` 新增 metadata 欄位
- `CREATE TABLE public.event_internal_notes`
- `ENABLE ROW LEVEL SECURITY` + policies（`event_internal_notes_*`）

### Thread 7 migrations（cloud）

```bash
supabase db push --dry-run
supabase db push
```

預期 dry-run 摘要：
- `CREATE TABLE public.event_forms`
- `CREATE TABLE public.ticket_form_responses`
- `ENABLE ROW LEVEL SECURITY` + `event_forms_*` / `ticket_form_responses_*`
- `CREATE FUNCTION public.register_free_v2(...)`

### Drift check（cloud）

```bash
supabase migration list
supabase db diff --linked > supabase/drift_check.sql
```

若 `supabase/drift_check.sql` 非空，表示 linked cloud 與 migrations 有差異，需新增 migration 修正後再 `supabase db push`。

## MVP-1 DB 驗證

Cloud SQL Editor 驗證步驟：
1. 到 Supabase Dashboard -> Authentication -> Users，建立兩個測試使用者。
   - `OWNER_UUID`：主辦方 owner
   - `ATTENDEE_UUID`：報名者
2. 打開 `supabase/verify_mvp1.sql`，只替換兩個 UUID 變數值。
3. 在 SQL Editor 直接整份執行（單檔一鍵跑）。
4. 預期輸出（NOTICE）至少包含：
   - `register_free success`
   - `first commit result` 與 `second commit result`（第二次 `already_checked_in=true`）
   - `per_user_limit test pass`（成功擋下第二次報名）

## DB 權限行為（MVP-1）

- 公開：`events`（published）、`event_media`（published event）、`ticket_types`（active + published）
- 使用者：只能讀自己 `tickets` / `profiles`
- 主辦成員：可讀自己 org/event 相關資料與 attendee tickets
- `tickets` 不開放 client 直接 `INSERT/UPDATE`，只能透過 RPC

## Rollback 備註

- Local 開發：使用 `supabase db reset` 回到 migration 定義狀態。
- Shared/production 環境：以「新 migration forward 修正」為主，不建議手動回滾已執行 migration。

## Known Limitations (MVP-1)

- Organizer check-in 已支援相機掃碼，但需瀏覽器提供相機權限；部分裝置/瀏覽器在非 `localhost` 的 `http` 會限制相機。
- `POST /api/v1/me/tickets/{ticket_id}/resend` 目前為 email service stub（log），未串第三方郵件供應商。
- Admin endpoint 目前只保留最小 allowlist 讀取能力，管理功能維持 MVP-1 最小化。
