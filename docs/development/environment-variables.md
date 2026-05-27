# 環境變數完整清單

> 涵蓋 Backend（Flask）與 Frontend（Vite）所有環境變數。
> 對應原始碼：`backend/app/config.py`、`frontend/src/api/client.ts`、`frontend/src/api/supabase.ts`。

---

## 一、總覽

| 分類 | 數量 | 說明 |
|------|------|------|
| Backend | 17 | Flask app 透過 `config.py` 的 `os.getenv()` 讀取 |
| Frontend | 4 | Vite 透過 `import.meta.env.VITE_*` 讀取 |
| **合計** | **21** | |

### 機密等級標記

| 標記 | 說明 |
|------|------|
| 🔴 SECRET | 絕對不可洩露，禁止出現在 frontend / log / API response / git |
| 🟡 SENSITIVE | 不宜公開但洩露影響有限（如內部 URL） |
| 🟢 PUBLIC | 可安全公開 |

---

## 二、Backend 環境變數

### 2.1 應用程式核心

| 變數名 | 機密 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `APP_ENV` | 🟢 | 否 | `development` | 應用環境。`development` / `production` |
| `FLASK_DEBUG` | 🟢 | 否 | `0` | 啟用 Flask debug mode。`1` / `true` / `True` 為啟用 |
| `CORS_ORIGINS` | 🟢 | 否 | `http://localhost:5173` | 允許的 CORS 來源，逗號分隔。例：`http://localhost:5173,https://app.cypherhub.com` |
| `FRONTEND_BASE_URL` | 🟡 | 否 | `http://localhost:5173` | 前端 URL，用於 Email 中的票券連結、活動連結等 |

**讀取方式**（`config.py`）：

```python
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
```

### 2.2 Supabase 連線

| 變數名 | 機密 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `SUPABASE_URL` | 🟡 | **是** | _(空)_ | Supabase 專案 URL |
| `SUPABASE_ANON_KEY` | 🟡 | **是** | _(空)_ | Supabase 公開 / Anonymous Key（即 Publishable Key） |
| `SUPABASE_SERVICE_ROLE_KEY` | 🔴 | **是** | _(空)_ | Supabase Service Role Key，繞過 RLS，**僅限 server-side** |

> ⚠️ `SUPABASE_SERVICE_ROLE_KEY` **禁止**出現在 frontend、log、API response 中。

**本地 vs 雲端差異**：

| 環境 | `SUPABASE_URL` | Key 來源 |
|------|-----------------|----------|
| 本地（`supabase start`） | `http://127.0.0.1:54321`（直接執行）<br>`http://host.docker.internal:54321`（Docker 內） | `supabase status` 輸出 |
| 雲端 | `https://YOUR_PROJECT_REF.supabase.co` | Supabase Dashboard → Settings → API |

**讀取方式**：

```python
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
```

**使用端**（`services/supabase_client.py`）：

```python
public_client()         # 使用 ANON_KEY → 受 RLS anon 政策約束
authed_client(jwt)      # 使用使用者 JWT → 受 RLS authenticated 政策約束
service_role_client()   # 使用 SERVICE_ROLE_KEY → 繞過 RLS
```

### 2.3 ECPay 綠界金流

| 變數名 | 機密 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `ECPAY_MERCHANT_ID` | 🔴 | 是（付費功能） | _(空)_ | 綠界特店編號 |
| `ECPAY_HASH_KEY` | 🔴 | 是（付費功能） | _(空)_ | 綠界 HashKey（用於 CheckMacValue 驗證） |
| `ECPAY_HASH_IV` | 🔴 | 是（付費功能） | _(空)_ | 綠界 HashIV（用於 CheckMacValue 驗證） |
| `ECPAY_RETURN_URL` | 🟡 | 是（付費功能） | _(空)_ | 綠界 Webhook 回呼 URL。必須 HTTPS（本地用 ngrok） |
| `ECPAY_STAGE` | 🟢 | 否 | `1` | 測試模式。`1` / `true` = 測試環境（stage.ecpay.com.tw）；`0` / `false` = 正式環境 |

> 💡 僅 MVP-2 付費票功能需要 ECPay 變數。MVP-1 免費報名不需設定。

**測試環境值**（綠界提供）：

```
ECPAY_MERCHANT_ID=3002607
ECPAY_HASH_KEY=pwFHCqoQZGmho4w6
ECPAY_HASH_IV=EkRm7iFT261dpevs
ECPAY_STAGE=1
```

**讀取方式**：

```python
ECPAY_MERCHANT_ID = os.getenv("ECPAY_MERCHANT_ID", "")
ECPAY_HASH_KEY = os.getenv("ECPAY_HASH_KEY", "")
ECPAY_HASH_IV = os.getenv("ECPAY_HASH_IV", "")
ECPAY_RETURN_URL = os.getenv("ECPAY_RETURN_URL", "")
ECPAY_STAGE = os.getenv("ECPAY_STAGE", "1").lower() in ("1", "true")
```

### 2.4 Email（Resend）

| 變數名 | 機密 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `RESEND_API_KEY` | 🔴 | 否 | _(空)_ | Resend API Key。未設定時進入 stub mode（僅 log 不發信） |
| `RESEND_FROM_EMAIL` | 🟢 | 否 | `CypherHub <onboarding@resend.dev>` | 寄件者地址 |

> 💡 開發階段可不設定 `RESEND_API_KEY`，`email_service` 會以 stub mode 運行，將信件內容輸出至 log。

**讀取方式**（`services/email_service.py` 直接讀取）：

```python
api_key = os.environ.get("RESEND_API_KEY")
from_email = os.environ.get("RESEND_FROM_EMAIL", "CypherHub <onboarding@resend.dev>")
```

### 2.5 平台管理

| 變數名 | 機密 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `ADMIN_ALLOWLIST` | 🟡 | 否 | _(空)_ | 平台管理員白名單。逗號分隔的 user_id 或 email |
| `PLATFORM_FEE_RATE` | 🟢 | 否 | `0.05` | 平台抽成比例（float）。`0.05` = 5% |
| `ORG_APPROVAL_REQUIRED` | 🟢 | 否 | `0` | 是否需要管理員審核組織入駐。`1` / `true` 為啟用 |

**範例**：

```bash
ADMIN_ALLOWLIST=admin@example.com,550e8400-e29b-41d4-a716-446655440000
PLATFORM_FEE_RATE=0.05
ORG_APPROVAL_REQUIRED=1
```

**讀取方式**：

```python
ADMIN_ALLOWLIST = {s.strip() for s in os.getenv("ADMIN_ALLOWLIST", "").split(",") if s.strip()}
PLATFORM_FEE_RATE = float(os.getenv("PLATFORM_FEE_RATE", "0.05"))
ORG_APPROVAL_REQUIRED = os.getenv("ORG_APPROVAL_REQUIRED", "0").lower() in ("1", "true")
```

### 2.6 背景任務

| 變數名 | 機密 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `CRON_SECRET` | 🔴 | 是（Cron job） | _(空)_ | 外部 Cron 呼叫 `/api/v1/internal/jobs/*` 時的驗證 header |

**使用方式**（`blueprints/jobs.py`）：

```python
# 外部 Cron 請求必須帶 X-Cron-Secret header
secret = request.headers.get("X-Cron-Secret", "")
if secret != current_app.config.get("CRON_SECRET"):
    raise AppError(code="FORBIDDEN", ...)
```

**呼叫範例**：

```bash
curl -X POST https://api.example.com/api/v1/internal/jobs/event-reminders \
  -H "X-Cron-Secret: your-secret-here"
```

---

## 三、Frontend 環境變數

Vite 規定前端環境變數必須以 `VITE_` 為前綴，透過 `import.meta.env.VITE_*` 存取。

| 變數名 | 機密 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `VITE_API_BASE_URL` | 🟢 | **是** | `http://localhost:8000` | Backend API base URL |
| `VITE_SUPABASE_URL` | 🟡 | **是** | _(空)_ | Supabase 專案 URL（與 Backend 同值） |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | 🟡 | **是**（二擇一） | _(空)_ | Supabase Publishable Key（新格式，優先使用） |
| `VITE_SUPABASE_ANON_KEY` | 🟡 | **是**（二擇一） | _(空)_ | Supabase Anon Key（舊格式，向下相容） |

> `VITE_SUPABASE_PUBLISHABLE_KEY` 與 `VITE_SUPABASE_ANON_KEY` 二擇一即可。`supabase.ts` 優先使用 `PUBLISHABLE_KEY`，若未設定則 fallback 至 `ANON_KEY`。

**使用端**：

```typescript
// frontend/src/api/client.ts
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

// frontend/src/api/supabase.ts
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
  || import.meta.env.VITE_SUPABASE_ANON_KEY;
```

**本地 vs 雲端差異**：

| 環境 | `VITE_API_BASE_URL` | `VITE_SUPABASE_URL` |
|------|----------------------|---------------------|
| 本地 | `http://localhost:8000` | `http://127.0.0.1:54321` |
| 雲端 | `https://cypherhub-234430776857.asia-east1.run.app` | `https://YOUR_PROJECT_REF.supabase.co` |

---

## 四、.env 檔案管理

### 4.1 檔案結構

```
backend/
├── .env                    # 目前使用的環境變數（git ignored）
├── .env.example            # 通用範本（commit 至 git）
├── .env.local.example      # 本地 Supabase 範本
└── .env.cloud.example      # 雲端 Supabase 範本

frontend/
├── .env                    # 目前使用的環境變數（git ignored）
├── .env.example            # 通用範本（commit 至 git）
├── .env.local.example      # 本地開發範本
└── .env.cloud.example      # 雲端範本
```

### 4.2 本地 / 雲端切換

提供兩支 script 快速切換（僅複製 `.env` 檔案，不改 code）：

```bash
# 切換至本地 Supabase
./scripts/use-local-supabase.sh

# 切換至雲端 Supabase
./scripts/use-cloud-supabase.sh
```

詳見 [setup/local-cloud-switch.md](../setup/local-cloud-switch.md)。

### 4.3 Docker Compose

`infra/docker-compose.yml` 透過 `env_file` 載入：

```yaml
services:
  backend:
    env_file: ../.env
  frontend:
    env_file: ../.env
```

Docker 環境中 `SUPABASE_URL` 需使用 `http://host.docker.internal:54321`（而非 `127.0.0.1`），才能從容器內存取主機的本地 Supabase。

### 4.4 CI/CD

`.github/workflows/ci.yml` 中的 unit test job 不需外部服務，因此不設定環境變數（測試使用 monkeypatch mock）。

---

## 五、快速設定指南

### 5.1 最小可運行（MVP-1 免費報名）

只需設定 Supabase 連線，其他皆有預設值或可省略：

```bash
# .env
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=eyJ...（from supabase status）
SUPABASE_SERVICE_ROLE_KEY=eyJ...（from supabase status）

VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_ANON_KEY=eyJ...（same as backend ANON_KEY）
```

### 5.2 完整功能（含付費 + Email + 管理）

在最小設定之上加入：

```bash
# .env（追加）
ECPAY_MERCHANT_ID=3002607          # 測試特店
ECPAY_HASH_KEY=pwFHCqoQZGmho4w6
ECPAY_HASH_IV=EkRm7iFT261dpevs
ECPAY_RETURN_URL=https://cypherhub-234430776857.asia-east1.run.app/api/v1/webhooks/ecpay
ECPAY_STAGE=1

RESEND_API_KEY=re_xxxx
RESEND_FROM_EMAIL=CypherHub <noreply@your-domain.com>

ADMIN_ALLOWLIST=your-email@example.com
PLATFORM_FEE_RATE=0.05
ORG_APPROVAL_REQUIRED=1
CRON_SECRET=your-random-secret

FRONTEND_BASE_URL=http://localhost:5173
```

### 5.3 正式環境 Checklist

上線前確認：

- [ ] `APP_ENV=production`
- [ ] `FLASK_DEBUG=0`
- [ ] `ECPAY_STAGE=0`（切至正式環境）
- [ ] `ECPAY_MERCHANT_ID` / `HASH_KEY` / `HASH_IV` 使用正式特店值
- [ ] `ECPAY_RETURN_URL` 為正式 HTTPS URL
- [ ] `CORS_ORIGINS` 僅包含正式域名
- [ ] `FRONTEND_BASE_URL` 為正式前端 URL
- [ ] `SUPABASE_URL` / Keys 指向雲端 Supabase
- [ ] `RESEND_FROM_EMAIL` 使用已驗證的域名
- [ ] `CRON_SECRET` 為足夠強度的隨機字串
- [ ] 所有 🔴 SECRET 變數存放於安全的 Secrets Manager（非明文 `.env`）

---

## 六、變數總表

| # | 變數名 | 層級 | 機密 | 必填 | 預設值 | 用途 |
|---|--------|------|------|------|--------|------|
| 1 | `APP_ENV` | Backend | 🟢 | 否 | `development` | 應用環境 |
| 2 | `FLASK_DEBUG` | Backend | 🟢 | 否 | `0` | Debug 模式 |
| 3 | `CORS_ORIGINS` | Backend | 🟢 | 否 | `http://localhost:5173` | CORS 白名單 |
| 4 | `FRONTEND_BASE_URL` | Backend | 🟡 | 否 | `http://localhost:5173` | Email 連結前綴 |
| 5 | `SUPABASE_URL` | Both | 🟡 | **是** | _(空)_ | Supabase URL |
| 6 | `SUPABASE_ANON_KEY` | Both | 🟡 | **是** | _(空)_ | Supabase Anon Key |
| 7 | `SUPABASE_SERVICE_ROLE_KEY` | Backend | 🔴 | **是** | _(空)_ | Supabase Service Role |
| 8 | `ECPAY_MERCHANT_ID` | Backend | 🔴 | 付費功能 | _(空)_ | 綠界特店編號 |
| 9 | `ECPAY_HASH_KEY` | Backend | 🔴 | 付費功能 | _(空)_ | 綠界 HashKey |
| 10 | `ECPAY_HASH_IV` | Backend | 🔴 | 付費功能 | _(空)_ | 綠界 HashIV |
| 11 | `ECPAY_RETURN_URL` | Backend | 🟡 | 付費功能 | _(空)_ | 綠界 Webhook URL |
| 12 | `ECPAY_STAGE` | Backend | 🟢 | 否 | `1` | 綠界測試模式 |
| 13 | `RESEND_API_KEY` | Backend | 🔴 | 否 | _(空)_ | Resend Email Key |
| 14 | `RESEND_FROM_EMAIL` | Backend | 🟢 | 否 | `CypherHub <onboarding@resend.dev>` | 寄件者 |
| 15 | `ADMIN_ALLOWLIST` | Backend | 🟡 | 否 | _(空)_ | 管理員白名單 |
| 16 | `PLATFORM_FEE_RATE` | Backend | 🟢 | 否 | `0.05` | 平台抽成 |
| 17 | `ORG_APPROVAL_REQUIRED` | Backend | 🟢 | 否 | `0` | 組織審核開關 |
| 18 | `CRON_SECRET` | Backend | 🔴 | Cron job | _(空)_ | Cron 驗證密鑰 |
| 19 | `VITE_API_BASE_URL` | Frontend | 🟢 | **是** | `http://localhost:8000` | Backend API URL |
| 20 | `VITE_SUPABASE_URL` | Frontend | 🟡 | **是** | _(空)_ | Supabase URL |
| 21 | `VITE_SUPABASE_PUBLISHABLE_KEY` | Frontend | 🟡 | 二擇一 | _(空)_ | Supabase Key（新） |
| 22 | `VITE_SUPABASE_ANON_KEY` | Frontend | 🟡 | 二擇一 | _(空)_ | Supabase Key（舊） |
