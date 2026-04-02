# Backend: Flask & Python Standards

## 1. Python 最佳實踐
- **型別提示 (Type Hints)**：強制在所有函數、方法與類別使用 Type Hints (Python 3.12+)。提升代碼可讀性與靜態分析 (如 Mypy) 的準確度。
- **Pydantic v2 驗證**：使用 Pydantic 進行所有傳入資料 (Request Body, Query Params) 與傳出資料 (Response) 的結構定義與驗證。
- **現代 Python 特性**：適當使用 `match-case` (Pattern Matching), F-strings, 列表推導式 (List Comprehensions) 等現代特性。

## 2. Flask 框架規範
- **Application Factory Pattern**：使用 `create_app()` 工廠模式建立 Flask 實例，便於測試與避免全域狀態。
- **依賴注入與全域變數**：避免使用 `g` 對象來傳遞複雜狀態。避免模組級別的全局變數，以防止並發請求間的狀態污染。
- **上下文管理**：正確處理 App Context 與 Request Context。在背景任務或離線腳本中需手動推送 App Context。

## 3. 效能與併發 (Performance & Concurrency)
- **Gunicorn WSGI 配置**：生產環境應使用適當數量的 Worker (通常為 `2 * CPU cores + 1`)，以及適當的 Threading 或 Async Worker (如 Gevent) 視 I/O 密集度而定。
- **連接池 (Connection Pooling)**：與資料庫或 Supabase 溝通時，確保使用連接池並合理設定 Timeout 與 Pool Size，避免資源耗盡。

## 4. 日誌與監控 (Logging)
- **結構化日誌 (Structured Logging)**：日誌應以 JSON 格式輸出，包含 `timestamp`, `level`, `trace_id`, `user_id` 等上下文資訊。
- **日誌級別**：
  - `ERROR`: 系統發生錯誤且無法自動恢復。
  - `WARNING`: 潛在問題或可容忍的異常 (如用戶輸入錯誤導致的 API 拒絕)。
  - `INFO`: 重要的系統狀態改變 (如訂單建立、付款成功)。
  - `DEBUG`: 僅在開發或排查問題時開啟，包含詳細變數狀態。
- **敏感資訊遮蔽**：日誌中絕對不可包含密碼、Token、信用卡號等 PII (個人可識別資訊)。