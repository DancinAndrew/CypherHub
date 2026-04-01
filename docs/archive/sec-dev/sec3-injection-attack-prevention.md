# SEC-3：注入與攻擊防護（SQL、XSS、CSRF、Rate Limit）

> **階段**：SEC-3（上線前安全強化）
> **狀態**：✅ 已完成
> **前置條件**：SEC-1、SEC-2 已完成
> **參考規格**：[develop.md — SEC-3](develop.md#sec-3注入與攻擊防護-)

---

## 一、目標與範圍

### 目標

確保應用程式對常見注入攻擊（SQL Injection、XSS、CSRF）具備防護能力，所有寫入端點具備適當的 Rate Limiting，檔案上傳驗證 MIME 類型白名單。

### Done 條件（來自 develop.md）

> 無 raw SQL 串接；前端無 unsafe `v-html` 渲染使用者內容；rate limit 已實作。

### 範圍內（In Scope）

| # | 項目 | 說明 |
|---|------|------|
| 1 | SQL Injection 審查 | 確認所有 DB 查詢使用參數化（Supabase RPC） |
| 2 | XSS 審查 | 確認前端無 `v-html`、`innerHTML` 渲染未淨化使用者內容 |
| 3 | CSRF 確認 | 確認 API 使用 Bearer token（非 cookie session） |
| 4 | 輸入驗證完整性 | 確認所有寫入端點使用 Pydantic schema 驗證 |
| 5 | IDOR 確認 | 確認 `user_id` 來自 JWT，RLS 防止跨用戶操作 |
| 6 | Rate Limiting 補全 | 補齊缺少限流的寫入端點 |
| 7 | 檔案上傳安全 | 加入 MIME 類型白名單驗證 |

### 範圍外（Out of Scope）

- Content-Security-Policy header → 屬 SEC-4 部署檢查
- Log 敏感資料審查 → 屬 SEC-4
- Secrets 管理 → 屬 SEC-4

---

## 二、現況分析

### ✅ 已通過（經審計確認）

| 項目 | 實作位置 | 說明 |
|------|----------|------|
| SQL Injection | `services/supabase_client.py` | 所有 DB 存取透過 `call_rpc()` 參數化呼叫，無 raw SQL 串接 |
| XSS — `v-html` | 全站 `.vue` 檔案 | **零個** `v-html` 使用，所有內容透過 Vue 安全插值 `{{ }}` |
| XSS — `innerHTML` | `main.ts:45` | 唯一 `innerHTML` 在 app mount 失敗的 fallback，已用 `.replace(/</g, "&lt;")` escape |
| CSRF | `api/client.ts:16-25` | 純 Bearer token 認證（Authorization header），無 cookie session |
| 輸入驗證 | `domain/schemas.py` | 所有 request body 使用 Pydantic v2 驗證（UUID、min_length、enum） |
| IDOR | `services/auth_service.py` + RLS | `user_id` 從 JWT 解析（`g.user_id`），所有表啟用 RLS |
| Rate limit — auth | `blueprints/auth.py:112` | `POST /auth/login` → 10/min |
| Rate limit — register | `blueprints/registrations.py:18` | `POST /<id>/register` → 20/min |
| Rate limit — checkin | `blueprints/checkin.py:16,33` | verify/commit → 60/min |
| Rate limit — progress | `blueprints/progress.py` | 各端點 10~60/min |
| 全局預設限流 | `extensions.py:27` | 5000/day + 500/hour 全局預設 |
| X-Content-Type-Options | `__init__.py` | `nosniff` 防止 MIME 嗅探（SEC-1 已設） |
| API Content-Type | Flask `jsonify` | 所有 API 回傳 `application/json`，防止瀏覽器 XSS |

### ⚠️ 需補強

| 項目 | 風險等級 | 位置 | 說明 |
|------|----------|------|------|
| Rate limit — 訂單/付款 | 中 | `orders.py`, `payments.py` | 寫入端點無獨立限流 |
| Rate limit — 主辦方寫入 | 低 | `ticket_types.py` | apply / create event / media upload 無獨立限流 |
| Rate limit — 管理員 | 低 | `admin.py` | refund / approval 等無獨立限流 |
| Rate limit — 其他寫入 | 低 | `tickets.py`, `settlements.py`, `jobs.py` | 部分端點無獨立限流 |
| 檔案上傳 MIME 驗證 | 低 | `ticket_types.py:248` | 接受任意 content_type，未做白名單驗證 |

---

## 三、需補強項目分析

### 3.1 Rate Limiting 缺口

目前僅 auth、register、checkin、progress 有獨立限流。以下端點依賴全局預設（500/hour），對於寫入操作可能過於寬鬆：

#### 高優先級（面向一般使用者）

| 端點 | 方法 | 位置 | 建議限制 | 原因 |
|------|------|------|----------|------|
| `/api/v1/orders` | POST | `orders.py:23` | 30/min | 防止刷單、佔位攻擊 |
| `/api/v1/payments/checkout` | POST | `payments.py:16` | 30/min | 防止重複建立付款 |
| `/api/v1/orders/<id>` | DELETE | `orders.py:48` | 30/min | 防止反覆取消佔位 |
| `/api/v1/tickets/<id>` | DELETE | `tickets.py:35` | 20/min | 防止惡意取消票券 |
| `/api/v1/tickets/<id>/resend` | POST | `tickets.py:44` | 5/min | 防止濫發 email |

#### 中優先級（主辦方端點）

| 端點 | 方法 | 位置 | 建議限制 | 原因 |
|------|------|------|----------|------|
| `/api/v1/organizer/apply` | POST | `ticket_types.py:35` | 5/min | 防止重複申請 |
| `/api/v1/organizer/events` | POST | `ticket_types.py:47` | 10/min | 防止批量建活動 |
| `/api/v1/organizer/events/<id>/media` | POST | `ticket_types.py:236` | 10/min | 防止濫傳檔案 |
| `/api/v1/organizer/events/<id>/comp-ticket` | POST | `ticket_types.py:218` | 20/min | 防止批量送票 |
| `/api/v1/organizer/events/<id>/attendees/<id>/resend` | POST | `ticket_types.py:208` | 5/min | 防止濫發 email |

#### 低優先級（管理員 + 內部）

| 端點 | 方法 | 位置 | 建議限制 | 原因 |
|------|------|------|----------|------|
| `/api/v1/admin/orders/<id>/refund` | POST | `admin.py:112` | 10/min | 防止誤操作 |
| `/api/v1/admin/organizations/<id>/approval` | PATCH | `admin.py:132` | 10/min | 防止誤操作 |
| `/api/v1/admin/settlements/generate` | POST | `admin.py:148` | 5/min | 防止重複結算 |
| `/api/v1/admin/payout-requests/<id>` | PATCH | `admin.py:172` | 10/min | 防止誤操作 |
| `/api/v1/payout-requests` | POST | `settlements.py:36` | 5/min | 防止重複請款 |

### 3.2 檔案上傳 MIME 類型

**問題描述**

`ticket_types.py:248` 的檔案上傳端點接受任意 content_type：

```python
content_type = file.content_type or "image/jpeg"  # 未驗證！
```

攻擊者可上傳 `.html`、`.svg`（含 XSS）等非圖片檔案。雖然 Supabase Storage 有自身安全機制，但在應用層加入白名單是防禦深度的最佳實踐。

**修復方案**

```python
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

content_type = file.content_type or ""
if content_type not in ALLOWED_IMAGE_TYPES:
    raise AppError(
        code="VALIDATION_ERROR",
        message="不支援的檔案類型，僅允許 JPEG、PNG、WebP、GIF",
        http_status=400,
    )
```

---

## 四、開發計畫

### Task 1：補齊使用者端寫入端點 Rate Limit（P0）

**修改檔案**：
- `backend/app/blueprints/orders.py`
- `backend/app/blueprints/payments.py`
- `backend/app/blueprints/tickets.py`

**變更內容**：

```python
# orders.py
from app.extensions import rate_limiter

@bp.post("/")
@rate_limiter.limit("30 per minute")
@require_auth
def create_hold_order(): ...

@bp.delete("/<order_id>")
@rate_limiter.limit("30 per minute")
@require_auth
def cancel_order(order_id): ...

# payments.py
from app.extensions import rate_limiter

@bp.post("/checkout")
@rate_limiter.limit("30 per minute")
@require_auth
def create_checkout(): ...

# tickets.py
from app.extensions import rate_limiter

@bp.delete("/<ticket_id>")
@rate_limiter.limit("20 per minute")
@require_auth
def cancel_ticket(ticket_id): ...

@bp.post("/<ticket_id>/resend")
@rate_limiter.limit("5 per minute")
@require_auth
def resend_ticket_email(ticket_id): ...
```

### Task 2：補齊主辦方端點 Rate Limit（P1）

**修改檔案**：`backend/app/blueprints/ticket_types.py`

**變更內容**：

```python
from app.extensions import rate_limiter

@bp.post("/apply")
@rate_limiter.limit("5 per minute")
@require_auth
def apply_organizer(): ...

@bp.post("/events")
@rate_limiter.limit("10 per minute")
@require_auth
def create_event(): ...

@bp.post("/events/<event_id>/media")
@rate_limiter.limit("10 per minute")
@require_auth
def upload_event_media(event_id): ...

@bp.post("/events/<event_id>/comp-ticket")
@rate_limiter.limit("20 per minute")
@require_auth
def send_comp_ticket(event_id): ...

@bp.post("/events/<event_id>/attendees/<ticket_id>/resend")
@rate_limiter.limit("5 per minute")
@require_auth
def resend_attendee_email(event_id, ticket_id): ...
```

### Task 3：補齊管理員與內部端點 Rate Limit（P1）

**修改檔案**：
- `backend/app/blueprints/admin.py`
- `backend/app/blueprints/settlements.py`
- `backend/app/blueprints/jobs.py`

**變更內容**：

```python
# admin.py
from app.extensions import rate_limiter

@bp.post("/orders/<order_id>/refund")
@rate_limiter.limit("10 per minute")
@require_auth
def admin_refund_order(order_id): ...

@bp.patch("/organizations/<org_id>/approval")
@rate_limiter.limit("10 per minute")
@require_auth
def update_org_approval(org_id): ...

@bp.post("/settlements/generate")
@rate_limiter.limit("5 per minute")
@require_auth
def generate_settlements(): ...

@bp.patch("/payout-requests/<payout_id>")
@rate_limiter.limit("10 per minute")
@require_auth
def update_payout_request(payout_id): ...

# settlements.py
@bp.post("/payout-requests")
@rate_limiter.limit("5 per minute")
@require_auth
def create_payout_request(): ...
```

### Task 4：檔案上傳 MIME 類型白名單（P1）

**修改檔案**：`backend/app/blueprints/ticket_types.py`

**變更內容**：在 `upload_event_media()` 中加入 MIME 類型驗證：

```python
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# 在 file.read() 之前加入
content_type = file.content_type or ""
if content_type not in ALLOWED_IMAGE_TYPES:
    raise AppError(
        code="VALIDATION_ERROR",
        message="不支援的檔案類型，僅允許 JPEG、PNG、WebP、GIF",
        http_status=400,
    )
```

### Task 5：撰寫測試（P0）

**新增檔案**：`backend/app/tests/test_sec3_rate_limit.py`

測試覆蓋：
1. 訂單端點 rate limit 觸發（超過 30/min 回傳 429）
2. 付款端點 rate limit 觸發
3. 主辦方端點 rate limit 觸發
4. 管理員端點 rate limit 觸發
5. 檔案上傳 MIME 驗證（合法類型通過 / 非法類型被拒）
6. 既有 rate limit 不受影響（auth 10/min, register 20/min）

### Task 6：安全審查確認文件（P2）

更新本文件，記錄每項審查結果：
- SQL Injection：✅ 確認無 raw SQL
- XSS：✅ 確認無 `v-html`
- CSRF：✅ 確認 Bearer token
- 輸入驗證：✅ 確認 Pydantic
- IDOR：✅ 確認 JWT + RLS
- Rate Limiting：✅ 全面補齊
- 檔案上傳：✅ MIME 白名單

---

## 五、檔案變更清單

| 檔案 | 變更類型 | 說明 |
|------|----------|------|
| `backend/app/blueprints/orders.py` | 修改 | 加入 rate limit（30/min） |
| `backend/app/blueprints/payments.py` | 修改 | 加入 rate limit（30/min） |
| `backend/app/blueprints/tickets.py` | 修改 | 加入 rate limit（20/min, 5/min） |
| `backend/app/blueprints/ticket_types.py` | 修改 | 加入 rate limit + MIME 白名單 |
| `backend/app/blueprints/admin.py` | 修改 | 加入 rate limit（5-10/min） |
| `backend/app/blueprints/settlements.py` | 修改 | 加入 rate limit（5/min） |
| `backend/app/tests/test_sec3_rate_limit.py` | 新增 | Rate limit + MIME 驗證測試 |

**不需要 Migration**：純 Python 邏輯變更。
**不需要前端修改**：前端已通過 XSS 審查。

---

## 六、測試計畫

### 6.1 單元測試（`test_sec3_rate_limit.py`）

```python
class TestOrderRateLimit:
    """訂單端點 rate limit 測試"""
    def test_create_order_rate_limit(self, client):
        """POST /orders 超過 30 次/min → 429"""
    def test_cancel_order_rate_limit(self, client):
        """DELETE /orders/<id> 超過 30 次/min → 429"""

class TestPaymentRateLimit:
    """付款端點 rate limit 測試"""
    def test_checkout_rate_limit(self, client):
        """POST /payments/checkout 超過 30 次/min → 429"""

class TestOrganizerRateLimit:
    """主辦方端點 rate limit 測試"""
    def test_apply_rate_limit(self, client):
        """POST /organizer/apply 超過 5 次/min → 429"""
    def test_create_event_rate_limit(self, client):
        """POST /organizer/events 超過 10 次/min → 429"""
    def test_upload_media_rate_limit(self, client):
        """POST /organizer/events/<id>/media 超過 10 次/min → 429"""

class TestFileUploadMIME:
    """檔案上傳 MIME 驗證測試"""
    def test_allowed_jpeg(self, client):
        """image/jpeg → 通過"""
    def test_allowed_png(self, client):
        """image/png → 通過"""
    def test_rejected_html(self, client):
        """text/html → 400"""
    def test_rejected_svg(self, client):
        """image/svg+xml → 400（可含 XSS）"""
    def test_rejected_empty_type(self, client):
        """空 content_type → 400"""
```

### 6.2 既有測試驗證

```bash
cd backend && .venv/bin/python -m pytest -q  # 全部測試通過
```

### 6.3 建置驗證

```bash
cd frontend && npm run build  # TypeScript + Vite 建置
```

### 6.4 手動驗證清單

| # | 驗證項目 | 步驟 | 預期結果 |
|---|----------|------|----------|
| 1 | 訂單 rate limit | 快速連續建立 > 30 筆訂單 | 超過限制後回傳 429 |
| 2 | 付款 rate limit | 快速連續送出 > 30 次 checkout | 超過限制後回傳 429 |
| 3 | 主辦方申請 rate limit | 快速連續送出 > 5 次 apply | 超過限制後回傳 429 |
| 4 | 檔案上傳 — 合法 | 上傳 .jpg / .png 圖片 | 上傳成功 |
| 5 | 檔案上傳 — 非法 | 上傳 .html / .svg 檔案 | 回傳 400 錯誤 |
| 6 | XSS 確認 | 在活動名稱輸入 `<script>alert(1)</script>` | 前端正常顯示文字，無彈窗 |
| 7 | SQL Injection 確認 | 在搜尋欄輸入 `'; DROP TABLE events;--` | 回傳正常錯誤或空結果 |

---

## 七、執行順序

```
Step 1: Task 1 — 使用者端寫入端點 Rate Limit（orders, payments, tickets）
Step 2: Task 2 — 主辦方端點 Rate Limit（ticket_types）
Step 3: Task 3 — 管理員與內部端點 Rate Limit（admin, settlements）
Step 4: Task 4 — 檔案上傳 MIME 類型白名單
Step 5: Task 5 — 撰寫並執行測試
Step 6: Task 6 — 更新文件，標記完成
```

---

## 八、風險與注意事項

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| Rate limit 過嚴 | 正常使用者被擋 | 設定合理閾值（30/min 為一般使用遠綽有餘） |
| MIME 白名單遺漏 | 合法圖片格式被拒 | 涵蓋 JPEG、PNG、WebP、GIF 四大主流格式 |
| Rate limit 誤觸 CI 測試 | 測試失敗 | 測試 fixture 中 reset limiter 或用 `TESTING` 環境跳過 |
| `@rate_limiter.limit` 裝飾器順序 | 限流不生效 | 確保 `@rate_limiter.limit` 在 `@require_auth` 之前（先檢查頻率再驗證身份） |
