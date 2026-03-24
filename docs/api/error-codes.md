# Error Code 對照表

> 本文件列出 CypherHub 後端所有 `AppError` error code，以及前端 `errorMessages.ts` 的中文映射。
> 對應原始碼：`backend/app/domain/errors.py`、`frontend/src/utils/errorMessages.ts`。

---

## 一、錯誤回應格式

所有 API 錯誤均透過 `AppError` 包裝，回傳統一格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": null
  }
}
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `code` | `string` | 機器可讀的 error code（大寫 SNAKE_CASE） |
| `message` | `string` | 英文錯誤訊息（供開發除錯） |
| `details` | `any \| null` | 額外資訊（Pydantic 驗證欄位、Supabase 原始錯誤等） |

前端透過 `toApiErrorMessage()` 將 `code` 映射為中文使用者訊息。

---

## 二、Error Code 總表

### 2.1 認證（Auth）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `AUTH_REQUIRED` | 401 | Missing Authorization Bearer token | 請先登入後再操作。 | 未帶 `Authorization` header 或 token 為空 |
| `AUTH_INVALID` | 401 | Invalid or expired access token | 登入已過期，請重新登入。 | JWT 過期或 Supabase `get_user()` 驗證失敗 |
| `AUTH_FAILED` | 400 | Invalid login credentials | 登入失敗：帳號或密碼不正確。 | 帳密錯誤、Supabase 未回傳 session、session 缺少 token |
| `AUTH_SERVICE_ERROR` | 502 | Unable to reach auth service | *(前端未映射，顯示原始 message)* | 無法連線 Supabase Auth 服務 |
| `CONFIG_ERROR` | 500 | Auth not configured | *(前端未映射)* | `SUPABASE_URL` 或 `SUPABASE_ANON_KEY` 未設定 |

### 2.2 權限（Permission）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `FORBIDDEN` | 403 | You do not have permission / Admin allowlist required / Operation blocked by RLS | 您沒有權限執行此操作。 | 非 Admin、非組織成員、RLS 阻擋 |
| `STAFF_CANNOT_MANAGE` | 403 | Staff role cannot create or edit events | 工作人員身分僅能核銷與查看名單，無法建立或編輯活動。 | Staff 嘗試建立/編輯活動、票種、表單 |
| `ORG_NOT_APPROVED` | 403 | Organization is pending approval | 組織尚未通過審核，無法執行此操作。 | 組織 `approval_status ≠ approved` 時嘗試建活動 |
| `ORGANIZER_PERMISSION_CHECK_FAILED` | — | — | 權限檢查失敗，請確認您有此組織的管理權限。 | *(僅前端映射，泛用權限檢查失敗)* |

### 2.3 活動（Event）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `EVENT_NOT_FOUND` | 404 | Event not found | 找不到此活動。 | 活動 ID 不存在或無 RLS 可見性 |
| `EVENT_NOT_PUBLISHED` | 409 | Event is not open for registration | 活動尚未發布，暫時不可報名。 | 活動 `status ≠ published` 時嘗試報名/購票 |
| `INVALID_EVENT_ID` | 400 | Invalid event id | *(前端未映射)* | RPC 收到無效的 event UUID |
| `CREATE_EVENT_FAILED` | — | — | 建立活動失敗，請稍後再試。 | *(僅前端映射，catch-all)* |
| `UPDATE_EVENT_FAILED` | — | — | 更新活動失敗，請稍後再試。 | *(僅前端映射，catch-all)* |

### 2.4 票種（Ticket Type）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `TICKET_TYPE_NOT_FOUND` | 404 | Ticket type not found | 找不到此票種。 | 票種 ID 不存在 |
| `TICKET_TYPE_INACTIVE` | 409 | Ticket type is inactive | 票種目前未開放。 | 票種 `is_active = false` |
| `TICKET_TYPE_EVENT_MISMATCH` | 400 | ticket_type_id does not belong to event_id | 票種不屬於此活動。 | 票種與活動 ID 不匹配 |
| `SOLD_OUT` | 409 | Tickets are sold out | 票券已售完。 | `sold_count + hold_count ≥ capacity` 或 DB check constraint 觸發 |
| `CAPACITY_EXCEEDED` | 409 | Ticket type is sold out | 票券容量已滿。 | RPC 扣量時容量不足 |
| `SALE_NOT_STARTED` | 409 | Sale has not started | 票券尚未開賣。 | 目前時間早於 `sale_start_at` |
| `SALE_ENDED` | 409 | Sale has ended | 票券販售已結束。 | 目前時間晚於 `sale_end_at` |
| `PER_USER_LIMIT_EXCEEDED` | 409 | Per-user limit exceeded | 已達每人限購數量，無法重複報名此票種。 | 使用者持有數量已達 `per_user_limit` |
| `PAID_TICKET_NOT_ALLOWED_IN_MVP1` | 400 | Paid tickets are not available in MVP-1 | *(前端未映射)* | 透過免費報名端點嘗試購買付費票 |
| `CREATE_TICKET_TYPE_FAILED` | — | — | 建立票種失敗，請稍後再試。 | *(僅前端映射，catch-all)* |
| `UPDATE_TICKET_TYPE_FAILED` | — | — | 更新票種失敗，請稍後再試。 | *(僅前端映射，catch-all)* |
| `DELETE_TICKET_TYPE_FAILED` | — | — | 刪除票種失敗，請稍後再試。 | *(僅前端映射，catch-all)* |

### 2.5 票券（Ticket）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `TICKET_NOT_FOUND` | 404 | Ticket not found | 找不到此票券。 | 票券 ID 不存在或不屬於當前使用者 |
| `TICKET_NOT_FOUND_OR_ALREADY_CANCELLED` | 404 | Ticket not found or already cancelled | *(前端未映射)* | RPC 取消時找不到或已取消 |
| `INVALID_STATUS` | 409 | Ticket status does not allow this operation | *(前端未映射)* | 票券狀態不允許當前操作（如已核銷無法取消） |
| `ATTENDEE_NO_EMAIL` | 400 | 該參加者帳號無信箱，無法重寄票券 | 此參加者無 email，無法寄送票券。 | 重寄票券時使用者無 email |
| `LIST_TICKETS_FAILED` | — | — | 載入票券列表失敗，請稍後再試。 | *(僅前端映射，catch-all)* |
| `CANCEL_TICKET_FAILED` | — | — | 取消票券失敗，請稍後再試。 | *(僅前端映射，catch-all)* |
| `RESEND_TICKET_FAILED` | — | — | 重寄票券信件失敗，請稍後再試。 | *(僅前端映射，catch-all)* |

### 2.6 報名（Registration）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `REGISTER_FAILED` | — | — | 報名失敗，請稍後再試。 | *(僅前端映射，catch-all)* |

### 2.7 訂單（Order）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `ORDER_NOT_FOUND` | 404 | Order not found | 找不到此訂單。 | 訂單 ID 不存在或不屬於當前使用者 |
| `ORDER_NOT_HOLDING` | 409 | Only holding orders can be cancelled | *(前端未映射)* | 嘗試取消非 `holding` 狀態的訂單 |
| `ORDER_CANNOT_REFUND` | 409 | Order status cannot be refunded | 此訂單無法退款。 | 訂單狀態非 `paid` / `issued`，無法退款 |
| `HOLD_ITEMS_EMPTY` | 400 | Hold items cannot be empty | *(前端未映射)* | 建立 hold order 時 items 為空陣列 |
| `HOLD_ORDER_CREATE_FAILED` | 500 | Unexpected RPC response | 建立訂單失敗，請稍後再試。 | `create_hold_order` RPC 回傳異常 |
| `INVALID_HOLD_MINUTES` | 400 | Hold minutes must be between 1 and 60 | *(前端未映射)* | `hold_minutes` 超出 1–60 範圍 |
| `INVALID_ITEM` | 400 | Invalid item: ticket_type_id and quantity required | *(前端未映射)* | 訂單項目缺少必要欄位 |
| `INVALID_QUANTITY` | 400 | Quantity must be greater than zero | *(前端未映射)* | RPC 收到 `quantity ≤ 0` |
| `INVALID_ORDER_STATUS_TRANSITION` | — | — | 訂單狀態轉換不合法。 | *(僅前端映射)* |
| `ORDERS_LIST_FAILED` | — | — | 載入訂單列表失敗，請稍後再試。 | *(僅前端映射，catch-all)* |
| `ORDER_FETCH_FAILED` | — | — | 載入訂單詳情失敗，請稍後再試。 | *(僅前端映射，catch-all)* |
| `CANCEL_ORDER_FAILED` | — | — | 取消訂單失敗，請稍後再試。 | *(僅前端映射，catch-all)* |

### 2.8 金流（Payment）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `ECPAY_CONFIG_MISSING` | 503 | ECPay configuration not configured | 金流設定遺失，請聯絡客服。 | 缺少 ECPay Merchant ID / Hash Key / IV |
| `PAYMENT_NOT_FOUND` | 404 | No ECPay payment found for this order | 找不到付款紀錄。 | 訂單無對應的 ECPay payment 記錄 |
| `PAYMENT_NOT_COMPLETED` | 409 | Payment is not completed, cannot refund | 付款尚未完成。 | 嘗試退款但 payment `status ≠ completed` |
| `ORDER_ID_REQUIRED` | 400 | order_id is required | *(前端未映射)* | `POST /checkout` 缺少 `order_id` 參數 |
| `TRADE_NO_MISSING` | 400 | TradeNo not found in payment | *(前端未映射)* | 退款時 payment 缺少 ECPay TradeNo |

### 2.9 退款（Refund）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `REFUND_NOT_SUPPORTED` | 400 | This payment type does not support API refund | 此付款方式不支援退款。 | 非信用卡付款（ATM / 超商等）無法 API 退款 |
| `REFUND_CREATE_FAILED` | 500 | Failed to create refund record | 退款處理失敗，請稍後再試。 | Supabase 建立 refund record 失敗 |
| `REFUND_API_FAILED` | 502 | ECPay refund failed | 金流退款 API 呼叫失敗，請稍後再試。 | ECPay DoAction API 回傳錯誤 |

### 2.10 結算與提領（Settlement / Payout）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `SETTLEMENT_NOT_FOUND` | 404 | Settlement not found | 找不到此結算紀錄。 | 結算 ID 不存在或不屬於該組織 |
| `INSUFFICIENT_BALANCE` | 400 | Available balance is insufficient | 可用餘額不足，無法提領此金額。 | 提領金額超過可用餘額 |
| `PAYOUT_NOT_FOUND` | 404 | Payout request not found | 找不到此提領申請。 | 提領申請 ID 不存在 |
| `PAYOUT_CREATE_FAILED` | 500 | Failed to create payout request | 提領申請失敗，請稍後再試。 | Supabase 建立 payout request 失敗 |
| `PAYOUT_ALREADY_PROCESSED` | 409 | Payout already processed | 此提領申請已處理完畢。 | 嘗試重複處理已完成的提領 |
| `PAYOUT_NOT_APPROVED` | 409 | Payout must be approved before marking paid | *(前端未映射)* | Admin 嘗試標記未核准的提領為已付款 |
| `SETTLEMENTS_LIST_FAILED` | — | — | 載入結算列表失敗，請稍後再試。 | *(僅前端映射，catch-all)* |
| `SETTLEMENT_FETCH_FAILED` | — | — | 載入結算詳情失敗，請稍後再試。 | *(僅前端映射，catch-all)* |

### 2.11 核銷（Check-in）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `QR_MISMATCH` | 400 | QR payload does not match ticket | QR 碼資訊不符，請確認票券正確性。 | QR payload 與 ticket 資料不一致 |
| `CHECKIN_VERIFY_FAILED` | — | — | 核銷驗證失敗，請重新掃描。 | *(僅前端映射，catch-all)* |
| `CHECKIN_COMMIT_FAILED` | — | — | 核銷確認失敗，請重新操作。 | *(僅前端映射，catch-all)* |

### 2.12 組織（Organization）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `ORGANIZATION_NOT_FOUND` | 404 | Organization not found | 找不到此組織。 | 組織 ID 不存在 |
| `MEMBER_NOT_FOUND` | 404 | Member not found | 找不到此成員。 | 成員 ID 不存在於該組織 |
| `USER_NOT_FOUND` | 404 | No user found with this email | *(前端未映射)* | 邀請成員時 email 未註冊 |
| `ORGANIZER_APPLY_FAILED` | — | — | 主辦方申請失敗，請稍後再試。 | *(僅前端映射，catch-all)* |

### 2.13 表單（Form）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `FORM_SCHEMA_INVALID` | 500 | Stored form schema is invalid | 表單欄位設定格式不正確。 | 資料庫中的 form schema JSON 格式異常 |
| `FORM_UPSERT_FAILED` | — | — | 儲存表單失敗，請稍後再試。 | *(僅前端映射，catch-all)* |

### 2.14 Admin 專用

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `COMP_TICKET_FAILED` | 500 | Failed to create ticket | *(前端未映射)* | Admin 建立 Comp 票失敗 |

### 2.15 RPC / 資料庫（Supabase Error Mapping）

這些 code 由 `map_supabase_error()` 自動從 Supabase 例外中解析產生：

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `RPC_PERMISSION_DENIED` | 403 | Current user token cannot execute this RPC | 目前登入身分沒有執行此操作的權限，請重新登入後再試。 | JWT 無權限呼叫某 RPC function |
| `RPC_NOT_FOUND` | 500 | Required RPC function is missing or signature mismatch | 後端 RPC 函式不存在或版本不一致，請確認 migration 已完整套用。 | RPC function 不存在（migration 未套用） |
| `DB_PATCH_REQUIRED` | 500 | Database patch required | 資料庫缺少必要 patch，請先執行 supabase db push。 | 缺少 `gen_random_bytes` function（migration 0005） |
| `VALIDATION_ERROR` | 400 | Invalid UUID format in request | *(前端特殊處理，顯示欄位 + 訊息)* | UUID 格式錯誤，或 Pydantic 驗證失敗 |
| `SUPABASE_ERROR` | 400 | Supabase operation failed | *(前端未映射，顯示原始 message)* | 無法歸類的 Supabase 錯誤（fallback） |

### 2.16 通用（Global）

| Code | HTTP | 英文訊息 | 中文訊息 | 觸發場景 |
|------|------|----------|----------|----------|
| `NOT_FOUND` | 404 | Resource not found | 找不到此資源。 | Flask 404 handler（路由不存在） |
| `METHOD_NOT_ALLOWED` | 405 | Method not allowed | 不支援此請求方法。 | Flask 405 handler（HTTP method 不支援） |
| `RATE_LIMIT_EXCEEDED` | 429 | Too Many Requests | 操作過於頻繁，請稍後再試。 | 超過 Rate Limit（登入 10/min、核銷 30/min） |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error | *(前端未映射)* | 未預期的 500 錯誤 |

---

## 三、錯誤產生機制

### 3.1 直接拋出

Service / Blueprint 層主動 raise：

```python
raise AppError(
    code="EVENT_NOT_FOUND",
    message="Event not found",
    http_status=404,
)
```

### 3.2 RPC Error Mapping

Supabase RPC 可能在 DB 層 `RAISE EXCEPTION`，由 `map_supabase_error()` 自動轉換：

```python
# backend/app/domain/errors.py
_RPC_ERROR_MAP = {
    "AUTH_REQUIRED": (401, "Authentication is required"),
    "SOLD_OUT": (409, "Tickets are sold out"),
    "PER_USER_LIMIT_EXCEEDED": (409, "Per-user limit exceeded"),
    # ... 共 22 組映射
}
```

轉換邏輯：
1. 將 Supabase exception message 轉大寫
2. 依序比對特殊模式（`PERMISSION DENIED FOR FUNCTION`、`COULD NOT FIND THE FUNCTION` 等）
3. 遍歷 `_RPC_ERROR_MAP` 做 substring 匹配
4. 最後比對 `ROW-LEVEL SECURITY` / `FORBIDDEN`
5. 都不匹配時回傳 fallback code（預設 `SUPABASE_ERROR`）

### 3.3 Flask Error Handler

全域錯誤攔截（`backend/app/__init__.py`）：

```python
@app.errorhandler(404)
def not_found(e):
    return AppError(code="NOT_FOUND", ...).to_dict(), 404

@app.errorhandler(429)
def rate_limited(e):
    return AppError(code="RATE_LIMIT_EXCEEDED", ...).to_dict(), 429
```

### 3.4 Pydantic 驗證錯誤

`parse_json()` 攔截 Pydantic `ValidationError`，轉為：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request body",
    "details": [
      { "loc": ["body", "email"], "msg": "field required", "type": "value_error.missing" }
    ]
  }
}
```

---

## 四、前端錯誤處理

### 4.1 `toApiErrorMessage(error, fallback)`

通用 API 錯誤轉中文（`frontend/src/utils/errorMessages.ts`）：

```
收到 API 錯誤
  ↓
HTTP 429? → "操作過於頻繁，請稍後再試。"
  ↓
error.code 在 ERROR_CODE_MAP 中? → 回傳對應中文
  ↓
details.raw 包含已知 code? → 回傳對應中文
  ↓
code === "VALIDATION_ERROR"? → 組合欄位 + 訊息顯示
  ↓
有 message? → 回傳 "message (code)"
  ↓
回傳 fallback
```

### 4.2 `toAuthErrorMessage(error, mode)`

認證專用錯誤處理（登入 / 註冊 / 忘記密碼），額外比對 Supabase Auth 的原始訊息：

| 原始訊息 | 中文 |
|----------|------|
| `invalid login credentials` | 登入失敗：帳號或密碼不正確。 |
| `email not confirmed` | 此帳號尚未完成信箱驗證，請先到信箱點擊確認連結。 |
| `user already registered` | 此 Email 已註冊，請直接 Sign In。 |
| `email address ... invalid` | Email 格式不正確，請輸入有效信箱。 |
| `password should be at least` | 密碼長度不足，至少需要 6 個字元。 |
| `email rate limit` / `over_email_send_rate_limit` | 註冊信寄送過於頻繁，請稍後再試。 |

### 4.3 前端專用 Code（catch-all）

以下 code 僅定義在前端 `ERROR_CODE_MAP` 中，用於前端 try-catch 區塊的 fallback 場景。後端不會直接回傳這些 code，但前端預先映射以確保使用者看到中文提示：

`CREATE_EVENT_FAILED`、`UPDATE_EVENT_FAILED`、`CREATE_TICKET_TYPE_FAILED`、`UPDATE_TICKET_TYPE_FAILED`、`DELETE_TICKET_TYPE_FAILED`、`LIST_TICKETS_FAILED`、`CANCEL_TICKET_FAILED`、`RESEND_TICKET_FAILED`、`REGISTER_FAILED`、`ORDERS_LIST_FAILED`、`ORDER_FETCH_FAILED`、`CANCEL_ORDER_FAILED`、`CHECKIN_VERIFY_FAILED`、`CHECKIN_COMMIT_FAILED`、`ORGANIZER_APPLY_FAILED`、`FORM_UPSERT_FAILED`、`SETTLEMENTS_LIST_FAILED`、`SETTLEMENT_FETCH_FAILED`、`ORGANIZER_PERMISSION_CHECK_FAILED`、`INVALID_ORDER_STATUS_TRANSITION`

---

## 五、快速查找

### 依 HTTP Status 分類

| HTTP Status | Error Codes |
|-------------|-------------|
| **400** | `AUTH_FAILED`, `VALIDATION_ERROR`, `HOLD_ITEMS_EMPTY`, `INVALID_HOLD_MINUTES`, `INVALID_ITEM`, `INVALID_QUANTITY`, `INVALID_EVENT_ID`, `QR_MISMATCH`, `TICKET_TYPE_EVENT_MISMATCH`, `PAID_TICKET_NOT_ALLOWED_IN_MVP1`, `ORDER_ID_REQUIRED`, `TRADE_NO_MISSING`, `REFUND_NOT_SUPPORTED`, `INSUFFICIENT_BALANCE`, `ATTENDEE_NO_EMAIL`, `SUPABASE_ERROR` |
| **401** | `AUTH_REQUIRED`, `AUTH_INVALID` |
| **403** | `FORBIDDEN`, `STAFF_CANNOT_MANAGE`, `ORG_NOT_APPROVED`, `RPC_PERMISSION_DENIED` |
| **404** | `NOT_FOUND`, `EVENT_NOT_FOUND`, `TICKET_TYPE_NOT_FOUND`, `TICKET_NOT_FOUND`, `TICKET_NOT_FOUND_OR_ALREADY_CANCELLED`, `ORDER_NOT_FOUND`, `PAYMENT_NOT_FOUND`, `SETTLEMENT_NOT_FOUND`, `PAYOUT_NOT_FOUND`, `ORGANIZATION_NOT_FOUND`, `MEMBER_NOT_FOUND`, `USER_NOT_FOUND` |
| **405** | `METHOD_NOT_ALLOWED` |
| **409** | `EVENT_NOT_PUBLISHED`, `TICKET_TYPE_INACTIVE`, `SOLD_OUT`, `CAPACITY_EXCEEDED`, `SALE_NOT_STARTED`, `SALE_ENDED`, `PER_USER_LIMIT_EXCEEDED`, `ORDER_NOT_HOLDING`, `ORDER_CANNOT_REFUND`, `PAYMENT_NOT_COMPLETED`, `INVALID_STATUS`, `PAYOUT_ALREADY_PROCESSED`, `PAYOUT_NOT_APPROVED` |
| **429** | `RATE_LIMIT_EXCEEDED` |
| **500** | `CONFIG_ERROR`, `INTERNAL_SERVER_ERROR`, `RPC_NOT_FOUND`, `DB_PATCH_REQUIRED`, `HOLD_ORDER_CREATE_FAILED`, `REFUND_CREATE_FAILED`, `PAYOUT_CREATE_FAILED`, `COMP_TICKET_FAILED`, `FORM_SCHEMA_INVALID` |
| **502** | `AUTH_SERVICE_ERROR`, `REFUND_API_FAILED` |
| **503** | `ECPAY_CONFIG_MISSING` |
