# 部署指南

> 本文件說明 CypherHub 從本地開發到正式上線的完整部署流程。
> 涵蓋前端（Vercel）、後端（Docker / Cloud Run）、Supabase 雲端、DNS 設定、以及首次部署與更新部署的差異。

---

## 一、部署架構總覽

```
                                   ┌──────────────────────┐
                                   │    Namecheap 網域    │
                                   │ (your-domain.com)    │
                                   └──────────┬───────────┘
                                              │
                                   ┌──────────▼───────────┐
                                   │    Cloudflare DNS    │
                                   │  (解析與 Proxy 管理)   │
                                   └──────────┬───────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    │                                                   │
              ┌─────▼───────────────┐                             ┌─────▼───────────────┐
              │ Vercel (Frontend)   │                             │ Zeabur (Backend)    │
              │ app.your-domain.com │───API (CORS 允許)─────────▶ │ api.your-domain.com │
              │ Vue 3 + Vite SPA    │                             │ Flask Backend       │
              └─────────────────────┘                             └────────────┬────────────┘
                                                                               │
                                          ┌────────────────────────────────────┼─────────────────────┐
                                          ▼                                    ▼                     ▼
                                ┌──────────────────┐                 ┌──────────────────┐  ┌──────────────────┐
                                │  Supabase Cloud  │                 │  ECPay 綠界      │  │  Resend          │
                                │  (Auth + DB      │                 │  金流 API        │  │  Email API       │
                                │   + Storage)     │                 └──────────────────┘  └──────────────────┘
                                └──────────────────┘
```

| 元件 | 推薦服務 |
|------|----------|
| Frontend hosting | Vercel |
| Backend hosting | Zeabur |
| Database + Auth | Supabase Cloud |
| Email | Resend |
| Payment | ECPay 綠界 |
| Domain | Namecheap |
| DNS | Cloudflare |

---

## 二、Supabase 雲端設定

### 2.1 建立專案

1. 登入 [supabase.com](https://supabase.com) → New Project
2. 選擇 Region（建議 `Northeast Asia (Tokyo)` 或 `Southeast Asia (Singapore)`）
3. 設定 Database Password（保存備用）
4. 記錄以下資訊（Settings → API）：

   | 項目 | 用途 |
   |------|------|
   | Project URL | `SUPABASE_URL` / `VITE_SUPABASE_URL` |
   | `anon` public key | `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY` |
   | `service_role` key | `SUPABASE_SERVICE_ROLE_KEY`（🔴 僅 Backend） |

### 2.2 推送 Migrations

```bash
# 安裝 Supabase CLI（若尚未安裝）
brew install supabase/tap/supabase

# 登入
supabase login

# 連結專案
supabase link --project-ref YOUR_PROJECT_REF

# 預覽要套用的 migrations
supabase db push --dry-run

# 正式推送（0001-0027 全部套用）
supabase db push
```

> 也可使用專案內建的 script：`./scripts/push-to-cloud.sh`

### 2.3 Storage Bucket

Migration `0014` 會自動建立 `event-media` bucket，但推送至雲端後需確認：

1. Dashboard → Storage → 確認 `event-media` bucket 存在
2. 確認 policies：
   - Public read（任何人可讀取活動圖片）
   - Authenticated upload（登入使用者可上傳）
3. 限制：5MB、僅允許 `image/*` MIME type

若 bucket 未自動建立，手動執行：

```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('event-media', 'event-media', true, 5242880, ARRAY['image/*']);
```

### 2.4 Auth 設定

Dashboard → Authentication → Settings：

| 設定 | 建議值 | 說明 |
|------|--------|------|
| Site URL | `https://your-domain.com` | 前端正式 URL |
| Redirect URLs | `https://your-domain.com/reset-password` | 忘記密碼導向 |
| Email Confirmations | 依需求 | 開啟則註冊後需驗證信箱 |
| JWT Expiry | `3600`（1 小時） | Access token 有效期 |
| Minimum Password Length | `6`（或更高） | 密碼強度 |

### 2.5 pg_cron 排程

Migration `0018` 建立了兩個排程任務：

| Job | 排程 | 用途 |
|-----|------|------|
| `release_expired_holds` | 每分鐘 | 釋放逾時的 holding 訂單 |
| `compensate_paid_orders` | 每 5 分鐘 | 補償已付款但未出票的訂單 |

Supabase Cloud 預設啟用 `pg_cron`，推送 migration 後即生效。確認方式：

```sql
SELECT jobid, schedule, command FROM cron.job;
```

---

## 三、Backend 部署

### 3.1 準備與部署 (Zeabur)

Zeabur 支援直接從 GitHub repository 自動建置與部署，非常適合 Python/Flask 專案。

#### 3.1.1 準備工作

專案已有 `backend/Dockerfile` 以及 `requirements.txt`。Zeabur 在偵測到這些檔案時可以自動處理建置。

確保 `requirements.txt` 中已包含 `gunicorn`。正式環境會透過 Dockerfile 裡的 CMD 使用 gunicorn 啟動服務。

#### 3.1.2 在 Zeabur 上部署

1. 登入 [Zeabur](https://zeabur.com)
2. 建立新專案 (Create Project)
3. 點擊 "Deploy New Service"，選擇 "GitHub"
4. 選擇你的 CypherHub Repository
5. 在部署設定中：
   - 選擇你的 Branch (通常是 `main`)
   - 確保 **Root Directory** 設定為 `backend` (如果你的 repo 包含前後端的話)
6. 點擊 Deploy。

#### 3.1.3 設定環境變數 (Variables)

在 Zeabur Dashboard 中，進入該服務的 "Variables" 頁籤，將以下機密資訊填入：

| 變數名稱 | 說明 |
|---------|------|
| `APP_ENV` | 設為 `production` |
| `FLASK_DEBUG` | 設為 `0` |
| `SUPABASE_URL` | Supabase URL |
| `SUPABASE_ANON_KEY` | Supabase Anon Key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Service Role Key (🔴 SECRET) |
| `ECPAY_STAGE` | `0` (若是正式環境) |
| `ECPAY_MERCHANT_ID` | 綠界商店代號 (🔴 SECRET) |
| `ECPAY_HASH_KEY` | 綠界 HashKey (🔴 SECRET) |
| `ECPAY_HASH_IV` | 綠界 HashIV (🔴 SECRET) |
| `CORS_ORIGINS` | 你的前端 Vercel URL (例如 `https://your-domain.vercel.app`) |

*註：Zeabur 會自動提供一組預設的公開網域 (例如 `your-project.zeabur.app`)，請先記錄下這組網址，後續我們會用 Cloudflare 自訂網域指向它。*

---

## 四、Frontend 部署（Vercel）

### 4.1 首次部署

1. 登入 [vercel.com](https://vercel.com) → Import Project → 選擇 GitHub repo
2. 設定：

   | 項目 | 值 |
   |------|-----|
   | Framework Preset | Vue.js |
   | Root Directory | `frontend` |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |

3. 設定 Environment Variables：

   | 變數 | 值 |
   |------|-----|
   | `VITE_API_BASE_URL` | `https://api.your-domain.com`（Backend URL） |
   | `VITE_SUPABASE_URL` | `https://YOUR_REF.supabase.co` |
   | `VITE_SUPABASE_ANON_KEY` | Supabase anon key |

4. Deploy

### 4.2 SPA 路由處理

Vue Router 使用 HTML5 History Mode，需設定 rewrite 規則。在 `frontend/` 建立 `vercel.json`：

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

> 這確保所有路徑（如 `/events/123`、`/login`）都導向 `index.html`，由 Vue Router 處理。

### 4.3 自訂域名

1. Vercel Dashboard → Project → Settings → Domains
2. 新增域名（如 `app.your-domain.com`）
3. 依 Vercel 指示設定 DNS：
   - `CNAME app → cname.vercel-dns.com`
4. Vercel 自動簽發 SSL 憑證

### 4.4 Preview Deployments

Vercel 預設對每個 PR 產生 Preview URL。注意：

- Preview 環境的 `VITE_API_BASE_URL` 仍指向正式 Backend（除非另設 staging）
- 敏感環境變數建議僅設定在 Production environment

---

## 五、網域與 DNS 設定 (Namecheap + Cloudflare)

本專案使用 Namecheap 購買網域，並將 DNS 解析託管至 Cloudflare 進行統一管理與防護。

### 5.1 步驟一：Namecheap 網域註冊與設定

1. 登入 [Namecheap](https://www.namecheap.com/) 並購買你的網域（例如 `your-domain.com`）。
2. 在 Domain List 找到剛購買的網域，點擊 `Manage`。
3. 找到 **Nameservers** 區塊。我們稍後要將這裡改為 "Custom DNS"，並填入 Cloudflare 提供的 Nameservers。

### 5.2 步驟二：註冊與設定 Cloudflare

1. 登入 [Cloudflare](https://dash.cloudflare.com/)。
2. 點擊 `Add a Site`，輸入你的網域 `your-domain.com`。
3. 選擇 Free Plan。
4. Cloudflare 會掃描既有 DNS 紀錄，點擊 `Continue`。
5. Cloudflare 會提供你兩組 Nameservers（例如 `olivia.ns.cloudflare.com` 與 `rick.ns.cloudflare.com`）。
6. 回到 Namecheap 的 **Nameservers** 區塊，選擇 `Custom DNS`，並填入這兩組 Cloudflare Nameservers，點擊綠色勾勾儲存。
7. 回到 Cloudflare，點擊 `Done, check nameservers`。（DNS 生效可能需要幾分鐘到數小時）

### 5.3 步驟三：設定 DNS 紀錄 (在 Cloudflare)

在 Cloudflare 的 DNS → Records 區塊中，新增以下紀錄：

| Type | Name | Content | Proxy status | 說明 |
|------|------|---------|--------------|------|
| CNAME | `app` | `cname.vercel-dns.com` | DNS only | 前端 Vercel (關閉小橘雲) |
| CNAME | `api` | `your-project.zeabur.app` | Proxied | 後端 Zeabur (開啟小橘雲) |
| CNAME | `@` | `cname.vercel-dns.com` | DNS only | (選填) 主網域指向前端 |

> ⚠️ **重要提醒：Vercel 的限制**
> Vercel 會自動為你的前端簽發 SSL 憑證，並要求 DNS 紀錄為 **DNS only**（關閉 Cloudflare Proxy/小橘雲）。如果開啟 Proxy，會導致 SSL 憑證衝突（`ERR_TOO_MANY_REDIRECTS`）。

### 5.4 步驟四：在 Vercel 綁定自訂網域

1. Vercel Dashboard → Project → Settings → Domains
2. 新增網域：`app.your-domain.com` (或 `your-domain.com`)。
3. 由於已經在 Cloudflare 設定好 DNS，Vercel 偵測到 CNAME 指向後，會自動簽發 SSL 憑證並顯示 `Valid`。

### 5.5 步驟五：在 Zeabur 綁定自訂網域

1. Zeabur Dashboard → 進入你的 CypherHub 專案 → 點擊 Backend 服務。
2. 在 Domain (網域) 區塊，新增自訂網域 `api.your-domain.com`。
3. 由於 Cloudflare 的 `api` 紀錄已開啟 Proxy (Proxied)，Zeabur 將透過 Cloudflare 接收請求，並自動獲得 HTTPS 保護。

### 5.6 最終 CORS 確認

當前後端都綁定好自訂網域後，必須回頭去修改**後端的環境變數**：

在 Zeabur Dashboard 的 Variables：
```bash
CORS_ORIGINS=https://app.your-domain.com
FRONTEND_BASE_URL=https://app.your-domain.com
```

---

## 六、環境變數配置

### 6.1 正式環境完整變數

**Backend**：

```bash
# 核心
APP_ENV=production
FLASK_DEBUG=0
CORS_ORIGINS=https://app.your-domain.com
FRONTEND_BASE_URL=https://app.your-domain.com

# Supabase
SUPABASE_URL=https://YOUR_REF.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...          # 🔴 SECRET

# ECPay（正式環境）
ECPAY_MERCHANT_ID=YOUR_PROD_ID            # 🔴 SECRET
ECPAY_HASH_KEY=YOUR_PROD_KEY              # 🔴 SECRET
ECPAY_HASH_IV=YOUR_PROD_IV               # 🔴 SECRET
ECPAY_RETURN_URL=https://api.your-domain.com/api/v1/webhooks/ecpay
ECPAY_STAGE=0                             # ⚠️ 0 = 正式環境

# Email
RESEND_API_KEY=re_xxxx                    # 🔴 SECRET
RESEND_FROM_EMAIL=CypherHub <noreply@your-domain.com>

# 管理
ADMIN_ALLOWLIST=admin@your-domain.com
PLATFORM_FEE_RATE=0.05
ORG_APPROVAL_REQUIRED=1

# 背景任務
CRON_SECRET=your-strong-random-secret     # 🔴 SECRET
```

**Frontend**：

```bash
VITE_API_BASE_URL=https://api.your-domain.com
VITE_SUPABASE_URL=https://YOUR_REF.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

### 6.2 Secrets 管理

正式環境的 🔴 SECRET 變數**不應**以明文 `.env` 存放。建議：

| 部署平台 | Secrets 管理方式 |
|----------|-----------------|
| Zeabur | Dashboard → Variables |
| Vercel | Dashboard → Environment Variables（標記為 Sensitive） |
| Cloud Run | Google Secret Manager（`--set-secrets`） |
| Render / Fly.io | 各平台 Dashboard → Environment / Secrets |

詳見 [development/environment-variables.md](../development/environment-variables.md)。

---

## 七、背景任務部署

### 7.1 pg_cron（Database 層）

已透過 migration 設定，推送後自動啟用：

- `release_expired_holds`：每分鐘
- `compensate_paid_orders`：每 5 分鐘

### 7.2 外部 Cron Job（Application 層）

活動提醒等任務透過外部 Cron 呼叫 Backend API：

```bash
# 每小時執行活動提醒
curl -X POST https://api.your-domain.com/api/v1/internal/jobs/event-reminders \
  -H "X-Cron-Secret: your-cron-secret"
```

**設定方式**（依平台）：

| 平台 | 方式 |
|------|------|
| Zeabur | 目前未內建 Cron，建議使用 cron-job.org 呼叫 API |
| cron-job.org | 免費外部 Cron 服務 |
| GitHub Actions | Scheduled workflow（`cron: '0 * * * *'`） |

---

## 八、Health Check 與監控

### 8.1 Health Endpoint

```
GET /api/v1/health
→ { "status": "ok" }
```

部署平台可用此端點做 liveness check：

- Zeabur：在 Dashboard 自動監控服務狀態
- Vercel：前端為靜態檔，無需 health check

### 8.2 監控建議

| 監控項目 | 工具建議 |
|----------|----------|
| API 可用性 | UptimeRobot / Better Stack（ping `/api/v1/health`） |
| 錯誤追蹤 | Sentry（Flask + Vue 整合） |
| 效能 | Cloud Run Metrics / Supabase Dashboard |
| 日誌 | Cloud Logging / `fly logs` / Supabase Logs |

---

## 九、首次部署 vs 更新部署

### 9.1 首次部署 Checklist

```
1. Supabase 雲端
   □ 建立 Supabase 專案
   □ supabase link --project-ref YOUR_REF
   □ supabase db push（套用所有 migrations）
   □ 確認 event-media bucket 與 policies
   □ 設定 Auth（Site URL、Redirect URLs）
   □ 記錄 URL + Keys

2. Backend
   □ 準備好 requirements.txt 與 Dockerfile
   □ 在 Zeabur 部署 GitHub Repo
   □ 進入 Dashboard 設定所有 Variables / secrets
   □ 確認 /api/v1/health 回傳 200
   □ 記錄 Backend URL（預設為 zeabur.app 網域或自訂域名）

3. Frontend
   □ Vercel Import Project
   □ 設定 Root Directory = frontend
   □ 設定環境變數（VITE_API_BASE_URL 等）
   □ 建立 vercel.json（SPA rewrite）
   □ Deploy
   □ 確認頁面可正常載入

4. DNS
   □ 設定 app.domain → Vercel
   □ 設定 api.domain → Backend
   □ 確認 HTTPS 憑證生效

5. 驗證
   □ CORS_ORIGINS 包含前端域名
   □ ECPAY_RETURN_URL 為正式 HTTPS URL
   □ FRONTEND_BASE_URL 為正式前端 URL
   □ 註冊 → 登入 → 瀏覽活動 → 報名（完整流程）
   □ ECPay 付款測試（先用測試環境確認流程）
   □ Email 寄送確認
   □ Supabase Auth Redirect URL 設定正確

6. 背景任務
   □ pg_cron 排程確認（release_expired_holds、compensate_paid_orders）
   □ 外部 Cron 設定（event-reminders）
```

### 9.2 更新部署

一般程式碼更新（不含 DB migration）：

```bash
# Backend — 只要 Push 至對應的 Branch (如 main) Zeabur 即會自動觸發建置與部署
git push origin main

# Frontend — Vercel 自動部署（push to main 即觸發）
git push origin main
```

包含 DB migration 的更新：

```bash
# 1. 先推送 migration
supabase db push

# 2. 再部署 Backend（確保新 code 對應新 schema）
# (在 GitHub push 程式碼，由 Zeabur 接手部署)
git push origin main

# 3. Frontend（若有 API contract 變更）
# (同上，Vercel 自動部署)
```

> ⚠️ **順序很重要**：先推 migration → 再部署 Backend → 最後更新 Frontend。避免 Backend 存取尚未存在的表或欄位。

### 9.3 Rollback

**Backend rollback**：

在 Zeabur Dashboard 中：
1. 進入 Service 設定
2. 找到 "Deployments" 歷史紀錄
3. 選擇先前穩定的版本，點擊 Rollback 或 Redeploy

**Frontend rollback**：

Vercel Dashboard → Deployments → 選擇先前版本 → Promote to Production

**Database rollback**：

Supabase 不支援自動 rollback migration。需手動撰寫反向 SQL 或從 Point-in-Time Recovery 還原。建議：

- 新 migration 上線前先在本地 `supabase db reset` 測試
- 破壞性變更（DROP TABLE / DROP COLUMN）謹慎處理，建議先 deprecate 再移除

---

## 十、本地開發部署（Docker Compose）

供本地開發或 staging 使用：

```bash
# 啟動本地 Supabase
supabase start

# 切換至本地環境
./scripts/use-local-supabase.sh

# 套用 migrations
supabase db reset

# 啟動 Backend + Frontend
docker compose -f infra/docker-compose.yml up --build
```

存取：
- Frontend：`http://localhost:5173`
- Backend API：`http://localhost:8000`
- Supabase Studio：`http://localhost:54323`

---

## 十一、常見問題

### Q: CORS 錯誤（`Access-Control-Allow-Origin` missing）

確認 Backend 的 `CORS_ORIGINS` 包含前端 URL，且格式正確（含 protocol，無尾斜線）：
```bash
# ✅ 正確
CORS_ORIGINS=https://app.your-domain.com
# ❌ 錯誤
CORS_ORIGINS=app.your-domain.com
CORS_ORIGINS=https://app.your-domain.com/
```

### Q: Supabase Auth redirect 失敗

確認 Supabase Dashboard → Auth → URL Configuration → Redirect URLs 包含：
- `https://app.your-domain.com/reset-password`
- `https://app.your-domain.com`（主站）

### Q: ECPay Webhook 收不到

- 確認 `ECPAY_RETURN_URL` 為 HTTPS（ECPay 不支援 HTTP callback）
- 確認 URL 可從外部存取（Zeabur 的 public URL 或自訂域名）
- 本地測試需使用 ngrok：`ngrok http 8000`

### Q: Docker 內無法連線本地 Supabase

Docker 容器無法用 `127.0.0.1` 存取主機服務，需使用：
- macOS / Windows：`http://host.docker.internal:54321`
- Linux：`http://172.17.0.1:54321`（或用 `--network host`）

### Q: Frontend 路由 404

SPA 需要 rewrite 規則將所有路徑導向 `index.html`。確認 `vercel.json` 或對應平台的 rewrite 設定正確。
