# docs/ 全 .md 檔案更新計畫（對齊最新進度）

> 產出：2025-03-19。目標：將所有 docs 內 .md 更新至 MVP-1/2/3 實作完成之最新狀態。

---

## 一、檔案清單（共 37 個 .md）

| # | 路徑 | 更新類型 | 說明 |
|---|------|----------|------|
| 1 | README.md | 結構+入口 | 補 mvp3/、verification 總覽、MVP1-2-3 狀態報告入口 |
| 2 | development/develop.md | 已做 | 階段一覽已更新（前次）；其餘規格為敘述性，保持 |
| 3 | development/note.md | 狀態 | 「與 MVP2 相關的技術債」改為「MVP2 已完成」摘要；Hold/Webhook/金流 改為 ✅ |
| 4 | development/Tools.md | 檢查 | 若有「未實作」等字樣且對應功能已完成則更新 |
| 5 | development/mvp2/README.md | 狀態+連結 | 加「MVP-2 已實作完成」、連結至 verification 報告 |
| 6 | development/mvp2/mvp2-readiness-checklist.md | 狀態 | 3.3 金流改 ✅；結論改為「MVP-2 已完成」 |
| 7 | development/mvp2/mvp2-4-inventory-safety-plan.md | 狀態 | 3.2 防超賣併發測試若有做則標註；現狀盤點已多為 ✅ |
| 8 | development/mvp2/mvp2-5-form-csv-plan.md | 狀態 | 名單匯出 CSV 改為 ✅ 已實作，實作位置註明 |
| 9 | development/mvp2/mvp2-6-refund-plan.md | 狀態 | 現狀盤點：refunds 表、refund_service、DoAction、退款 Email 依實作更新 |
| 10 | development/mvp2/background-tasks-analysis.md | 檢查 | 若結論有「待選」改為「已採用 pg_cron」 |
| 11 | development/mvp3/mvp3-master-plan.md | 檢查 | 1.1 前置已標 MVP-2 ✅；各節驗收若已做則勾選 |
| 12 | development/mvp3/mvp3-2-org-approval-plan.md | 狀態 | 頂部加「已實作」註記與 migration/API 對照 |
| 13 | development/plans/error-boundary-plan.md | 狀態 | 頂部加「已實作」與報告連結 |
| 14 | development/plans/email-service-test-plan.md | 狀態 | 頂部加「已實作」與報告連結 |
| 15 | development/plans/rate-limit-test-plan.md | 狀態 | 頂部加「已實作」與報告連結 |
| 16 | development/plans/navigate-button-plan.md | 狀態 | 頂部加「已實作」與報告連結 |
| 17 | development/plans/api-integration-test-plan.md | 狀態 | 頂部加「已實作」與報告連結 |
| 18 | verification/MVP1-2-3-implementation-status-report.md | 無 | 已為最新總覽報告 |
| 19 | verification/mvp1/mvp1-verification-checklist.md | 無 | 仍為 MVP-1 驗收用，保持 |
| 20 | verification/mvp1/mvp1-manual-verification.md | 無 | 同上 |
| 21 | verification/mvp1/verification-report.md | 無 | 已為完成報告 |
| 22 | verification/mvp2/mvp2-verification-plan.md | 狀態 | 可加「程式已就緒，手動 E2E 待執行」說明 |
| 23 | verification/mvp2/mvp2-verification-report.md | 狀態 | 結論可加「MVP-2 程式與 DB 已全部就緒」一句 |
| 24 | verification/mvp3/mvp3-verification-checklist.md | 狀態 | 六、驗收完成條件總表：可標註「程式與單測已通過，手動項待執行」 |
| 25 | verification/mvp3/mvp3.5-verification-report.md | 無 | 已為完成報告 |
| 26 | verification/reports/api-integration-test-report.md | 無 | 報告類，保持 |
| 27 | verification/reports/email-service-test-report.md | 無 | 同上 |
| 28 | verification/reports/rate-limit-test-report.md | 無 | 同上 |
| 29 | verification/reports/error-boundary-report.md | 無 | 同上 |
| 30 | verification/reports/navigate-button-report.md | 無 | 同上 |
| 31 | setup/local-cloud-switch.md | 檢查 | 若提到 migrations 數量可註「含 MVP-2/3」 |
| 32 | setup/local-supabase-reference.md | 檢查 | 無狀態則不更動 |
| 33 | old/AGENTS.md | 聲明 | 頂部加「歷史文件；MVP 階段狀態以 develop.md 為準」 |
| 34 | old/note.md | 聲明 | 頂部加「舊版筆記，以 development/note.md 為主」 |
| 35 | design/CYPHER_REDESIGN_V2.md | 檢查 | 若無 MVP 狀態則不更動 |
| 36 | design/FRONTEND_UI_IMPROVEMENT_PLAN.md | 檢查 | 同上 |
| 37 | design/UI_UX_OPTIMIZATION_PLAN.md | 檢查 | 同上 |

---

## 二、執行順序

1. **README.md** — 目錄結構、verification 區塊、常用入口（含 MVP1-2-3 報告）。
2. **development/note.md** — MVP2 技術債改為完成摘要。
3. **development/mvp2/** — README、readiness、mvp2-4/5/6、background-tasks 狀態。
4. **development/mvp3/** — mvp3-master-plan 驗收勾選、mvp3-2 頂部註記。
5. **development/plans/** — 五個 plan 頂部加「已實作」與報告連結。
6. **verification/** — mvp2 plan/report、mvp3 checklist 狀態說明。
7. **old/** — AGENTS.md、note.md 頂部聲明。
8. **setup/**、**design/**、**Tools.md** — 僅必要小改。

---

## 三、不更動原則

- 規格類內容（develop.md 規格章節、API 列表、DB 設計）維持不變，僅狀態/勾選/結論更新。
- 報告類（reports/*.md、verification-report.md、mvp3.5-verification-report.md）維持原樣。
- 手動驗證清單（mvp1-verification-checklist、mvp1-manual-verification、mvp3-verification-checklist）保留為「執行用」清單，僅可加一句總體狀態說明。

---

## 四、執行紀錄

- **2025-03-19**：依本計畫完成全 docs .md 更新。已更新：README.md（目錄、mvp3、verification 總覽、常用入口）、note.md（MVP2 技術債→完成摘要）、mvp2/*（README、readiness、2-4/2-5/2-6、background-tasks）、mvp3/mvp3-2-org-approval-plan、plans/*（五個 plan 頂部已實作+報告連結）、verification（mvp2 plan/report、mvp3 checklist）、old/AGENTS.md 與 old/note.md（頂部聲明）、Tools.md（Stripe/ECPay 對照）。
