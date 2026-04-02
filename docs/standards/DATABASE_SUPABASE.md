# Database: Supabase & PostgreSQL Standards

## 1. 資料庫結構設計 (Schema Design)
- **命名規範**：
  - 表名：蛇形命名、複數名詞 (如 `users`, `events`, `orders`)。
  - 欄位名：蛇形命名 (如 `created_at`, `ticket_type_id`)。
- **關聯性與約束**：
  - 必須建立 Foreign Keys 確保資料完整性。
  - 建立適當的 Indexes 以加速查詢，尤其是 Foreign Keys 欄位與常被 WHERE 篩選的欄位。
- **時間戳記**：所有表應包含 `created_at` 與 `updated_at` (並使用 Trigger 自動更新 `updated_at`)。

## 2. 行級安全 (Row Level Security - RLS)
- **預設拒絕**：所有新建的表都必須啟用 RLS (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`)。
- **明確策略 (Explicit Policies)**：為 `SELECT`, `INSERT`, `UPDATE`, `DELETE` 分別定義明確的策略。
- **最小權限原則**：使用者只能存取自己擁有的資源，或公開的資源。
- **性能考量**：RLS 策略中的查詢應盡量簡單，避免在 Policy 中使用複雜的 JOIN 導致嚴重的效能問題。必要時考慮使用 Security Definer Functions 作為輔助。

## 3. RPC 與資料庫邏輯 (Stored Procedures)
- **何時使用 RPC**：適用於需要保證原子性 (Atomicity)、大量資料批次更新、或高頻發生的複雜交易 (例如：扣減票券庫存、建立訂單)，以減少 Application 與 Database 之間的網路來回 (Network Roundtrips)。
- **權限控制**：明確定義 RPC 的 `SECURITY INVOKER` (預設，使用調用者的權限) 或 `SECURITY DEFINER` (使用建立者的權限，需極度謹慎處理權限提升風險)。
- **參數驗證**：即便後端已做驗證，RPC 內部仍應進行基本的輸入驗證與防呆。

## 4. 遷移管理 (Migrations)
- 所有的資料庫變更 (Schema, Policies, RPCs) 都必須透過 Supabase Migrations (`.sql` 文件) 進行版本控制，嚴禁手動在 Production Dashboard 修改。
- Migration 腳本應具有冪等性 (Idempotency) 或設計為不可變的版本推進。