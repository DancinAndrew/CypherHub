# CypherHub 文件說明

`docs/` 依用途分成三類：**環境設定**、**開發規格**、**驗證與 QA**。另有一目錄 **old** 存放舊版文件。

---

## 技術棧與依賴

技術棧與套件版本見根目錄 [README.md#技術棧與套件](../README.md#技術棧與套件)。  
Backend 需 **Python 3.12+**，Frontend 為 Vue 3 + Vite + TypeScript。

---

## 目錄結構

```
docs/
├── README.md           # 本說明
├── setup/              # 環境與 Supabase 設定
├── development/        # 開發路線、規格、工具
│   ├── develop.md      # 主規格（必讀）
│   ├── note.md
│   ├── Tools.md
│   ├── plans/          # 實作計畫（測試、功能）
│   └── mvp2/           # MVP-2 開發（就緒檢查、金流 best practices、背景任務）
├── verification/       # 驗證與 QA
│   ├── mvp1/           # MVP-1 主體驗收
│   └── reports/        # 功能驗證報告
└── old/                # 舊版／備考
```

---

## setup/ — 環境與設定

| 檔案 | 說明 |
|------|------|
| **local-cloud-switch.md** | 本地 / 雲端 Supabase 切換指南。何時用本地、何時用雲端、`use-local-supabase.sh` 與 `use-cloud-supabase.sh` 流程、注意事項（migrations 分別套用、雲端 pause 等）。 |
| **local-supabase-reference.md** | 本地 `supabase start` 後的固定端點速查：Studio、Mailpit、API URL、DB 連線字串、取得 ANON_KEY / SERVICE_ROLE_KEY 方式。 |

---

## development/ — 開發規格與參考

### 核心

| 檔案 | 說明 |
|------|------|
| **develop.md** | 開發路線圖與規格主檔。階段一覽（MVP-1～MVP-3、SEC）、開發環境指令、推薦套件與 Tools 對照、MVP 詳細規格、RBAC、API/DB 規範、Non-Goals。 |
| **note.md** | 待研究與規劃筆記：架構與併發、部署上雲、DevOps、監控與儀表板等。 |
| **Tools.md** | 工具選單：Vercel、Stripe、Resend、Sentry、Cloudflare 等用途說明，以及與 CypherHub MVP 的對照。 |

### plans/ — 實作計畫

各功能與測試的計畫與實作紀錄。

| 檔案 | 說明 |
|------|------|
| **api-integration-test-plan.md** | API 整合測試計畫。 |
| **email-service-test-plan.md** | email_service 單元測試計畫。 |
| **rate-limit-test-plan.md** | Rate limit 測試計畫與實作紀錄。 |
| **error-boundary-plan.md** | 前端 Error boundary 實作計畫。 |
| **navigate-button-plan.md** | 活動頁導航按鈕計畫。 |

### mvp2/ — MVP-2 開發（訂單、金流、背景任務）

| 檔案 | 說明 |
|------|------|
| **mvp2-readiness-checklist.md** | 進入 MVP-2 前的檢查清單。 |
| **payment-best-practices.md** | **金流開發必讀**。ECPay 驗簽、Form 參數、Webhook 冪等、provider 介面、安全檢查清單。 |
| **background-tasks-analysis.md** | 背景任務選型分析（RQ、Celery、pg_cron）。 |

---

## verification/ — 驗證與 QA

### mvp1/ — MVP-1 主體驗收

| 檔案 | 說明 |
|------|------|
| **mvp1-verification-checklist.md** | MVP-1 手動驗證勾選清單。對應 develop.md 規格，從環境準備到註冊登入、活動列表、報名、票券、主辦、核銷、Admin 等，逐項勾選完成驗收。 |
| **mvp1-manual-verification.md** | MVP-1 完整手動驗證「步驟說明」版。同一套流程，以表格列出每步操作與預期結果，適合照著做一遍。 |
| **verification-report.md** | 功能驗證報告。與 Accupass / KKTIX / Eventbrite 等購票平台流程對照表、register_free_v2 業務邏輯驗證、API 與前端對照。 |

### reports/ — 功能驗證報告

各功能實作後的驗證報告。

| 檔案 | 說明 |
|------|------|
| **api-integration-test-report.md** | API 整合測試驗證。GET /events、POST /register 無 mock 直連 Supabase。 |
| **email-service-test-report.md** | email_service 單元測試驗證。 |
| **rate-limit-test-report.md** | Rate limit 實作驗證。429、auth 10/min、register 20/min、checkin 60/min。 |
| **error-boundary-report.md** | 前端 Error boundary 驗證。 |
| **navigate-button-report.md** | 活動詳情「導航」按鈕驗證。 |

---

## old/ — 舊版／備考

| 檔案 | 說明 |
|------|------|
| **AGENTS.md** | 舊版專案規範與 API 總覽，已由根目錄 AGENTS.md 與 docs/development/develop.md 取代，保留作參考。 |
| **note.md** | 舊版筆記，現以 development/note.md 為主。 |

---

## 常用入口

- **第一次架環境、切本地/雲端** → [setup/local-cloud-switch.md](setup/local-cloud-switch.md)、[setup/local-supabase-reference.md](setup/local-supabase-reference.md)
- **看階段規劃、規格、推薦套件** → [development/develop.md](development/develop.md)、[development/Tools.md](development/Tools.md)
- **跑 MVP-1 驗收** → [verification/mvp1/mvp1-verification-checklist.md](verification/mvp1/mvp1-verification-checklist.md) 或 [verification/mvp1/mvp1-manual-verification.md](verification/mvp1/mvp1-manual-verification.md)
- **MVP-2 開發** → [development/mvp2/](development/mvp2/)（就緒檢查、金流 best practices、背景任務分析）
