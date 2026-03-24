# CypherHub 文件說明

`docs/` 依用途分為七類：**API 文件**、**環境設定**、**開發規格**、**設計參考**、**部署與 CI/CD**、**驗證與 QA**、**歸檔**。

---

## 目錄結構

```
docs/
├── README.md                # 本說明
├── api/                     # API 文件
│   ├── endpoints.md         # REST API 端點總表（38 端點）
│   ├── authentication.md    # 認證與權限機制
│   └── error-codes.md       # Error code 對照表（60+ codes）
├── setup/                   # 環境設定
│   ├── local-cloud-switch.md
│   └── local-supabase-reference.md
├── development/             # 開發規格（仍活躍）
│   ├── develop.md           # 主規格（必讀）
│   ├── Tools.md             # 工具選單
│   ├── database-schema.md   # DB Schema 總覽（19 表 + 10 RPC）
│   └── environment-variables.md # 環境變數完整清單（⬜ 待撰寫）
├── design/                  # 設計參考
│   └── design-reference.md  # V2 改版 + UI/UX 優化（合併版）
├── deployment/              # 部署與 CI/CD（⬜ 待撰寫）
│   ├── deploy-guide.md      # 部署流程
│   └── ci-cd.md             # GitHub Actions CI/CD
├── verification/            # 驗證與 QA
│   ├── master-plan.md       # MVP-1/2/3 主驗證計畫（AI 可重複執行）
│   ├── acceptance-checklist.md  # 最新完整驗收清單（397 項）
│   ├── implementation-status.md # MVP-1/2/3 實作狀態總覽
│   ├── mvp1-verification.md # MVP-1 手動清單 + 邏輯驗證（合併版）
│   ├── mvp2-verification.md # MVP-2 驗證計畫 + 報告（合併版）
│   ├── mvp3-verification.md # MVP-3 測試清單 + 報告（合併版）
│   └── reports/             # 功能驗證報告
│       ├── api-integration-test-report.md
│       ├── email-service-test-report.md
│       ├── rate-limit-test-report.md
│       ├── error-boundary-report.md
│       └── navigate-button-report.md
└── archive/                 # 歸檔（已完成/已取代）
    ├── README.md
    ├── old/                 # 舊版文件（AGENTS.md、ChatGPT 整理等）
    ├── mvp2-dev/            # MVP-2 已完成開發計畫
    ├── mvp3-dev/            # MVP-3 已完成開發計畫
    ├── feature-plans/       # 已完成功能計畫
    ├── verification/        # 合併前的驗證原始檔
    └── ...                  # 其他已執行的一次性計畫
```

---

## api/ — API 文件

| 檔案 | 應撰寫內容 | 讀者 |
|------|------------|------|
| [endpoints.md](api/endpoints.md) | 38 個 REST API 端點，依 12 個 blueprint 分組，含 HTTP method、路徑、請求/回應範例、分頁參數、權限需求 | 人 + AI |
| [authentication.md](api/authentication.md) | 認證流程說明：Supabase Auth JWT、Bearer token、`@require_auth`、Token refresh、四層權限模型 | 人 + AI |
| [error-codes.md](api/error-codes.md) | 60+ 個 `AppError` error code 對照表（code → HTTP status → 中英文訊息 → 觸發場景），含前端 `errorMessages.ts` 映射 | 人 + AI |

---

## setup/ — 環境設定

| 檔案 | 說明 |
|------|------|
| [local-cloud-switch.md](setup/local-cloud-switch.md) | 本地 / 雲端 Supabase 切換指南 |
| [local-supabase-reference.md](setup/local-supabase-reference.md) | 本地 `supabase start` 後的端點速查 |

---

## development/ — 開發規格

| 檔案 | 說明 | 讀者 |
|------|------|------|
| [develop.md](development/develop.md) | 開發路線圖、規格主檔（MVP-1~3、SEC、API、DB） | 人 + AI |
| [Tools.md](development/Tools.md) | 工具選單（Vercel、Sentry、Resend 等） | 人 |
| [database-schema.md](development/database-schema.md) | 19 張表 + 10 個 RPC + 8 個 enum：所有欄位定義、FK、RLS 策略、Check Constraints、索引、pg_cron 排程。依 migration（0001-0027）整理 | 人 + AI |
| [environment-variables.md](development/environment-variables.md) | 所有環境變數完整清單（backend + frontend），含變數名、用途、必填/選填、預設值、範例值。標註哪些是 secret（不可洩露）、哪些在本地/雲端不同。取代散落在 `.env.example` 和 `CLAUDE.md` 的片段資訊 | 人 + AI |

---

## design/ — 設計參考

| 檔案 | 說明 |
|------|------|
| [design-reference.md](design/design-reference.md) | V2 深色改版 + UI 改善 + UX 無障礙優化（全部已完成） |

---

## verification/ — 驗證與 QA

### 總覽（給 AI 或團隊負責人）

| 檔案 | 說明 | 讀者 |
|------|------|------|
| [master-plan.md](verification/master-plan.md) | MVP-1/2/3 主驗證計畫（Phase 0~6，可重複執行） | AI |
| [acceptance-checklist.md](verification/acceptance-checklist.md) | 最新最完整驗收清單（Phase 0~4，含逐項 API 驗證） | 人 + AI |
| [implementation-status.md](verification/implementation-status.md) | MVP-1/2/3 實作狀態總覽報告 | 人 |

### MVP 驗證（手動 + 報告合併版）

| 檔案 | 說明 | 類型 |
|------|------|------|
| [mvp1-verification.md](verification/mvp1-verification.md) | MVP-1 手動清單 + 邏輯驗證 + 平台對照 | 手動 |
| [mvp2-verification.md](verification/mvp2-verification.md) | MVP-2 驗證計畫 + 報告（綠界 E2E 重點） | 手動 + 自動 |
| [mvp3-verification.md](verification/mvp3-verification.md) | MVP-3 測試清單 + MVP-3.5 報告 | 手動 + 自動 |

### 功能驗證報告

| 檔案 | 驗證內容 |
|------|----------|
| [api-integration-test-report.md](verification/reports/api-integration-test-report.md) | GET /events、POST /register 無 mock 整合測試 |
| [email-service-test-report.md](verification/reports/email-service-test-report.md) | email_service 單元測試（9 passed） |
| [rate-limit-test-report.md](verification/reports/rate-limit-test-report.md) | Rate limiting 429 驗證 |
| [error-boundary-report.md](verification/reports/error-boundary-report.md) | 前端 Error boundary |
| [navigate-button-report.md](verification/reports/navigate-button-report.md) | 活動「導航」按鈕 |

---

## deployment/ — 部署與 CI/CD

| 檔案 | 應撰寫內容 | 讀者 |
|------|------------|------|
| [deploy-guide.md](deployment/deploy-guide.md) | 完整部署流程：Vercel（前端）部署設定、Backend 部署方式（Docker / Cloud Run / 其他）、Supabase 雲端設定（`supabase db push`、Storage bucket、Auth 設定）、DNS / 自訂域名、環境變數配置、首次部署 vs 更新部署的差異 | 人 |
| [ci-cd.md](deployment/ci-cd.md) | GitHub Actions workflow 說明：觸發條件、各 job 做什麼（lint、test、build、deploy）、branch 策略（main / staging）、secrets 設定、手動 deploy 方式、rollback 流程 | 人 + AI |

---

## archive/ — 歸檔

已完成或被取代的文件，保留作歷史參考。詳見 [archive/README.md](archive/README.md)。

---

## 常用入口

- **第一次架環境** → [setup/local-cloud-switch.md](setup/local-cloud-switch.md)
- **看規格與路線圖** → [development/develop.md](development/develop.md)
- **查 API 端點** → [api/endpoints.md](api/endpoints.md)
- **查 Error Code** → [api/error-codes.md](api/error-codes.md)
- **查 DB Schema** → [development/database-schema.md](development/database-schema.md)
- **部署上線** → [deployment/deploy-guide.md](deployment/deploy-guide.md)（⬜ 待撰寫）
- **MVP-1/2/3 驗證（AI 用）** → [verification/master-plan.md](verification/master-plan.md)
- **最新驗收清單** → [verification/acceptance-checklist.md](verification/acceptance-checklist.md)
- **實作狀態總覽** → [verification/implementation-status.md](verification/implementation-status.md)
- **ECPay 金流 Skill** → [.claude/skills/ecpay/](.claude/skills/ecpay/)
