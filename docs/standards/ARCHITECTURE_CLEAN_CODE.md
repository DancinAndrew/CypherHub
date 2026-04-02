# Architecture & Clean Code Standards

## 1. 核心設計原則 (Core Design Principles)
- **遵循 SOLID 原則**：尤其是單一職責原則 (SRP) 與依賴反轉原則 (DIP)。
- **DRY (Don't Repeat Yourself)**：減少重複代碼，將共用邏輯抽象為輔助函數或服務。
- **KISS (Keep It Simple, Stupid)**：避免過度設計，優先選擇簡單易懂的解決方案。
- **高內聚，低耦合**：模組內部應該高度相關，模組之間的依賴應該盡可能少。

## 2. 分層架構 (Layered Architecture)
CypherHub 後端應該嚴格遵守分層架構，確保各層職責分離：
- **Blueprints/Controllers 層 (API 層)**：
  - 僅負責處理 HTTP 請求與響應。
  - 解析參數、調用 Service 層、返回格式化的 JSON 與適當的 HTTP 狀態碼。
  - 絕對不包含業務邏輯或直接的資料庫查詢。
- **Service 層 (業務邏輯層)**：
  - 包含應用程式的核心業務邏輯。
  - 協調多個 Domain 實體、處理交易(Transaction)邊界。
  - 不依賴 Flask request/response 對象，保持純粹的 Python 邏輯以便於單元測試。
- **Domain/Models 層 (領域層)**：
  - 定義資料結構、Schema (如 Pydantic models)、狀態機 (State Machines)。
  - 包含與業務實體直接相關的核心規則。
- **Providers/Utils 層 (外部服務與基礎設施層)**：
  - 封裝第三方 API (如 ECPay)、Email 發送器、Supabase 客戶端等。

## 3. 命名規範 (Naming Conventions)
- **變數與函數**：`snake_case`，名稱應具備描述性。避免使用單字母變數 (除了迴圈計數器 `i`, `j`)。
- **類別與異常**：`PascalCase` (例如 `OrderService`, `PaymentFailedError`)。
- **常數**：`UPPER_SNAKE_CASE` (例如 `MAX_RETRY_COUNT`)。
- **布林變數**：應使用 `is_`, `has_`, `can_` 等前綴 (例如 `is_active`, `has_ticket`)。

## 4. 錯誤處理 (Error Handling)
- **自定義異常**：定義應用程式專屬的例外類別 (繼承自 `Exception` 或特定基礎類別)，例如 `DomainError`, `ResourceNotFoundError`。
- **統一例外處理**：在 Blueprint 層或 Flask 全局錯誤處理器中捕捉異常，並轉換為標準化的 API 錯誤響應格式。
- **避免空的 except**：絕不使用 `except Exception: pass`，必須明確指定捕捉的異常類型並記錄日誌。