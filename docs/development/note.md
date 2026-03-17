# 待辦事項

- [ ] 街舞活動客製化資訊：附近抽煙地點、便利商店、小吃、聚餐餐廳推薦
- [ ] 活動日曆：集中檢視報名／參加的活動
- [ ] 提醒功能：活動前（一週／幾天／當天）自訂 timer 提醒
- [ ] 即時活動進度：主辦方可更新進度（如海選、晉級等），參加者可即時查看
- [ ] Google Maps 導航：活動頁面加入「導航」按鈕，串接 Google Map
- [ ] AI 推薦系統：依使用者過往參與偏好推薦街舞活動

---

# 後續發展（街舞生態深化）

## 街舞活動客製化
- 活動場地周邊資訊：抽煙區、便利商店、小吃、聚餐餐廳（依距離／評分排序）
- 串接 Google Places API 或 OpenStreetMap／Overpass 取得周邊 POI

## 活動日曆與提醒
- 個人日曆視圖：月曆／週曆顯示已報名／已加入的活動
- 可匯出 iCal（與 Google Calendar、Apple Calendar 同步）
- 提醒規則：比賽前 7 天／3 天／1 天／當天 自訂通知（Email + 站內可選）

## 即時活動進度
- 主辦方可即時更新階段：海選中 → 晉級公布 → 決賽等
- 參加者即時看到目前進度，減少「不知道比到哪」的狀況
- 技術：WebSocket 或 SSE 即時推送、或短輪詢

## 導航整合
- 活動詳情頁加入「導航至此」按鈕
- 開啟 Google Maps：`https://www.google.com/maps/dir/?api=1&destination={lat},{lng}`

## AI 活動推薦
- 基於：參加／報名過的活動（舞風、地區、主辦方、時間偏好）
- 輸出：個人化街舞活動推薦列表
- 可選：協同過濾、內容特徵 + 輕量 embedding

---

# 進入 MVP2 前優化與補強建議

> 基於 verification-report、FRONTEND_UI_IMPROVEMENT_PLAN、UI_UX_OPTIMIZATION_PLAN、實際程式碼分析

## 一、現況總覽

| 類別 | 狀態 |
|------|------|
| MVP1 核心流程 | ✓ 完整（活動→報名→出票→核銷、Form Builder、register_free_v2、防超賣） |
| JWT + RLS | ✓ 已落實 |
| Rate limiting | ✓ auth 10/min、register 20/min、checkin 60/min |
| Email | 可選 Resend；未設定時僅 log，非純 stub |
| CI/CD | ✗ 無 GitHub Actions |
| 測試 | 有 pytest，但無 rate limit、email 單元測試；多 mock、少整合 |
| UI/UX | Phase 1–4 已完成；FRONTEND_UI 多數已做，表單輸入仍偏深色 |

## 二、優先級建議

### 🔴 高優先（進入 MVP2 前強烈建議）

| 項目 | 說明 |
|------|------|
| **CI pipeline** | GitHub Actions：`ruff check`、`pytest`、`npm run build`，PR 時自動跑並阻擋失敗 |
| **README 更新** | 將「Resend 為 stub」改為「可選 Resend，未設定時僅 log」 |
| **安全性檢查** | 確認 `.env.cloud` 從未 commit（已在 .gitignore）；若有外洩疑慮請在 Resend 後台輪換 API key |

### 高優先項目：可執行與驗證計畫

#### 1. CI Pipeline

**步驟 1.1** 建立 workflow 檔

```
mkdir -p .github/workflows
```

建立 `.github/workflows/ci.yml`，內容：

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: "backend/requirements.txt"
      - run: pip install -r backend/requirements.txt
      - run: cd backend && ruff check .
      - run: cd backend && pytest -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npm run build
```

**驗證 1.1（本地模擬）**

```bash
cd backend && ruff check . && pip install -r requirements.txt && pytest -q
# 預期：ruff 無輸出、pytest 顯示 passed

cd frontend && npm ci && npm run build
# 預期：build 成功，dist/ 目錄產生
```

**驗證 1.2（CI 觸發）**

- 推送到 `main` 或開 PR → GitHub Actions tab 應出現 workflow run
- 任一 job 失敗 → 整個 workflow 標記為 failed

**驗證 1.3（失敗阻擋測試，可選）**

在 `backend/app/__init__.py` 刻意加 `x = 1  # noqa` 違規 → push → CI 應 fail；改回後應 pass

---

#### 2. README 更新

**步驟 2.1** 修改 `README.md`（約 L478–482）

**原文：**
> `POST /api/v1/me/tickets/{ticket_id}/resend` 目前為 email service stub（log），未串第三方郵件供應商。

**改為：**
> `POST /api/v1/me/tickets/{ticket_id}/resend` 由 Resend 寄送；若未設定 `RESEND_API_KEY` 則僅 log，不寄信，不影響報名流程。

**步驟 2.2** 修改 `docs/verification/verification-report.md`

| 行號 | 原文 | 改為 |
|------|------|------|
| 17 | Resend（Stub） | Resend（可選） |
| 21 | Resend Email 目前為 stub（log），未串真實郵件服務 | Resend 為可選；有設定 API key 會寄信，未設定則僅 log |
| 66 | Resend 為 stub \| 未寄真實 Email | Resend 可選；有 key 才寄 |
| 107 | Resend stub | Resend 可選 |

**驗證 2.1**

```bash
rg -n "stub" README.md docs/verification/
# 預期：無與 Resend/email 相關的 stub 描述（或已改為「可選」脈絡）
```

---

#### 3. 安全性檢查

**步驟 3.1** 確認 .gitignore

```bash
git check-ignore -v backend/.env.cloud
# 預期：.gitignore:8:backend/.env.cloud    backend/.env.cloud
```

**步驟 3.2** 檢查 env 是否曾 commit

```bash
git log -p --all -S "RESEND_API_KEY" -- "*.env*" "backend/.env*" "frontend/.env*" 2>/dev/null | head -80
# 預期：無輸出（或僅顯示 .env.example 的 placeholder）
```

```bash
git log --all --oneline -- "backend/.env.cloud" "frontend/.env.cloud"
# 預期：無輸出
```

**步驟 3.3** 檢查硬編碼 key

```bash
rg "re_[a-zA-Z0-9]{24,}" --glob '!*.lock' .
# 預期：無 match
```

**步驟 3.4** 若有外洩疑慮

1. 登入 [Resend Dashboard](https://resend.com/api-keys)
2. 撤銷該 key
3. 建立新 key
4. 更新 `backend/.env` 或 `backend/.env.cloud` 的 `RESEND_API_KEY`
5. 報名一次活動，確認收到信

**驗證 3.4**

```bash
curl -s -X POST .../register  # 或用 UI 報名
# 檢查信箱是否收到 Resend 寄出的信
```

---

### 執行檢查清單（一鍵驗證）

```bash
# 1. CI 本地通過
(cd backend && ruff check . && pytest -q) && (cd frontend && npm run build)
echo "CI 本地驗證: $([ $? -eq 0 ] && echo PASS || echo FAIL)"

# 2. README 無 stub 誤解
! rg "stub.*email|email.*stub" README.md docs/verification/ 2>/dev/null && echo "README stub 檢查: PASS" || echo "README stub 檢查: 請確認"

# 3. env 未 commit
[ -z "$(git log -p --all -S 'RESEND_API_KEY' -- '*.env' '*.env.*' 'backend/.env*' 'frontend/.env*' 2>/dev/null | head -20)" ] && echo "Secrets 檢查: PASS" || echo "Secrets 檢查: 請檢查歷史"
```

### 🟡 中優先（補強穩定性與體感）

| 項目 | 說明 |
|------|------|
| **DynamicForm 表單樣式** | FRONTEND_UI_IMPROVEMENT_PLAN：輸入框改淺色、細 border、focus 明顯；label 至少 text-gray-700 |
| **Rate limit 測試** | 單元測試：超過 limit 時回 429、不同 endpoint 各自 limit 正確 |
| **email_service 測試** | 測試 `_is_resend_available()` 分支、send 失敗時 log 行為 |
| **導航按鈕（零成本）** | 活動頁若已有 `map_url` 或 lat/lng，加「導航」按鈕開 Google Maps；為 note 待辦鋪路 |

### 🟢 低優先（有餘力再做）

| 項目 | 說明 |
|------|------|
| **API 整合測試** | 選 1–2 個關鍵 public endpoint（如 `GET /events`、`POST /register`）做未 mock 整合測試 |
| **錯誤邊界** | 前端 global error boundary，避免白屏；可搭配未來 Sentry |
| **E2E 閉環** | Playwright/Cypress 跑一次完整報名→核銷流程（可放在 MVP2 後） |

## 三、與 MVP2 相關的技術債

| MVP2 功能 | 現有基礎 | 進入前可預先做的事 |
|-----------|----------|---------------------|
| Hold + 逾時 | 無 | 先設計 orders 表、訂單狀態機 schema 草稿 |
| Webhook 冪等 | 無 | 可先建 `webhook_events` 表與 idempotency key 欄位 |
| 金流 | 無 | 研讀 ECPay 文件、設計 payment_attempts / payments 表 |

## 四、執行順序建議

1. **本週**：CI（ruff + pytest + frontend build）
2. **本週**：README Resend 說明修正
3. **下週**：DynamicForm + 活動詳情頁導航按鈕（若有 map_url）
4. **下週**：rate_limit + email_service 單元測試
5. **進入 MVP2 前**：orders / hold 資料模型與 migration 草稿

## 五、文件與結論

- `verification-report.md`：可補充「Resend 為可選」說明
- `FRONTEND_UI_IMPROVEMENT_PLAN`：Phase 1–4 多已完成；表單輸入與 DynamicForm 為剩餘項
- `note.md` 待辦（活動日曆、即時進度、AI 推薦）屬 MVP3+，可不影響 MVP2 時程

**結論**：MVP1 已達進入 MVP2 門檻；最關鍵缺口為 **CI**；其餘可採「邊做 MVP2 邊補」。

---

# **待研究**

- **架構與併發**
  - 分散式系統（distributed systems）
  - 系統設計（system design）
  - 高併發處理（搶票、hold 逾時、冪等、鎖與佇列）

- **部署與上雲（個人 side project 最小化）**
  - 前端：Vercel（Vue/Vite 靜態站，Preview 分支）
  - 後端：選一即可 — Railway / Render / Fly.io（容器或直接跑 Flask）
  - DB/Auth：Supabase Cloud 已算上雲，不需自建
  - 網域與 DNS：Namecheap 買網域 + Cloudflare 或 Vercel 綁定

- **DevOps / 運維（簡單版）**
  - CI：GitHub Actions — 跑 pytest、ruff、前端 build，PR 時自動跑
  - 環境變數：各平台後台填（Vercel / Railway 等），勿 commit secrets
  - 日誌：先 stdout → 用平台內建 log 查；要集中再考慮 Logtail / Axiom（可選）

- **監控與儀表板**
  - 可用性：UptimeRobot — 對 API + 前端 URL 做 HTTP 偵測、故障告警
  - 錯誤：Sentry — 前/後端 exception、source map、release 對應
  - 產品分析（可選）：PostHog — 事件、漏斗、Session 錄影
  - 儀表板：個人專案用 UptimeRobot + Sentry 內建頁面即可；要自建再考慮 Grafana

工具細節與對照見 [Tools.md](./Tools.md)、[develop.md](./develop.md) 推薦套件章節。