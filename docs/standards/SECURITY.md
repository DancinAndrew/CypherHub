# Security Standards

## 1. API 與後端安全
- **身分驗證 (Authentication)**：
  - 驗證 JWT 簽章，檢查 Token 是否過期。
  - 敏感操作需二次驗證或檢查用戶角色 (Role-Based Access Control)。
- **輸入驗證與過濾**：
  - 絕不信任前端傳來的資料。所有 Input 都必須經過 Pydantic 嚴格的類型與邊界驗證。
  - 防止 SQL Injection (Supabase/PostgreSQL 預設透過 Parameterized Queries 防範，但需注意動態組裝的 SQL 或 RPC 內部邏輯)。
- **CORS (跨來源資源共用)**：
  - 嚴格限制 `Access-Control-Allow-Origin`，不允許 `*`，僅開放已知的前端網域。

## 2. 第三方服務與 Webhook 安全
- **金流串接 (ECPay)**：
  - 嚴格驗證 Webhook 的 `CheckMacValue` (SHA-256)，確保回傳資料未遭篡改。
  - 處理 Webhook 時須具備冪等性 (Idempotency)，防止金流服務重複發送通知導致重複結帳。
  - 不依賴前端的付款成功回調進行訂單狀態更新，必須以後端接收到的伺服器對伺服器 (S2S) Webhook 為準。

## 3. 基礎設施與敏感配置
- **環境變數與機密管理**：
  - `.env` 文件絕對不可進入版控 (`.gitignore`)。
  - 所有 API Keys, Database URLs, JWT Secrets 必須透過環境變數注入。
- **Rate Limiting (限流)**：
  - 針對登入、註冊、發送驗證碼等高風險 API 實作限流，防止暴力破解與 DDoS 攻擊。
- **安全標頭 (Security Headers)**：
  - 確保 API 與前端伺服器回傳適當的 HTTP Security Headers (如 `Content-Security-Policy`, `X-Content-Type-Options`, `Strict-Transport-Security`)。