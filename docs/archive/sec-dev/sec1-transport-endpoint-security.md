# SEC-1：傳輸與端點安全（HTTPS、CORS、Security Headers）

> **階段**：SEC-1（上線前安全強化）
> **狀態**：✅ 已完成
> **前置條件**：MVP-1~3 已完成；建議先完成 SEC-4（Secrets 與部署檢查）
> **參考規格**：[develop.md — SEC-1](develop.md#sec-1傳輸與端點安全-)

---

## 一、目標與範圍

### 目標

確保所有用戶端 ↔ 後端 ↔ Supabase 之間的通訊皆在加密通道上進行，並透過安全 HTTP headers 防範常見的傳輸層攻擊（降級攻擊、點擊劫持、MIME 嗅探等）。

### Done 條件（來自 develop.md）

> 生產環境全程 HTTPS；CORS 僅允許白名單；必要時加上 HSTS header（可由反向代理設定）。

### 範圍內（In Scope）

| # | 項目 | 說明 |
|---|------|------|
| 1 | HTTPS 全站強制 | 生產環境所有端點走 HTTPS，無混合內容 |
| 2 | HSTS Header | `Strict-Transport-Security` 防止協議降級 |
| 3 | CORS 收斂驗證 | 確認 `CORS_ORIGINS` 無 `*`，僅允許已知 domain |
| 4 | 安全回應 Headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` 等 |
| 5 | API Base URL 驗證 | `VITE_API_BASE_URL` 指向正確的 HTTPS 端點 |
| 6 | Supabase URL 驗證 | 生產環境使用 Cloud 正式 URL（非 localhost） |

### 範圍外（Out of Scope）

- CSP（Content-Security-Policy）→ 屬 SEC-3 注入防護
- Rate Limiting 調整 → 已在 MVP-3 完成
- 身份驗證邏輯修改 → 屬 SEC-2
- WAF / DDoS 防護 → 基礎設施層級，非應用層

---

## 二、現況分析

### ✅ 已完成

| 項目 | 實作位置 | 說明 |
|------|----------|------|
| CORS 白名單 | `backend/app/__init__.py:40` | `flask-cors`，scoped to `/api/*`，從 `CORS_ORIGINS` 讀取 |
| CORS 設定 | `backend/app/config.py` | 環境變數 `CORS_ORIGINS`，預設 `http://localhost:5173` |
| OPTIONS 免限流 | `backend/app/extensions.py` | Rate limiter 排除 CORS preflight |
| API Base URL | `frontend/src/api/client.ts` | `VITE_API_BASE_URL` 環境變數驅動 |
| Bearer Token | `backend/app/services/auth_service.py` | `@require_auth` decorator |

### ⬜ 待實作

| 項目 | 優先級 | 說明 |
|------|--------|------|
| ~~Security Headers Middleware~~ | ~~P0~~ | ~~後端統一注入安全 headers~~ ✅ 已完成 |
| ~~HSTS Header~~ | ~~P0~~ | ~~生產環境啟用 `Strict-Transport-Security`~~ ✅ 已完成 |
| ~~CORS 生產環境驗證~~ | ~~P1~~ | ~~確認生產 `.env` 無 `*`，無多餘 origin~~ ✅ 已完成 |
| ~~HTTPS 部署指引~~ | ~~P1~~ | ~~文件化反向代理設定（Nginx / Caddy）~~ ✅ 已完成（見附錄 A） |
| ~~Supabase URL 驗證~~ | ~~P1~~ | ~~啟動檢查：非 localhost~~ ✅ 已完成 |
| ~~前端 env 驗證~~ | ~~P2~~ | ~~建置時檢查 `VITE_API_BASE_URL` 為 https~~ ✅ 已完成 |

---

## 三、開發計畫

### Task 1：Security Headers Middleware（P0）

**修改檔案**：`backend/app/__init__.py`

在 Flask app 中加入 `@app.after_request` middleware，統一注入安全 headers：

```python
@app.after_request
def set_security_headers(response):
    # 防止 MIME 類型嗅探
    response.headers["X-Content-Type-Options"] = "nosniff"
    # 防止點擊劫持（僅允許同源嵌入）
    response.headers["X-Frame-Options"] = "DENY"
    # 控制 Referrer 資訊洩漏
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # 禁止被嵌入（現代瀏覽器替代 X-Frame-Options）
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    # 移除 Server header（減少資訊洩漏）
    response.headers.pop("Server", None)
    return response
```

**注意事項**：
- `X-XSS-Protection` 已被現代瀏覽器棄用，不加入
- HSTS 獨立處理（見 Task 2），因為開發環境不應啟用

---

### Task 2：HSTS Header（P0）

**修改檔案**：`backend/app/__init__.py`, `backend/app/config.py`

HSTS 僅在生產環境啟用，避免本地開發被鎖定：

```python
# config.py
ENABLE_HSTS = os.getenv("ENABLE_HSTS", "false").lower() == "true"
HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 預設 1 年

# __init__.py (在 set_security_headers 中)
if app.config.get("ENABLE_HSTS"):
    response.headers["Strict-Transport-Security"] = (
        f"max-age={app.config['HSTS_MAX_AGE']}; includeSubDomains"
    )
```

**環境變數更新**：
- `.env.example` 新增 `ENABLE_HSTS=false`、`HSTS_MAX_AGE=31536000`
- 生產環境設 `ENABLE_HSTS=true`

**替代方案**：若使用 Nginx/Caddy 反向代理，HSTS 可在反向代理層設定（見 Task 5）。兩者擇一即可，避免重複。

---

### Task 3：CORS 生產環境收斂（P1）

**修改檔案**：`backend/app/__init__.py`

新增啟動時 CORS 安全檢查：

```python
def _validate_cors_origins(app):
    """啟動時檢查 CORS 設定安全性"""
    origins = app.config.get("CORS_ORIGINS", [])
    if app.config.get("APP_ENV") == "production":
        for origin in origins:
            if origin == "*":
                raise ValueError("CORS_ORIGINS 禁止在生產環境使用 '*'")
            if origin.startswith("http://localhost"):
                app.logger.warning(
                    f"CORS_ORIGINS 包含 localhost: {origin}，請確認是否為誤設"
                )
```

**同時確認**：
- `flask-cors` 的 `supports_credentials` 未開啟（除非明確需要）
- 無額外 `Access-Control-Allow-*` headers 繞過白名單

---

### Task 4：Supabase / API URL 啟動驗證（P1）

**修改檔案**：`backend/app/__init__.py`

```python
def _validate_production_urls(app):
    """生產環境 URL 安全檢查"""
    if app.config.get("APP_ENV") != "production":
        return
    supabase_url = app.config.get("SUPABASE_URL", "")
    if "localhost" in supabase_url or "127.0.0.1" in supabase_url:
        raise ValueError("生產環境 SUPABASE_URL 不可指向 localhost")
    if not supabase_url.startswith("https://"):
        raise ValueError("生產環境 SUPABASE_URL 必須使用 HTTPS")
```

---

### Task 5：部署 HTTPS 指引文件（P1）

在本文件 [附錄 A](#附錄-a生產環境-https-部署參考) 提供 Nginx / Caddy 的反向代理設定範例，包含：
- TLS 憑證設定（Let's Encrypt）
- HTTPS 重導向
- HSTS header（反向代理層）
- Security headers（反向代理層替代方案）

---

### Task 6：前端環境變數建置檢查（P2）

**修改檔案**：`frontend/vite.config.ts`（或建置腳本）

考慮在建置時加入檢查，確保生產建置的 `VITE_API_BASE_URL` 使用 HTTPS：

```typescript
// vite.config.ts — 建議以 CI/CD 腳本檢查更合適
if (process.env.NODE_ENV === "production") {
  const apiUrl = process.env.VITE_API_BASE_URL || "";
  if (apiUrl && !apiUrl.startsWith("https://")) {
    console.warn("⚠️  VITE_API_BASE_URL should use HTTPS in production");
  }
}
```

> **注意**：此項為建議性質，不阻斷建置。實際 HTTPS 強制由部署層保證。

---

## 四、檔案變更清單

| 檔案 | 變更類型 | 說明 |
|------|----------|------|
| `backend/app/__init__.py` | 修改 | 新增 `set_security_headers` after_request + 啟動驗證 |
| `backend/app/config.py` | 修改 | 新增 `ENABLE_HSTS`, `HSTS_MAX_AGE`, `APP_ENV` 設定 |
| `.env.example` | 修改 | 新增 HSTS 相關環境變數 |
| `.env.cloud.example` | 修改 | 新增 HSTS 相關環境變數 |
| `backend/app/tests/test_security_headers.py` | 新增 | Security headers 測試 |

**不需要 Migration**：此功能純粹為 HTTP header 層級，不涉及資料庫變更。

---

## 五、測試計畫

### 5.1 單元測試（`backend/app/tests/test_security_headers.py`）

```python
class TestSecurityHeaders:
    """SEC-1: 安全回應 Headers 測試"""

    def test_x_content_type_options(self, client):
        """所有回應包含 X-Content-Type-Options: nosniff"""
        resp = client.get("/api/v1/events")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        """所有回應包含 X-Frame-Options: DENY"""
        resp = client.get("/api/v1/events")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client):
        """所有回應包含 Referrer-Policy"""
        resp = client.get("/api/v1/events")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_cross_origin_opener_policy(self, client):
        """所有回應包含 Cross-Origin-Opener-Policy: same-origin"""
        resp = client.get("/api/v1/events")
        assert resp.headers.get("Cross-Origin-Opener-Policy") == "same-origin"

    def test_no_server_header(self, client):
        """回應不包含 Server header（減少資訊洩漏）"""
        resp = client.get("/api/v1/events")
        assert "Server" not in resp.headers

    def test_hsts_disabled_by_default(self, client):
        """預設不啟用 HSTS（開發環境）"""
        resp = client.get("/api/v1/events")
        assert "Strict-Transport-Security" not in resp.headers

    def test_hsts_enabled_when_configured(self, app_with_hsts, client_with_hsts):
        """ENABLE_HSTS=true 時回應包含 HSTS header"""
        resp = client_with_hsts.get("/api/v1/events")
        hsts = resp.headers.get("Strict-Transport-Security")
        assert hsts is not None
        assert "max-age=" in hsts
        assert "includeSubDomains" in hsts

    def test_error_responses_include_security_headers(self, client):
        """404 等錯誤回應也包含安全 headers"""
        resp = client.get("/api/v1/nonexistent")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_options_preflight_includes_security_headers(self, client):
        """CORS preflight 回應也包含安全 headers"""
        resp = client.options("/api/v1/events")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
```

### 5.2 CORS 安全測試

```python
class TestCORSSecurity:
    """SEC-1: CORS 設定安全測試"""

    def test_cors_rejects_unknown_origin(self, client):
        """不在白名單的 origin 不回傳 Access-Control-Allow-Origin"""
        resp = client.get(
            "/api/v1/events",
            headers={"Origin": "https://evil.com"}
        )
        assert resp.headers.get("Access-Control-Allow-Origin") != "https://evil.com"

    def test_cors_allows_configured_origin(self, client):
        """白名單內的 origin 正確回傳 CORS header"""
        resp = client.get(
            "/api/v1/events",
            headers={"Origin": "http://localhost:5173"}
        )
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
```

### 5.3 啟動驗證測試

```python
class TestProductionValidation:
    """SEC-1: 生產環境啟動安全檢查"""

    def test_cors_wildcard_rejected_in_production(self):
        """生產環境不允許 CORS_ORIGINS='*'"""
        with pytest.raises(ValueError, match="禁止"):
            create_app({"APP_ENV": "production", "CORS_ORIGINS": ["*"]})

    def test_localhost_supabase_rejected_in_production(self):
        """生產環境不允許 SUPABASE_URL 指向 localhost"""
        with pytest.raises(ValueError, match="localhost"):
            create_app({
                "APP_ENV": "production",
                "SUPABASE_URL": "http://localhost:54321"
            })
```

### 5.4 手動驗證清單

| # | 驗證項目 | 驗證方式 | 預期結果 |
|---|----------|----------|----------|
| 1 | Security Headers | `curl -I https://api.example.com/api/v1/events` | 包含所有安全 headers |
| 2 | HSTS | 同上 | 包含 `Strict-Transport-Security` |
| 3 | CORS 拒絕 | `curl -H "Origin: https://evil.com" ...` | 無 `Access-Control-Allow-Origin` |
| 4 | CORS 允許 | `curl -H "Origin: https://your-frontend.com" ...` | 回傳正確 CORS header |
| 5 | 混合內容 | 瀏覽器 DevTools Console | 無 Mixed Content 警告 |
| 6 | HTTPS 重導向 | `curl -I http://api.example.com` | 301/302 → `https://` |
| 7 | Server Header | `curl -I ...` | 無 `Server` header 或為反向代理通用值 |
| 8 | 錯誤頁面 Headers | `curl -I .../nonexistent` | 404 回應仍包含安全 headers |

### 5.5 自動化驗證腳本（建議）

可考慮加入 CI/CD pipeline 的檢查：

```bash
# 檢查 .env 無 wildcard CORS
if grep -q 'CORS_ORIGINS=\*' .env; then
  echo "ERROR: CORS_ORIGINS cannot be '*'"
  exit 1
fi
```

---

## 六、執行順序與時程建議

```
Step 1: Task 1 + Task 2 — Security Headers + HSTS     （核心實作）
Step 2: Task 3 + Task 4 — 啟動驗證                      （安全防護網）
Step 3: 測試 — 撰寫並執行所有測試                         （驗證）
Step 4: Task 5 — 部署指引文件                             （文件）
Step 5: Task 6 — 前端建置檢查                             （選做）
```

---

## 七、風險與注意事項

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| HSTS 設定錯誤導致本地開發無法存取 | 開發環境被鎖定在 HTTPS | 僅在 `ENABLE_HSTS=true` 時啟用，預設 false |
| CORS 設定過嚴 | 前端無法存取 API | 啟動時驗證 + 完整測試覆蓋 |
| `X-Frame-Options: DENY` 影響合法嵌入需求 | 無法被 iframe 嵌入 | 目前無嵌入需求；未來如需可改為 `SAMEORIGIN` |
| 反向代理與 Flask 重複設定 headers | Header 重複 | 擇一設定，文件中說明清楚 |

---

## 附錄 A：生產環境 HTTPS 部署參考

### A.1 Caddy（推薦，自動 HTTPS）

```caddyfile
# Caddyfile
api.example.com {
    reverse_proxy backend:8000

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        -Server
    }
}

www.example.com {
    reverse_proxy frontend:5173
}
```

> Caddy 自動取得 Let's Encrypt 憑證，無需額外設定 TLS。

### A.2 Nginx + Let's Encrypt

```nginx
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 隱藏版本資訊
    server_tokens off;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### A.3 雲端平台（Render / Railway / Fly.io）

大多數雲端平台自動提供 HTTPS，僅需：
1. 確認自訂 domain 已綁定 SSL 憑證
2. 在 Flask 層設定 security headers（平台通常不提供 header 自訂介面）
3. 環境變數設 `ENABLE_HSTS=true`

---

## 附錄 B：相關安全 Headers 說明

| Header | 用途 | 建議值 |
|--------|------|--------|
| `Strict-Transport-Security` | 強制 HTTPS，防止降級攻擊 | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | 防止 MIME 類型嗅探 | `nosniff` |
| `X-Frame-Options` | 防止點擊劫持 | `DENY` |
| `Referrer-Policy` | 控制 Referer header 洩漏 | `strict-origin-when-cross-origin` |
| `Cross-Origin-Opener-Policy` | 隔離跨源視窗 | `same-origin` |
| ~~`X-XSS-Protection`~~ | ~~XSS 過濾（已棄用）~~ | 不設定（現代瀏覽器已移除） |
