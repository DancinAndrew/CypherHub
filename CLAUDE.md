# CypherHub — Claude Code 開發指南

## 專案概述

**CypherHub** 是街舞活動購票平台（類似 Accupass / KKTIX，專為街舞社群設計）。

- 核心流程：主辦方建立活動 → 使用者報名/購票 → 取得 QR 票券 → 現場掃碼核銷
- **MVP-1**（免費報名 + QR 核銷）✅ 完成
- **MVP-2**（付費票 + ECPay + 訂單 + 退款）✅ 完成
- **MVP-3**（治理 + 角色 + 結算 + Audit）✅ 完成
- **SEC-1~4**（HTTPS、CORS、Secrets、Rate Limit 完善）✅ 完成

## 技術棧

| 層級 | 技術 |
|------|------|
| Backend | Flask 3.x / Python 3.12 / Pydantic v2 |
| Frontend | Vue 3 (Composition API) / Vite / TypeScript / Pinia / TailwindCSS |
| Database | Supabase（PostgreSQL + Auth + RLS + RPC + Storage） |
| Payment | ECPay 綠界（AIO, CheckMacValue SHA-256） |
| Email | Resend |
| Infra | Docker Compose / GitHub Actions CI/CD |

## 常用指令

```bash
# Backend
cd backend && ruff check .                    # Lint
cd backend && ruff format .                   # Format
cd backend && pytest -q                       # 全部測試
cd backend && pytest -q -m "not integration"  # 僅 unit tests

# Frontend
cd frontend && npm run build                  # TypeScript + Vite build
cd frontend && npm run dev                    # Dev server (port 5173)

# Docker
docker compose -f infra/docker-compose.yml up --build

# Supabase
supabase db reset                             # 本地重置（套用所有 migrations）
supabase db push                              # 推送至雲端
```

## 專案結構

```
backend/app/
├── __init__.py           # Flask factory
├── config.py             # Config class (env-based)
├── extensions.py         # rate_limiter, supabase_client, mail
├── blueprints/           # 路由層（輕薄，委派給 service）
│   ├── auth.py, events.py, registrations.py, checkin.py
│   ├── ticket_types.py, tickets.py, me.py
│   ├── orders.py, payments.py, webhooks.py
│   ├── settlements.py, admin.py, jobs.py
│   └── _utils.py        # parse_uuid, parse_json
├── services/             # 業務邏輯層
│   ├── supabase_client.py   # 唯一 Supabase 呼叫入口
│   ├── events_service.py, forms_service.py, registration_service.py
│   ├── orders_service.py, payment_service.py, refund_service.py
│   ├── settlement_service.py, checkin_service.py
│   ├── email_service.py, audit_service.py, auth_service.py
│   └── ticket_service.py
├── domain/
│   ├── schemas.py        # Pydantic request/response models
│   ├── errors.py         # AppError, map_supabase_error
│   └── order_state_machine.py
├── providers/ecpay.py    # ECPay SDK wrapper
├── tasks/jobs.py         # 背景任務
└── tests/                # pytest (30+ test files)

frontend/src/
├── api/client.ts         # Axios + 型別安全 API 呼叫（唯一後端入口）
├── api/supabase.ts       # Supabase Auth client
├── views/                # 16 頁面 + organizer/ 子目錄
├── components/           # DynamicForm.vue 等可重用元件
├── stores/               # Pinia: auth, organizer, error
├── router/index.ts       # Vue Router 4 (18 routes, meta.requiresAuth)
├── constants/taxonomy.ts # 舞風、活動類型 enum
└── utils/errorMessages.ts

supabase/migrations/      # 0001-0027.sql（MVP-1 → MVP-3）
docs/                     # setup/, development/, design/, verification/, archive/
```

## 開發規範 — Backend

### 架構分層（嚴格遵守）

- **blueprints/** → 路由層：解析參數 → 呼叫 service → `jsonify` 回傳
- **services/** → 業務邏輯層：所有 Supabase 呼叫透過 `services/supabase_client.py`
- **domain/** → Pydantic schemas + AppError
- **禁止**在 blueprints 直接呼叫 Supabase

### API 設計

- Base：`/api/v1`，JSON only，`Authorization: Bearer <JWT>`
- 錯誤格式：`{ "error": { "code", "message", "details" } }` via `AppError`
- `user_id` **禁止**信任 client 傳入，必須從 JWT 解析（`g.jwt` → `g.user_id`）
- 受保護路由使用 `@require_auth`

### Supabase 規則

- **所有表必須開 RLS**
- 存取模式：`authed_client(jwt)` / `public_client()` / service_role（僅 server-side）
- **SERVICE_ROLE_KEY** 禁止出現在 frontend、log、回傳 payload

### DB 安全（防超賣）

- 扣量必須 race-safe：`FOR UPDATE` 鎖定 → 驗證 capacity → 建 ticket → 更新 sold_count
- **禁止** app 先查 remaining 再 insert（無鎖會超賣）
- Migration 格式：`supabase/migrations/NNNN_description.sql`

### 程式碼風格

- Python 3.12+，`from __future__ import annotations`，type hints
- `ruff check .` + `ruff format .`（設定見 `pyproject.toml`）
- 輸入驗證：`parse_json(SomeRequest)`、`parse_uuid()`

### 測試

- `app/tests/test_*.py`，`conftest.py` 共用 fixtures
- 新功能：unit test + integration test
- Critical ops（register / checkin / payment）：補 concurrency test
- Mock Supabase 用 `monkeypatch`

## 開發規範 — Frontend

### 架構

- `src/api/client.ts`：唯一後端 API 入口，interceptor 自動帶 Bearer token
- `src/stores/auth.ts`：session / user / accessToken / signIn / signOut
- `src/router/`：`meta: { requiresAuth: true }` 控制登入需求

### 規則

- `<script setup lang="ts">`，TypeScript，避免 `any`
- View 命名：`XxxView.vue`；Component：`PascalCase.vue`
- TailwindCSS utility-first，支援 mobile 響應式
- `npm run build` 必須通過
- **禁止**：`SERVICE_ROLE_KEY` / `sb_secret_` 出現在前端

## 開發流程（Definition of Done）

1. **先規劃**：`/plan` 列出要改的檔案、是否需 migration、要補哪些 tests
2. **控範圍**：單次改動聚焦單一功能，禁止「順手加功能」
3. **查閱 MVP 階段**：確認功能屬於哪個 MVP，不得提前實作 Non-Goals
4. **TDD 開發**：`/tdd` 先寫測試再實作
5. **程式碼審查**：`/code-review` + `/python-review`（backend）或 `/security-scan`（安全相關）
6. **驗證通過**：
   - `cd backend && ruff check . && ruff format --check .`
   - `cd backend && pytest -q`
   - `cd frontend && npm run build`（若改 API contract）
   - migrations 可乾淨套用
7. **絕不加入 secrets**：`.env.example` 放 placeholder，禁止 commit 真實 key

## ECC 常用指令

| 指令 | 用途 |
|------|------|
| `/plan` | 規劃功能實作（生成 task list + 架構分析） |
| `/tdd` | TDD 開發流程（先寫測試） |
| `/code-review` | 程式碼品質審查 |
| `/python-review` | Python / Flask 專項審查 |
| `/security-scan` | 安全性掃描（auth / payment 必跑） |
| `/e2e` | 產生並執行 E2E 測試 |
| `/ecpay-pay` | ECPay 金流實作 |
| `/ecpay-debug` | ECPay webhook / CheckMacValue 除錯 |
| `/std-security` | 安全強化架構參考（SEC-1~4） |
| `/std-database` | Supabase / RLS / migration 設計 |

## 禁止事項

1. 提前實作 MVP Non-Goals（見 `docs/development/develop.md` Explicit Non-Goals）
2. 在 frontend 暴露 `SERVICE_ROLE_KEY`
3. 信任 client 傳入的 `user_id` 或敏感參數
4. 用「先查再 insert」做庫存扣減（必須 DB 原子操作）
5. 在 blueprints 直接呼叫 Supabase（必須透過 `services/`）
6. commit 真實 secrets（`.env`、key、token）
7. `supabase db reset --linked`（會重置遠端資料庫）

## 關鍵文件索引

| 用途 | 路徑 |
|------|------|
| 開發路線圖與完整規格 | [docs/development/develop.md](docs/development/develop.md) |
| 文件總覽 | [docs/README.md](docs/README.md) |
| ECPay 金流 Skill | [.claude/skills/ecpay/SKILL.md](.claude/skills/ecpay/SKILL.md) |
| 環境切換（本地/雲端） | [docs/setup/local-cloud-switch.md](docs/setup/local-cloud-switch.md) |
| 驗證總計畫 | [docs/verification/master-plan.md](docs/verification/master-plan.md) |
| 驗收清單 | [docs/verification/acceptance-checklist.md](docs/verification/acceptance-checklist.md) |
| 設計參考 | [docs/design/design-reference.md](docs/design/design-reference.md) |
| 工具選單 | [docs/development/Tools.md](docs/development/Tools.md) |

## ECPay 金流

- Skill 位置：`.claude/skills/ecpay/`（`git clone https://github.com/ECPay/ECPay-API-Skill.git`）
- Slash commands：`/ecpay-pay`、`/ecpay-debug`、`/ecpay-go-live`、`/ecpay-invoice`、`/ecpay-logistics`、`/ecpay-ecticket`
- 本專案 ECPay 整合：`backend/app/providers/ecpay.py`
- 本地 Webhook 測試需 ngrok：`ngrok http 8000`

## 環境變數

- `.env`：SUPABASE_URL、SUPABASE_ANON_KEY、SUPABASE_SERVICE_ROLE_KEY、CORS_ORIGINS、ECPay keys
- `.env`：VITE_API_BASE_URL、VITE_SUPABASE_URL、VITE_SUPABASE_ANON_KEY
- 範本：`.env.example`、`.env.example`
- 切換腳本：`scripts/use-local-supabase.sh`、`scripts/use-cloud-supabase.sh`
