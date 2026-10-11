<div align="center">
  <img src="Logo/Logo.png" alt="CypherHub Logo" width="600"/>
</div>

# CypherHub

## English Summary

CypherHub is a ticketing and registration web app for street-dance events such as cyphers, battles, workshops, showcases and jams. Dancers find events by dance style and event type, register or pay, and receive a QR e-ticket; organizers create events, sell free or paid tickets, and check attendees in at the door. It aims to replace the Google Forms plus LINE group chats that organizers otherwise piece together.

**Key features**
- Event filtering by dance style (Hip-hop, Popping, Locking, Breaking, Waacking and more) and event type, plus registration forms that organizers build themselves, optionally one per ticket type.
- Paid tickets through ECPay, a Taiwanese payment gateway, via its hosted checkout (the README lists card, ATM transfer and convenience-store code). Requests and webhooks carry ECPay's SHA-256 CheckMacValue, which the backend computes and verifies; duplicate webhooks are handled idempotently and orders follow an explicit state machine. Platform admins can issue full refunds through ECPay's API for credit-card payments only.
- To avoid overselling, PostgreSQL functions lock the ticket-type row (`SELECT ... FOR UPDATE`) before reserving or issuing tickets. An integration test sends two concurrent holds for the last ticket; it skips itself unless a Supabase project is configured.
- QR e-tickets. Check-in by phone-camera scan or manual entry of the ticket ID and secret; a repeat check-in returns "already checked in" instead of an error.
- Organizer teams with owner, admin and staff roles, optional platform approval of new organizers (off by default), settlements with a platform fee (5% by default), payout requests, and audit logs.
- PostgreSQL row-level security (RLS), JWT auth through Supabase Auth, per-route rate limits and security headers. In production mode the backend refuses to start with CORS `*`, a non-HTTPS Supabase URL or missing secrets.

**Tech stack:** Python 3.12, Flask 3.1, Pydantic v2 · Vue 3, TypeScript, Vite, Pinia, Tailwind CSS · Supabase (PostgreSQL, Auth, Storage; 29 SQL migrations) · ECPay · Resend (optional email) · Docker Compose · GitHub Actions CI

**Status:** An MVP that was never launched to real users or real events; the hosted backend on Google Cloud Run has been shut down, so the hosted demo is offline and the app runs locally with Docker. Payments target ECPay's staging (test) environment by default (`ECPAY_STAGE` defaults to true), and a code comment notes that ECPay's refund API does not work in staging.

**Run locally** (needs Docker and the Supabase CLI; steps from `docs/setup/local-cloud-switch.md`):
```bash
./scripts/use-local-supabase.sh      # set up .env for local Supabase
supabase start
./scripts/setup-local-supabase.sh    # write local Supabase keys into .env
supabase db reset                    # apply supabase/migrations
docker compose -f infra/docker-compose.yml up --build
```
Frontend: http://localhost:5173 · API health check: http://localhost:8000/api/v1/health. These steps are not confirmed on a fresh clone: `supabase/config.toml` is not committed, and the repo's acceptance checklist still lists `supabase db reset` as unverified. Paid checkout also needs ECPay to reach the webhook `/api/v1/webhooks/ecpay` at a public URL.

**Run tests** (same commands as `.github/workflows/ci.yml`, which uses Python 3.12 and Node 20). The repo defines 174 backend test functions (pytest, 37 files) and 57 frontend test cases (Vitest, 6 files); `-m "not integration"` excludes the 4 tests marked as needing a live Supabase project.
```bash
pip install -r backend/requirements.txt
(cd backend && pytest -q -m "not integration")
(cd frontend && npm ci && npm run test)
```

User flows, the architecture diagram and the documentation index are in the Chinese sections below and in [`docs/`](docs/).

---


**專為街舞社群打造的活動購票平台。**

從 Cypher 到 Battle、Workshop 到 Showcase — CypherHub 讓主辦方輕鬆開活動、讓舞者一站搞定報名購票。

---

## 這是什麼？

CypherHub 是一個街舞活動整合平台，解決街舞圈長期缺乏專屬工具的痛點。不同於 Accupass、KKTIX 等通用售票平台，CypherHub 從街舞社群的需求出發：

- 支援 Cypher、Battle、Workshop、Showcase、Jam 等街舞專屬活動分類
- 內建舞風篩選（Hiphop、Popping、Locking、Breaking、Waacking⋯）
- 從報名到現場核銷的完整閉環，不需要再用 Google 表單 + LINE 群組拼湊

---

## 使用流程

### 舞者（參加者）

```
瀏覽活動 → 依舞風/類型篩選 → 查看活動詳情
    → 登入 → 選擇票種 → 填寫報名表 → 付款（或免費報名）
        → 取得 QR 電子票券 → 活動當天出示 QR 入場
```

- 在首頁依舞風（Hiphop、Popping⋯）或活動類型（Battle、Workshop⋯）找活動
- 點進活動頁查看時間、地點、票價、主辦資訊與社群連結
- 登入後選票種，填寫主辦方設定的報名表（姓名、電話、舞風等）
- 免費活動直接報名；付費活動透過綠界金流完成付款（信用卡、ATM、超商代碼）
- 報名成功後在「我的票券」頁面取得 QR Code
- 活動當天打開 QR 讓主辦方掃碼即可入場

### 主辦方

```
申請主辦 → 建立活動 → 設定票種與報名表 → 管理報名名單
    → 活動當天掃碼核銷 → 查看結算 → 申請提領
```

- 申請成為主辦方，經平台審核通過後即可建立活動
- 設定活動資訊（時間、地點、舞風標籤、流程表、社群連結）
- 建立多種票種（免費/付費、不同價格與數量限制）
- 透過表單建構器自訂報名欄位（文字、下拉選單、勾選框等）
- 邀請團隊成員協作，分配 Owner / Admin / Staff 權限
- 活動當天用手機掃描 QR 或手動輸入完成核銷
- 活動結束後查看結算明細，申請提領收入

---

## 平台特色

| | CypherHub | 通用售票平台 |
|---|---|---|
| 舞風分類 | Hiphop、Popping、Locking、Breaking 等精準篩選 | 僅「舞蹈」大分類 |
| 活動類型 | Cypher、Battle、Workshop、Showcase、Jam 專屬標籤 | 無對應分類 |
| 報名表單 | 主辦方自訂欄位，可依票種設定不同問題 | 固定格式或需外掛 |
| 核銷方式 | QR 掃碼 + 手動輸入雙模式，手機即可操作 | 多數需另購設備 |
| 團隊協作 | Owner / Admin / Staff 三級權限 | 通常僅單一管理員 |
| 費用結算 | 內建結算與提領申請 | 需另外對帳 |

---

## 目前狀態

平台已完成所有規劃開發階段：

- **MVP-1** — 免費報名 + QR 核銷 + 舞風篩選 + 自訂報名表
- **MVP-2** — 付費票種 + 綠界金流 + 訂單管理 + 退款
- **MVP-3** — 多角色權限 + 主辦方審核 + 費用結算 + 審計紀錄
- **SEC-1~4** — HTTPS 強制、CORS 收斂、Secrets 管理、Rate Limit 完善

120+ 自動化測試通過，214 項驗收項目全數完成。

---

## 系統架構

```mermaid
graph TB
    subgraph Client["瀏覽器 / 手機"]
        FE["Vue 3 Frontend<br/>TypeScript · Pinia · TailwindCSS"]
    end

    subgraph Backend["Backend (Docker)"]
        API["Flask API<br/>/api/v1"]
        BP["Blueprints<br/>auth · events · tickets<br/>orders · payments · checkin"]
        SVC["Services Layer<br/>business logic"]
        API --> BP --> SVC
    end

    subgraph Supabase["Supabase Cloud"]
        AUTH["Auth (JWT)"]
        DB["PostgreSQL + RLS"]
        STORAGE["Storage"]
    end

    subgraph External["外部服務"]
        ECPAY["ECPay 綠界<br/>信用卡 · ATM · 超商"]
        RESEND["Resend<br/>Email"]
    end

    FE -->|"Bearer JWT"| API
    FE -->|"Supabase Auth SDK"| AUTH
    AUTH -->|"JWT"| API
    SVC -->|"service_role"| DB
    SVC -->|"AIO API"| ECPAY
    SVC -->|"SMTP API"| RESEND
    ECPAY -->|"Webhook"| API
    DB --- STORAGE
```

## 技術棧

| 層級 | 技術 |
|------|------|
| Backend | Python 3.12 / Flask / Pydantic v2 |
| Frontend | Vue 3 / TypeScript / Vite / TailwindCSS |
| Database | Supabase（PostgreSQL + Auth + RLS） |
| Payment | 綠界 ECPay（信用卡、ATM、超商代碼） |
| Email | Resend |
| Infra | Docker Compose / GitHub Actions CI/CD |

---

## 文件

所有開發、部署、API 文件集中在 [`docs/`](docs/) 目錄：

| 需求 | 文件 |
|------|------|
| 開發環境架設 | [docs/setup/local-cloud-switch.md](docs/setup/local-cloud-switch.md) |
| 開發規格與路線圖 | [docs/development/develop.md](docs/development/develop.md) |
| API 端點總表 | [docs/api/endpoints.md](docs/api/endpoints.md) |
| DB Schema | [docs/development/database-schema.md](docs/development/database-schema.md) |
| 環境變數清單 | [docs/development/environment-variables.md](docs/development/environment-variables.md) |
| 部署指南 | [docs/deployment/deploy-guide.md](docs/deployment/deploy-guide.md) |
| CI/CD | [docs/deployment/ci-cd.md](docs/deployment/ci-cd.md) |
| 驗收清單 | [docs/verification/acceptance-checklist.md](docs/verification/acceptance-checklist.md) |
| 完整文件索引 | [docs/verification/README.md](docs/verification/README.md) |

---

## 快速啟動

```bash
# 1. Clone
git clone https://github.com/your-org/CypherHub.git
cd CypherHub

# 2. 環境設定
cp .env.example .env
# 編輯 .env 填入 Supabase keys

# 3. 啟動
docker compose -f infra/docker-compose.yml up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/v1/health

詳細設定（本地 Supabase、雲端 Supabase、非 Docker 開發）請見 [docs/setup/local-cloud-switch.md](docs/setup/local-cloud-switch.md)。
