# CypherHub 文件說明

`docs/` 依用途分成三類：**環境設定**、**開發規格**、**驗證與 QA**。另有一目錄 **old** 存放舊版文件。

---

## 目錄結構

```
docs/
├── README.md           # 本說明
├── setup/              # 環境與 Supabase 設定
├── development/        # 開發路線、規格、工具
├── verification/       # 驗證清單與報告
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

| 檔案 | 說明 |
|------|------|
| **develop.md** | 開發路線圖與規格主檔。階段一覽（MVP-1～MVP-3、SEC）、開發環境指令、推薦套件與 Tools 對照、未實作功能與替代方案、MVP-1 詳細規格（1.0～1.5）、RBAC、API/DB 規範、Non-Goals。 |
| **note.md** | 待研究與規劃筆記：架構與併發、部署上雲、DevOps、監控與儀表板等；附連結到 Tools.md / develop.md。 |
| **Tools.md** | 工具選單：Vercel、Stripe、Resend、Sentry、Cloudflare 等用途說明，以及與 CypherHub MVP-1 / MVP-2+ 的對照。 |

---

## verification/ — 驗證與 QA

| 檔案 | 說明 |
|------|------|
| **mvp1-verification-checklist.md** | MVP-1 手動驗證勾選清單。對應 develop.md 規格，從環境準備到註冊登入、活動列表、報名、票券、主辦、核銷、Admin 等，逐項勾選 `[ ]` → `[x]` 完成驗收。 |
| **mvp1-manual-verification.md** | MVP-1 完整手動驗證「步驟說明」版。同一套流程，以表格列出每步操作與預期結果，適合照著做一遍。 |
| **verification-report.md** | 功能驗證報告。與 Accupass / KKTIX / Eventbrite 等購票平台流程對照表、register_free_v2 業務邏輯驗證、API 與前端對照，確認 MVP-1 一致性與正確性。 |

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
- **跑 MVP-1 驗收** → [verification/mvp1-verification-checklist.md](verification/mvp1-verification-checklist.md) 或 [verification/mvp1-manual-verification.md](verification/mvp1-manual-verification.md)
