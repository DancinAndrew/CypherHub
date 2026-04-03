# SEC-4：Secrets 與部署檢查（環境變數、錯誤、日誌）

> **階段**：SEC-4（上線前安全強化 — 最終項目）
> **狀態**：✅ 已完成
> **前置條件**：SEC-1 ✅、SEC-2 ✅、SEC-3 ✅
> **參考規格**：[develop.md — SEC-4](develop.md#sec-4secrets-與部署檢查-)

---

## 一、目標與範圍

### 目標

確保所有機敏資料（Secrets）不會進入 Git、API 錯誤回應、或日誌輸出。生產部署配置安全、不暴露偵錯資訊。

### Done 條件（來自 develop.md）

> 無 secret 寫入程式碼或 Git；生產錯誤訊息不洩漏內部資訊；log 不含敏感資料。

### 範圍內（In Scope）

| # | 項目 | 說明 |
|---|------|------|
| 1 | Secrets 不進 Git | `.env*` 在 `.gitignore`、無硬編碼 secrets、`.env.example` 僅 placeholder |
| 2 | SERVICE_ROLE_KEY 隔離 | 僅 server-side 使用，前端 bundle / API response / log 無洩露 |
| 3 | 錯誤訊息安全 | 500 不回傳 stack trace / SQL / 路徑；`details.raw` 生產環境不外洩 |
| 4 | 日誌安全 | `app.logger` 不記錄密碼、完整 token、信用卡號 |
| 5 | Dockerfile 生產安全 | 不硬編碼 `--debug`；生產使用 gunicorn |
| 6 | 部署前檢查清單 | 環境變數完整性、安全 header、FLASK_DEBUG=0 確認 |

### 範圍外（Out of Scope）

- Secret 管理平台（AWS Secrets Manager / Vault）→ 未來 infra 優化
- 第三方 log 服務整合（Sentry / CloudWatch）→ 未來 infra 優化
- CDN / WAF 設定 → 屬部署基礎設施

---

## 二、現況分析

### ✅ 已通過（經審計確認）

| 項目 | 實作位置 | 說明 |
|------|----------|------|
| `.env*` 在 .gitignore | `.gitignore` | `.env`、`.env.cloud`、`.env.local`（backend/frontend）皆已排除 |
| `.env.example` 安全 | `.env.example`、`.env.example` | 所有值為空 placeholder，無真實 key |
| SERVICE_ROLE_KEY 隔離 | `config.py:12`、`supabase_client.py` | 僅 server-side 使用，前端無 `VITE_SUPABASE_SERVICE_ROLE_KEY` |
| 前端 bundle 安全 | `.env.example` | 僅 `VITE_API_BASE_URL`、`VITE_SUPABASE_URL`、`VITE_SUPABASE_ANON_KEY` |
| JWT 不信任 client | `auth_service.py` | `user_id` 從 JWT 解析（`g.user_id`），不從 request body 取 |
| 500 通用回應 | `__init__.py:145-164` | `handle_unexpected_error` 回傳 `"Unexpected server error"`，不含 stack trace |
| 404/405 通用回應 | `__init__.py:120-132` | 固定訊息，無內部資訊 |
| Logger 基本安全 | 全站搜尋 | 無 `print()` 洩露、無 `logger.*(password\|token\|secret)` 模式 |
| CORS 收斂 | `__init__.py:88-98` | 生產禁止 `*`，localhost 警告 |
| Security headers | `__init__.py:101-112` | `nosniff`、`DENY`、`strict-origin`、HSTS（可選） |
| Webhook 安全 | `payment_service.py` | 儲存 payload 時排除 `CheckMacValue` |
| ECPay 測試金鑰 | `test_ecpay_checkmacvalue.py` | 使用 ECPay 官方公開 sandbox key，非生產 secret |

### ⚠️ 需修復

| 項目 | 風險 | 位置 | 說明 |
|------|------|------|------|
| `details.raw` 洩露 | 🔴 HIGH | `domain/errors.py:60-135` | `map_supabase_error()` 將完整 Supabase 異常訊息放入 API response，生產環境會洩露 RLS policy 名稱、函式簽名等 |
| Dockerfile 硬編碼 `--debug` | 🟡 MEDIUM | `backend/Dockerfile:15` | `CMD` 硬編碼 `--debug`，生產部署無法透過環境變數控制 |
| docker-compose 硬編碼 `--debug` | 🟡 MEDIUM | `infra/docker-compose.yml:9` | `command` 硬編碼 `--debug`，生產不應使用此配置 |
| 缺少生產啟動腳本 | 🟡 MEDIUM | 無 | 生產應使用 gunicorn 而非 flask dev server |

---

## 三、任務計畫

### Task 1：修復 `details.raw` 錯誤訊息洩露 🔴

**目標**：生產環境 API error response 不包含內部錯誤細節

**修改檔案**：
- `backend/app/domain/errors.py`

**實作方式**：
1. 修改 `AppError.to_dict()` — 當 `APP_ENV=production` 時，排除 `details` 中的 `raw` 欄位
2. 需要存取 Flask `current_app.config`，但 `AppError` 是純 domain 物件，不應依賴 Flask
3. 改為在 `__init__.py` 的 error handler 層過濾：攔截 `AppError` 時，若 `APP_ENV=production` 且 details 含 `raw`，移除之

**具體做法**：
```python
# __init__.py — handle_app_error
@app.errorhandler(AppError)
def handle_app_error(error: AppError) -> tuple[dict, int]:
    body = error.to_dict()
    if app.config.get("APP_ENV") == "production":
        details = body.get("error", {}).get("details")
        if isinstance(details, dict):
            details.pop("raw", None)
            if not details:
                body["error"]["details"] = None
    return jsonify(body), error.http_status
```

**驗證**：
- 開發環境：`details.raw` 仍可見（方便除錯）
- 生產環境：`details.raw` 被移除

**測試**：
- `test_error_details_hidden_in_production` — `APP_ENV=production` 時 `details.raw` 不在 response
- `test_error_details_visible_in_development` — 開發環境 `details.raw` 可見

---

### Task 2：修復 Dockerfile 生產安全 🟡

**目標**：Dockerfile 不硬編碼 debug mode，支援生產部署

**修改檔案**：
- `backend/Dockerfile`

**實作方式**：
1. 移除 `--debug` flag
2. 安裝 gunicorn 作為生產 WSGI server
3. 預設使用 gunicorn 啟動，可透過環境變數覆蓋

**具體做法**：
```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 生產用 gunicorn；開發可透過 docker-compose command 覆蓋
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:create_app()"]
```

**驗證**：
- `docker build` 成功
- 生產環境使用 gunicorn（無 debug mode）
- 開發環境透過 docker-compose command 覆蓋為 flask dev server

**前置步驟**：
- 確認 `gunicorn` 已在 `requirements.txt` 中

---

### Task 3：更新 docker-compose.yml（開發配置）🟡

**目標**：明確標示 docker-compose.yml 為開發用途，與生產 Dockerfile 分離

**修改檔案**：
- `infra/docker-compose.yml`

**實作方式**：
1. 保留 `command: flask --app app run --host=0.0.0.0 --port=8000 --debug`（開發用覆蓋）
2. 加入註解說明此為開發配置
3. 確保 `--debug` 僅存在於開發用的 docker-compose，不在 Dockerfile

**驗證**：
- `docker compose -f infra/docker-compose.yml up` 正常啟動（開發模式）
- Dockerfile 預設無 debug（生產安全）

---

### Task 4：日誌安全強化 🟢

**目標**：確保日誌記錄不含敏感資料，新增日誌安全指引

**審查結果**：
- 現有日誌已安全（無密碼、token、卡號記錄）
- `app.logger.exception("Unexpected error: %s", error)` — 僅記錄 exception，不含 request body

**實作方式**：
1. 在 `__init__.py` 的 `handle_unexpected_error` 確認不記錄 request body（已滿足）
2. 檢查 ECPay webhook handler 不記錄完整 payload（已排除 CheckMacValue）

**驗證**：
- 全站 `grep` 確認無 `logger.*(password|token|secret|card)` 模式
- Webhook payload 儲存排除敏感欄位

**測試**：
- 現有測試已覆蓋 error handler 行為
- 無需新增測試（日誌為 side effect，難以 assert）

---

### Task 5：新增部署前環境變數檢查 🟢

**目標**：應用啟動時驗證生產必要環境變數已設定

**修改檔案**：
- `backend/app/__init__.py`

**實作方式**：
1. 新增 `_validate_production_config(app)` 函式
2. 生產環境（`APP_ENV=production`）強制檢查：
   - `SUPABASE_URL` 非空且為 HTTPS（已有）
   - `SUPABASE_ANON_KEY` 非空
   - `SUPABASE_SERVICE_ROLE_KEY` 非空
   - `ECPAY_MERCHANT_ID` 非空（若啟用付費票）
   - `CORS_ORIGINS` 不含 `*`（已有）
   - `FLASK_DEBUG` 為 `0`/`false`
   - `CRON_SECRET` 非空
3. 檢查失敗拋出 `ValueError`，阻止啟動

**驗證**：
- 生產環境缺少必要 env var → 應用拒絕啟動
- 開發環境 → 僅 warning，不阻止啟動

**測試**：
- `test_production_config_missing_supabase_key` — 生產缺少 key 時拋出 ValueError
- `test_development_config_allows_empty_keys` — 開發環境可正常啟動

---

### Task 6：測試與文件更新 📋

**測試檔案**：
- `backend/app/tests/test_sec4_deployment.py`（新建）

**測試案例**：

| # | 測試名稱 | 驗證項目 |
|---|----------|----------|
| 1 | `test_error_details_raw_hidden_in_production` | 生產環境 `details.raw` 不在 error response |
| 2 | `test_error_details_raw_visible_in_development` | 開發環境 `details.raw` 可見 |
| 3 | `test_500_no_stack_trace` | 未捕獲例外回傳通用訊息，無 stack trace |
| 4 | `test_production_requires_supabase_url` | 生產缺少 SUPABASE_URL → ValueError |
| 5 | `test_production_requires_anon_key` | 生產缺少 ANON_KEY → ValueError |
| 6 | `test_production_requires_service_role_key` | 生產缺少 SERVICE_ROLE_KEY → ValueError |
| 7 | `test_production_rejects_flask_debug` | 生產 FLASK_DEBUG=1 → ValueError |
| 8 | `test_production_requires_cron_secret` | 生產缺少 CRON_SECRET → ValueError |
| 9 | `test_development_allows_empty_config` | 開發環境空 config 可啟動 |

**文件更新**：
- `docs/development/develop.md` — SEC-4 狀態 `⬜ 未做` → `✅ 完成`
- 本文件狀態 → `✅ 已完成`

---

## 四、風險評估

| 風險 | 等級 | 影響 | 對策 |
|------|------|------|------|
| `details.raw` 洩露 Supabase 內部資訊 | 🔴 HIGH | 攻擊者可推測 DB schema / RLS policy | Task 1 修復 |
| Dockerfile `--debug` 導致生產暴露偵錯資訊 | 🟡 MEDIUM | stack trace / source code 洩露 | Task 2 修復 |
| 生產缺少必要 env var 導致功能異常 | 🟡 MEDIUM | 無聲失敗，難以排查 | Task 5 檢查 |
| Log 洩露敏感資料 | 🟢 LOW | 現已安全，持續監控 | Task 4 確認 |

---

## 五、執行順序

```
Task 1（details.raw 修復）→ Task 5（env var 檢查）→ Task 6（測試）
     ↘ Task 2（Dockerfile）→ Task 3（docker-compose）↗
                 Task 4（日誌審查）↗
```

**建議順序**：Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6

- Task 1 為 🔴 HIGH 優先
- Task 2-3 為 Dockerfile 相關，可連續處理
- Task 4 為審查確認，無程式碼變更
- Task 5 為防禦性檢查
- Task 6 為測試與文件收尾

---

## 六、驗收標準

- [ ] `details.raw` 在 `APP_ENV=production` 時不出現在 API response
- [ ] Dockerfile 預設使用 gunicorn，無 `--debug`
- [ ] docker-compose.yml 標示為開發用途
- [ ] 全站無 `logger.*(password|token|secret|card)` 洩露
- [ ] 生產環境啟動時驗證必要 env var
- [ ] 新增 9+ 個測試案例，全部通過
- [ ] `ruff check .` + `ruff format --check .` 通過
- [ ] `pytest -q` 全部通過
- [ ] develop.md SEC-4 狀態更新為 ✅
