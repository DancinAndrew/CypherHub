# CypherHub 程式碼庫大稽核與重構總結報告 (Codebase Audit & Refactor Summary)

這份文件記錄了由 AI 助手 (Gemini CLI) 針對 CypherHub 專案所進行的全面性架構稽核與程式碼重構過程。您可以將此文件提供給其他 AI 助手（例如 Claude Code）作為上下文參考，以了解目前專案的最新架構狀態與標準。

## 階段一：建立資深工程師開發標準

我們首先在 `docs/standards/` 目錄下建立了 5 份嚴格的開發標準文件，作為整個 codebase 的防呆與審查基準：

1. **`ARCHITECTURE_CLEAN_CODE.md`**：架構與整潔程式碼標準（SOLID 原則、分層架構、錯誤處理與命名規範）。
2. **`BACKEND_FLASK_PYTHON.md`**：後端 Python 與 Flask 標準（Pydantic 驗證、工廠模式、效能與結構化日誌）。
3. **`FRONTEND_VUE_TS.md`**：前端 Vue 3 與 TypeScript 標準（Composition API、Pinia 狀態管理、組件設計與 Tailwind 規範）。
4. **`DATABASE_SUPABASE.md`**：資料庫與 Supabase 標準（Schema 設計、RLS 行級安全策略、RPC 權限與 Migration 控制）。
5. **`SECURITY.md`**：安全規範（JWT 驗證、Webhook 金流安全、CORS 與限流策略）。

---

## 階段二：依據標準進行程式碼庫深度檢查與修復

針對上述 5 份標準，我們進行了深度的程式碼檢查，並立即實作了重構與修復：

### 1. 架構與整潔程式碼 (ARCHITECTURE_CLEAN_CODE)
- **發現問題**：
  - **分層越界**：Blueprint (`auth.py`) 直接呼叫了 Supabase Auth API，違反 Controller 不包含業務邏輯的原則。
  - **分層越界**：Service 層 (`auth_service.py`) 內的裝飾器直接依賴了 Flask 的 `request` 和 `g` 物件。
  - **不良例外處理**：`events_service.py` 中存在多處 `except Exception: pass` 吞沒錯誤的情況。
- **修復行動**：
  - 將登入邏輯從 Blueprint 抽離，在 `auth_service.py` 建立 `AuthService.login_with_password()`。
  - 將依賴 HTTP Request 的 `@require_auth` 裝飾器搬移到中介層 `blueprints/_utils.py`。
  - 全面替換 `except Exception:` 為 `except Exception as exc:`，並補上 `current_app.logger.warning(f"Error: {exc}")` 確保錯誤可追蹤。

### 2. 後端 Python 與 Flask (BACKEND_FLASK_PYTHON)
- **發現問題**：缺乏可觀測性的結構化日誌、Gunicorn 啟動參數寫死且未配置 threads（不利於 I/O 密集型應用）、呼叫外部 API 時缺乏 HTTP 連接池。
- **修復行動**：
  - **JSON 結構化日誌**：新增 `app/logger.py`，覆寫 Flask Formatter，並透過 `@app.before_request` 為每個請求注入唯一的 `trace_id`。
  - **Gunicorn 效能優化**：建立 `gunicorn.conf.py`，依據 `CPU cores * 2 + 1` 動態分配 workers，並開啟 `--threads 4` (gthread 模式) 避免 Supabase API 阻塞。
  - **HTTP 連接池**：在 `supabase_client.py` 內導入 `httpx.Client()` 取代效能低下的 `urllib.request`，實現 TCP 連線複用 (Keep-Alive)。

### 3. 安全防護 (SECURITY)
- **檢查結果**：表現極佳，無須額外修補。
- **亮點**：
  - ECPay Webhook 簽章 (CheckMacValue) 邏輯嚴謹。
  - JWT 身分驗證與 Role-Based Access Control (RBAC) 落實徹底。
  - CORS 白名單與 HTTP 安全標頭 (Security Headers) 具備生產環境防呆機制。

### 4. 前端 Vue 3 與 TypeScript (FRONTEND_VUE_TS)
- **發現問題**：部分 Pinia Store 仍使用舊版 Options API 風格；Vue Router 的頁面元件全部採用同步載入，影響首頁 Bundle Size。
- **修復行動**：
  - **Pinia Setup Syntax**：將 `stores/error.ts` 重構為 Vue 3 官方建議的 Composition API 風格（返回 refs 與 functions）。
  - **Vue Router Lazy Loading**：將 `router/index.ts` 內除了 Home 與 Login 以外的所有頁面替換為動態導入 (`() => import(...)`)，優化首次加載效能。編譯測試 (`npm run build`) 確認無誤且體積減小。

### 5. 資料庫與 Supabase (DATABASE_SUPABASE)
- **發現問題**：部分資料表忘記啟用 RLS 或漏掉 `updated_at` 自動更新機制。
- **修復行動**：
  - 產生並執行了第 29 號遷移檔 (`0029_fix_db_standards.sql`)。
  - 為 `audit_logs` 強制啟用 RLS (Row Level Security)。
  - 為 `event_stages`, `event_progress` 補上 `BEFORE UPDATE` Trigger 以自動更新 `updated_at`。
  - 為 `settlements` 與 `payout_requests` 補齊缺失的 `updated_at` 欄位與 Trigger。

---

## 階段三：自動化測試修復與品質確保

在上述大幅度重構後，我們運行了後端測試並進行了二次修復，確保系統不會因為重構而發生 Regression：

- **Pytest 單元與整合測試修復**：
  - 因 `_supabase_token` 從 `auth_bp` 移動至 `auth_service`，我們更新了 `test_auth_login.py` 與 `test_rate_limit.py` 中的所有 Mock (monkeypatch) 路徑。
  - 修正了測試環境中的 `FLASK_DEBUG=1` 干擾，確保 `test_sec4_deployment.py` 和 `test_security_headers.py` 能精確模擬生產環境 (`FLASK_DEBUG=False`)，使其順利通過 SEC-4 的防呆檢查。
- **Linter 修復**：
  - 執行 `ruff check --fix .`，自動整理並移除了所有後端 Python 檔案中因重構產生的無效 Imports 與排版問題。
- **最終測試結果**：
  - 後端 `pytest`：174 項測試全數通過 (174 passed)。
  - 前端 `npm run build`：Vue-TSC 型別檢查與 Vite 打包皆順利完成，無任何 any 污染。