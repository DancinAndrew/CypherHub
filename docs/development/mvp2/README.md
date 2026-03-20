# MVP-2 開發文件

> 訂單、金流、背景任務等 MVP-2 相關開發必讀文件，全部集中於此。  
> **狀態**：MVP-2 已實作完成（2025-03）。程式、migrations、單元測試就緒；綠界 E2E、Hold 逾時等需手動驗證。

| 檔案 | 說明 |
|------|------|
| [mvp2-readiness-checklist.md](./mvp2-readiness-checklist.md) | 進入 MVP-2 前的檢查清單（已完成，可作參考） |
| [.cursor/skills/ecpay](../../../.cursor/skills/ecpay) | **金流開發必讀** — ECPay 官方 Skill，AIO、CheckMacValue、Webhook |
| [background-tasks-analysis.md](./background-tasks-analysis.md) | 背景任務選型分析（已採用 pg_cron + SQL RPC） |
| [mvp2-4-inventory-safety-plan.md](./mvp2-4-inventory-safety-plan.md) | 庫存安全與背景任務（已實作） |
| [mvp2-5-form-csv-plan.md](./mvp2-5-form-csv-plan.md) | 報名表單擴充與名單匯出 CSV（已實作） |
| [mvp2-6-refund-plan.md](./mvp2-6-refund-plan.md) | 基礎退款（已實作） |

**驗證**：[mvp2-verification-report.md](../../verification/mvp2/mvp2-verification-report.md)、[MVP1-2-3-implementation-status-report.md](../../verification/MVP1-2-3-implementation-status-report.md)

**上層**：[develop.md](../develop.md)（主規格）、[note.md](../note.md)
