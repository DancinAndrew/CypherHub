# CypherHub Backend 開發規範

> 適用範圍：`backend/`（Flask / Supabase / migrations / pytest）  
> 參考：AGENTS.md、docs/develop.md

---

## 0. 開發流程（嚴格遵守）

### 執行前必做

1. **先寫短 plan**：列出要改的檔案、是否需要 migration、要補哪些 tests
2. **控範圍**：單次改動聚焦單一功能，禁止「順手加功能」導致 MVP 膨脹
3. **查閱 develop.md**：確認該功能屬於哪個 MVP 階段，不得提前實作 Non-Goals

### PR / 改動標準

- **diff 小且可跑**：每次改動可獨立 `ruff check .`、`pytest -q` 驗證
- **絕不加入 secrets**：僅修改 `.env.example` 放 placeholder，禁止 commit 真實 key
- **DB 變更**：必須包含 migration SQL、RLS policies、預期權限說明、回滾備註（文字即可）
- **Critical operations**（register/check-in/payment）：確保 atomicity + idempotency；盡量補 concurrency/race tests

### Definition of Done（每 PR）

- `ruff check .` 與 `ruff format .` 通過
- `pytest -q` 通過
- frontend build 無錯（若改 API contract）
- migrations 可乾淨套用
- README 若新增 setup 步驟必須更新

---

## 1. 專案結構（必須遵守）

```
backend/
├── app/
│   ├── __init__.py          # app factory
│   ├── config.py            # Config class, os.getenv
│   ├── extensions.py        # supabase_client, mail, rate_limiter
│   ├── blueprints/          # 路由層，輕薄，委派給 service
│   │   ├── _utils.py        # parse_uuid, parse_json
│   │   ├── auth.py
│   │   ├── events.py
│   │   ├── registrations.py
│   │   ├── checkin.py
│   │   ├── admin.py
│   │   └── ...
│   ├── services/            # 業務邏輯層
│   │   ├── supabase_client.py   # 唯一 Supabase 呼叫入口
│   │   ├── auth_service.py
│   │   ├── events_service.py
│   │   └── ...
│   ├── domain/
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── errors.py        # AppError, map_supabase_error
│   ├── tasks/
│   │   └── jobs.py          # 背景任務
│   └── tests/
├── requirements.txt
├── pyproject.toml           # ruff, pytest config
└── .env.example
```

- **禁止**在 blueprints 以外直接呼叫 Supabase；一律透過 `services/supabase_client.py` 或各 service
- **禁止**在 service 以外直接 `from supabase import ...`

---

## 2. API 設計

### 路由與格式

- **Base**：`/api/v1`
- **JSON only**：Content-Type: application/json
- **Auth**：`Authorization: Bearer <SUPABASE_ACCESS_TOKEN>`
- **Blueprint 註冊**：`url_prefix="/api/v1/..."` 或 `"/api/v1/organizer/..."`

### 錯誤回應（統一格式）

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

- 使用 `AppError` 與 `handle_app_error`；HTTP status 由 `AppError.http_status` 決定
- 4xx：VALIDATION_ERROR、AUTH_REQUIRED、TICKET_TYPE_NOT_FOUND、PER_USER_LIMIT_EXCEEDED、SOLD_OUT 等
- 5xx：僅用 INTERNAL_SERVER_ERROR，不暴露內部細節

### 身分驗證

- `user_id` **禁止**信任 client 傳入；必須從 JWT 解析（`g.jwt` → `supabase_client.get_user(jwt)`）
- 受保護路由使用 `@require_auth`，`g.jwt`、`g.user_id` 由 middleware 注入
- Supabase Auth 為 identity source of truth；Backend 驗 JWT（JWKS）或帶入 Supabase 查詢由 RLS 限制

---

## 3. Supabase 使用規則

### Keys & Security

- **Frontend**：僅 SUPABASE_URL、SUPABASE_ANON_KEY
- **Backend**：SUPABASE_URL、SUPABASE_ANON_KEY、SUPABASE_SERVICE_ROLE_KEY
- **SUPABASE_SERVICE_ROLE_KEY** 禁止出現在：frontend、log、client bundle、任何回傳 payload

### 存取模式

- 一般查詢：`supabase_client.authed_client(jwt)` 或 `public_client()`，由 RLS 限制
- Admin 操作（如建立用戶）：使用 service_role，僅在 server-side、不暴露給 client

### RLS（Row Level Security）

- 所有可被 API 存取的表必須開 RLS
- User：只能讀自己的 tickets、profiles
- Organizer：只能管理自己 org 的 events、ticket_types，只看自己活動的 attendee list
- Check-in：僅 organizer member（owner/admin/staff）可核銷該 event

---

## 4. Migrations

### 規範

- 所有 schema/policy 變更 **必須** 進 `supabase/migrations/*.sql`
- 檔名格式：`NNNN_description.sql`（例：`0012_add_orders_table.sql`）
- 每個 PR 若有 DB 變更，必須包含：migration SQL、RLS 更新、權限行為說明

### 套用方式

- **本地**：`supabase db reset`
- **雲端**：`./scripts/push-to-cloud.sh` 或 `supabase db push`
- **禁止** `supabase db reset --linked`（會重置遠端資料庫）

### 防超賣（必遵守）

- 扣量必須 race-safe，使用 DB-side transaction（RPC / stored procedure）
- 流程：`FOR UPDATE` 鎖定 ticket_type → 驗證 capacity、per_user_limit → 建 ticket → 更新 sold_count
- **禁止**：app 先查 remaining 再 insert（無鎖會超賣）

---

## 5. 程式碼風格

### Python 與工具

- **Python 3.12+**
- **Formatter**：`ruff format .`
- **Linter**：`ruff check .`（pyproject.toml 已設定 target-version、line-length、select rules）
- **型別**：使用 type hints；`from __future__ import annotations`

### Blueprint 撰寫

- 路由函式保持輕薄：解析參數 → 呼叫 service → 回傳 jsonify
- 使用 `parse_uuid`、`parse_json` 做輸入驗證；驗證失敗拋 `AppError`
- Pydantic schema 定義於 `domain/schemas.py`，request 用 `parse_json(SomeRequest)`

### Service 撰寫

- 業務邏輯放 service；不直接 import blueprint
- 透過 `supabase_client` 呼叫 Supabase；錯誤用 `map_supabase_error` 轉 `AppError`
- RPC 呼叫：`supabase_client.call_rpc("function_name", params, jwt=jwt)`

---

## 6. 測試

### 結構

- 測試置於 `app/tests/`
- `conftest.py`：共用 fixtures（client、mock supabase 等）
- 檔名：`test_*.py`，函式：`test_*`

### 覆蓋要求

- 每個 **新 feature**：unit test + 最小 integration test
- **Critical operations**（register、check-in、payment）：盡量補 concurrency/race tests
- Mock Supabase：使用 `monkeypatch` 或 pytest fixtures 替換 `supabase_client`

### 執行

```bash
cd backend
pytest -q
# 或
docker compose -f infra/docker-compose.yml run --rm backend pytest -q
```

---

## 7. 環境變數

- 從 `backend/.env` 讀取（不 commit）
- 範本：`backend/.env.example`，僅放 placeholder
- 必填：SUPABASE_URL、SUPABASE_ANON_KEY；MVP-2+ 需 SUPABASE_SERVICE_ROLE_KEY

---

## 8. 禁止事項

- 提前實作 MVP Non-Goals（見 develop.md Explicit Non-Goals）
- 在 frontend 或 client 暴露 service_role key
- 信任 client 傳入的 `user_id` 或敏感參數
- 在 app code 用「先查再 insert」做庫存扣減（必須 DB 原子操作）
