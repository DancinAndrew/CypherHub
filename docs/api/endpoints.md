# API 端點總表

> Base URL：`/api/v1`（除 Internal Jobs 為 `/internal`）
> 所有回應 `Content-Type: application/json`，錯誤格式見 [error-codes.md](error-codes.md)。
> 認證機制見 [authentication.md](authentication.md)。

---

## 快速索引

| 分組 | Prefix | 權限 | 說明 |
|------|--------|------|------|
| [Health](#health) | `/api/v1` | Public | 健康檢查 |
| [Auth](#auth) | `/api/v1/auth` | Public | 登入/登出 |
| [Events](#events) | `/api/v1/events` | Public | 活動列表與詳情 |
| [Registration](#registration) | `/api/v1/events` | Auth | 免費報名 |
| [Tickets](#tickets) | `/api/v1/me/tickets` | Auth | 我的票券 |
| [Orders](#orders) | `/api/v1/orders` | Auth | 訂單（Hold/付費） |
| [Payments](#payments) | `/api/v1/payments` | Auth | ECPay 付款 |
| [Webhooks](#webhooks) | `/api/v1/webhooks` | ECPay 驗簽 | 金流回呼 |
| [Me](#me) | `/api/v1/me` | Auth | 個人資訊 |
| [Organizer](#organizer) | `/api/v1/organizer` | Auth + Org | 主辦方管理 |
| [Admin](#admin) | `/api/v1/admin` | Auth + Admin | 平台管理 |
| [Internal Jobs](#internal-jobs) | `/internal/jobs` | X-Cron-Secret | 背景排程 |

**權限標記說明**：
- **Public** — 無需 token
- **Auth** — 需 `Authorization: Bearer <JWT>`
- **Org owner/admin** — Auth + `organizer_members` 表中 role 為 owner 或 admin
- **Org member** — Auth + 組織內任何角色（owner/admin/staff）
- **Admin** — Auth + `ADMIN_ALLOWLIST` 中的 user_id 或 email

---

## Health

### `GET /api/v1/health`

健康檢查。

- **權限**：Public
- **回應 200**：
```json
{ "status": "ok" }
```

---

## Auth

### `POST /api/v1/auth/login`

Email + Password 登入（Supabase Auth proxy）。

- **權限**：Public
- **Rate Limit**：10 per minute
- **Request Body**：
```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```
- **回應 200**：
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "v1.MjA1YzNm...",
  "expires_in": 3600,
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "aud": "authenticated",
    "role": "authenticated"
  }
}
```
- **錯誤**：`AUTH_FAILED`(400)、`AUTH_SERVICE_ERROR`(502)、`CONFIG_ERROR`(500)

---

### `POST /api/v1/auth/logout`

登出（目前為空操作，前端負責清除 session）。

- **權限**：Public
- **回應 204**：空 body

---

## Events

### `GET /api/v1/events`

公開活動列表，支援篩選與排序。

- **權限**：Public
- **Query Parameters**：

| 參數 | 型別 | 說明 |
|------|------|------|
| `q` | string | 關鍵字搜尋（title） |
| `from` | ISO datetime | 開始時間下限 |
| `to` | ISO datetime | 開始時間上限 |
| `org_id` | UUID | 篩選特定主辦方 |
| `styles` | string | 舞風，逗號分隔。可選值：`hiphop`, `popping`, `locking`, `house`, `waacking`, `breaking`, `krump`, `voguing`, `freestyle`, `choreo`, `allstyle` |
| `types` | string | 活動類型，逗號分隔。可選值：`cypher`, `battle`, `group_battle`, `workshop`, `jam`, `showcase`, `audition`, `party` |
| `sort` | string | 排序方式：`start_at`（預設）或 `hot`（依售票數） |

- **回應 200**：
```json
{
  "items": [
    {
      "id": "uuid",
      "org_id": "uuid",
      "title": "Summer Cypher 2025",
      "description": "...",
      "short_desc": "...",
      "start_at": "2025-07-01T18:00:00+08:00",
      "end_at": "2025-07-01T22:00:00+08:00",
      "timezone": "Asia/Taipei",
      "location_name": "台北 Legacy",
      "location_address": "...",
      "status": "published",
      "dance_styles": ["hiphop", "popping"],
      "event_types": ["cypher"],
      "thumbnail_path": "event-media/uuid/cover.jpg",
      "total_sold_count": 42
    }
  ]
}
```

> `total_sold_count` 僅在 `sort=hot` 時回傳。

---

### `GET /api/v1/events/:event_id`

活動詳情（含票種、主辦方資訊、同主辦其他活動）。

- **權限**：Public
- **回應 200**：
```json
{
  "event": { "...EventResponse" },
  "ticket_types": [
    {
      "id": "uuid",
      "event_id": "uuid",
      "name": "一般票",
      "price_cents": 50000,
      "currency": "TWD",
      "capacity": 100,
      "sold_count": 42,
      "per_user_limit": 4,
      "sale_start_at": "...",
      "sale_end_at": "...",
      "is_active": true
    }
  ],
  "event_media": [
    { "id": "uuid", "event_id": "uuid", "path": "event-media/...", "sort_order": 0 }
  ],
  "organizer": {
    "id": "uuid",
    "name": "CypherCrew",
    "description": "...",
    "contact_email": "...",
    "logo_url": "..."
  },
  "other_events": []
}
```

---

### `GET /api/v1/events/:event_id/forms`

取得報名表單 schema（公開端點，供前端渲染 DynamicForm）。

- **權限**：Public
- **Query Parameters**：

| 參數 | 型別 | 說明 |
|------|------|------|
| `ticket_type_id` | UUID | 選填，取特定票種的表單 |

- **回應 200**：
```json
{
  "form": {
    "id": "uuid",
    "event_id": "uuid",
    "ticket_type_id": null,
    "schema": {
      "version": 1,
      "fields": [
        {
          "key": "dancer_name",
          "label": "舞名",
          "type": "text",
          "required": true,
          "help_text": null,
          "placeholder": "輸入你的舞名",
          "options": [],
          "validation": null
        }
      ]
    },
    "version": 1,
    "is_active": true
  }
}
```

表單欄位型別：`text`, `number`, `email`, `phone`, `url`, `single_select`, `multi_select`, `dropdown`, `date`, `checkbox`

---

## Registration

### `POST /api/v1/events/:event_id/register`

免費票報名（透過 `register_free_v2` RPC，原子操作）。

- **權限**：Auth
- **Rate Limit**：20 per minute
- **Request Body**：
```json
{
  "ticket_type_id": "uuid",
  "quantity": 1,
  "answers": {
    "dancer_name": "B-Boy Ken",
    "crew": "CypherCrew"
  }
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `ticket_type_id` | UUID | 是 | 票種 ID |
| `quantity` | int | 否 | 數量（1-10，預設 1） |
| `answers` | object | 否 | 表單回答 |

- **回應 200**：
```json
{
  "tickets": [
    {
      "ticket_id": "uuid",
      "event_id": "uuid",
      "ticket_type_id": "uuid",
      "user_id": "uuid",
      "status": "issued",
      "qr_secret": "abc123...",
      "issued_at": "2025-03-20T10:00:00Z",
      "checked_in_at": null
    }
  ]
}
```
- **副作用**：成功後自動寄送報名成功 Email
- **錯誤**：`SOLD_OUT`(409)、`EVENT_NOT_PUBLISHED`(409)、`TICKET_TYPE_INACTIVE`(409)、`SALE_NOT_STARTED`(409)、`SALE_ENDED`(409)、`PER_USER_LIMIT_EXCEEDED`(409)

---

## Tickets

### `GET /api/v1/me/tickets`

我的所有票券。

- **權限**：Auth
- **回應 200**：
```json
{
  "items": [
    {
      "ticket_id": "uuid",
      "event_id": "uuid",
      "ticket_type_id": "uuid",
      "user_id": "uuid",
      "status": "issued",
      "qr_secret": "abc123...",
      "issued_at": "...",
      "checked_in_at": null
    }
  ]
}
```

---

### `DELETE /api/v1/me/tickets/:ticket_id`

取消自己的票（透過 `cancel_ticket` RPC）。

- **權限**：Auth
- **回應 200**：
```json
{ "ok": true }
```
- **錯誤**：`TICKET_NOT_FOUND_OR_ALREADY_CANCELLED`(404)

---

### `POST /api/v1/me/tickets/:ticket_id/resend`

重寄票券 Email（含 QR Code）。

- **權限**：Auth
- **回應 200**：
```json
{ "ok": true }
```

---

## Orders

### `POST /api/v1/orders/`

建立 holding 訂單（選票種、原子扣 hold_count）。15 分鐘內未付款自動釋放。

- **權限**：Auth
- **Request Body**：
```json
{
  "items": [
    { "ticket_type_id": "uuid", "quantity": 2 }
  ],
  "hold_minutes": 15
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `items` | array | 是 | 至少一項 |
| `items[].ticket_type_id` | UUID | 是 | 票種 ID |
| `items[].quantity` | int | 是 | 數量（1-20） |
| `hold_minutes` | int | 否 | 保留時間（1-60 分鐘，預設 15） |

- **回應 201**：
```json
{
  "order": {
    "id": "uuid",
    "user_id": "uuid",
    "status": "holding",
    "total_cents": 100000,
    "currency": "TWD",
    "hold_expires_at": "2025-03-20T10:15:00Z",
    "created_at": "...",
    "updated_at": "..."
  },
  "items": [
    {
      "id": "uuid",
      "order_id": "uuid",
      "ticket_type_id": "uuid",
      "quantity": 2,
      "price_cents": 50000,
      "created_at": "..."
    }
  ],
  "payments": []
}
```
- **錯誤**：`SOLD_OUT`(409)、`HOLD_ITEMS_EMPTY`(400)、`INVALID_HOLD_MINUTES`(400)

---

### `GET /api/v1/orders/`

列出自己的訂單。

- **權限**：Auth
- **回應 200**：
```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "status": "holding",
      "total_cents": 100000,
      "currency": "TWD",
      "hold_expires_at": "...",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

---

### `GET /api/v1/orders/:order_id`

訂單詳情（含 items + payments）。

- **權限**：Auth
- **回應 200**：同 `POST /orders/` 回應格式
- **錯誤**：`ORDER_NOT_FOUND`(404)

---

### `DELETE /api/v1/orders/:order_id`

取消自己的 holding 訂單，釋放名額。

- **權限**：Auth
- **回應 200**：
```json
{ "ok": true }
```
- **錯誤**：`ORDER_NOT_FOUND`(404)、`ORDER_NOT_HOLDING`(409)

---

## Payments

### `POST /api/v1/payments/checkout`

為 holding 訂單建立 ECPay 付款（取得綠界金流表單參數）。

- **權限**：Auth
- **Request Body**：
```json
{ "order_id": "uuid" }
```
- **回應 200**：
```json
{
  "form_params": {
    "MerchantID": "...",
    "MerchantTradeNo": "...",
    "CheckMacValue": "...",
    "...": "..."
  },
  "cashier_url": "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"
}
```

> 前端收到後建立隱藏 form POST 導向 `cashier_url`。

- **錯誤**：`ORDER_ID_REQUIRED`(400)、`ORDER_NOT_FOUND`(404)

---

## Webhooks

### `POST /api/v1/webhooks/ecpay`

綠界金流 ReturnURL 回呼。由 ECPay 伺服器呼叫，非前端。

- **權限**：ECPay CheckMacValue 驗簽（無 JWT）
- **Content-Type**：`application/x-www-form-urlencoded`
- **處理流程**：驗簽 → 冪等檢查（`webhook_events`） → paid 時觸發出票
- **回應**：純文字 `1|OK`（ECPay 規格要求）

---

## Me

### `GET /api/v1/me/organizer-summary`

取得當前使用者的主辦方身份與其活動列表。

- **權限**：Auth
- **回應 200**：
```json
{
  "organizations": [
    {
      "id": "uuid",
      "name": "CypherCrew",
      "role": "owner",
      "approval_status": "approved"
    }
  ],
  "events": [
    {
      "id": "uuid",
      "org_id": "uuid",
      "title": "Summer Cypher",
      "status": "published",
      "start_at": "..."
    }
  ]
}
```

---

## Organizer

所有路徑前綴 `/api/v1/organizer`。

### 申請主辦方

#### `POST /api/v1/organizer/apply`

申請成為主辦方。`ORG_APPROVAL_REQUIRED=True` 時新組織為 `pending`。

- **權限**：Auth
- **Request Body**：
```json
{
  "name": "CypherCrew",
  "description": "專注街舞活動的團隊",
  "contact_email": "crew@example.com",
  "logo_url": "https://..."
}
```
- **回應 201**：
```json
{
  "organization": {
    "id": "uuid",
    "name": "CypherCrew",
    "approval_status": "pending",
    "..."
  }
}
```

---

### 活動管理

#### `POST /api/v1/organizer/events`

建立活動。

- **權限**：Org owner/admin（且組織需 `approved`）
- **Request Body**：
```json
{
  "org_id": "uuid",
  "title": "Summer Cypher 2025",
  "start_at": "2025-07-01T18:00:00+08:00",
  "end_at": "2025-07-01T22:00:00+08:00",
  "location_name": "台北 Legacy",
  "location_address": "台北市中正區...",
  "dance_styles": ["hiphop", "popping"],
  "event_types": ["cypher"],
  "status": "draft"
}
```

完整欄位請參考 `CreateEventRequest` schema（所有 `EventResponse` 欄位除 `id`、`published_at` 外均可填入，選填欄位可省略）。

- **回應 201**：
```json
{ "event": { "...EventResponse" } }
```
- **錯誤**：`STAFF_CANNOT_MANAGE`(403)、`ORG_NOT_APPROVED`(403)

---

#### `PATCH /api/v1/organizer/events/:event_id`

更新活動（部分更新）。

- **權限**：Org owner/admin
- **Request Body**：僅需傳要更新的欄位
```json
{
  "title": "Updated Title",
  "status": "published",
  "published_at": "2025-03-20T12:00:00Z"
}
```
- **回應 200**：
```json
{ "event": { "...EventResponse" } }
```

---

#### `GET /api/v1/organizer/events/:event_id`

主辦方活動詳情（含 internal_note、event_media、ticket_types）。

- **權限**：Org member
- **回應 200**：
```json
{
  "event": { "...EventResponse" },
  "internal_note": "VIP 入場請走後門",
  "event_media": [],
  "ticket_types": []
}
```

---

#### `PATCH/PUT /api/v1/organizer/events/:event_id/internal-note`

更新活動私密備註。

- **權限**：Org owner/admin
- **Request Body**：
```json
{ "note": "VIP 入場請走後門" }
```
- **回應 200**：
```json
{
  "event_id": "uuid",
  "note": "VIP 入場請走後門",
  "updated_at": "...",
  "updated_by": "uuid"
}
```

---

### 票種管理

#### `POST /api/v1/organizer/events/:event_id/ticket-types`

建立票種。

- **權限**：Org owner/admin
- **Request Body**：
```json
{
  "name": "一般票",
  "price_cents": 50000,
  "capacity": 100,
  "per_user_limit": 4,
  "sale_start_at": "2025-06-01T00:00:00Z",
  "sale_end_at": "2025-06-30T23:59:59Z",
  "is_active": true
}
```

| 欄位 | 型別 | 必填 | 預設 | 說明 |
|------|------|------|------|------|
| `name` | string | 是 | — | 票種名稱 |
| `price_cents` | int | 否 | 0 | 價格（分），0 = 免費 |
| `capacity` | int | 是 | — | 總容量 |
| `per_user_limit` | int | 否 | 1 | 每人限購 |
| `sale_start_at` | datetime | 否 | null | 開賣時間 |
| `sale_end_at` | datetime | 否 | null | 結束售票 |
| `is_active` | bool | 否 | true | 是否啟用 |

- **回應 201**：
```json
{ "ticket_type": { "...TicketTypeResponse" } }
```

---

#### `PATCH /api/v1/organizer/events/:event_id/ticket-types/:ticket_type_id`

更新票種（部分更新）。

- **權限**：Org owner/admin
- **回應 200**：
```json
{ "ticket_type": { "...TicketTypeResponse" } }
```

---

#### `DELETE /api/v1/organizer/events/:event_id/ticket-types/:ticket_type_id`

刪除票種。

- **權限**：Org owner/admin
- **回應 204**：
```json
{ "ok": true }
```

---

### 表單管理

#### `GET /api/v1/organizer/events/:event_id/forms`

列出活動的所有表單。

- **權限**：Org owner/admin
- **回應 200**：
```json
{
  "items": [
    {
      "id": "uuid",
      "event_id": "uuid",
      "ticket_type_id": null,
      "schema": { "version": 1, "fields": [...] },
      "version": 1,
      "is_active": true,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

---

#### `POST /api/v1/organizer/events/:event_id/forms`

建立或更新表單（upsert）。

- **權限**：Org owner/admin
- **Request Body**：
```json
{
  "ticket_type_id": null,
  "schema": {
    "version": 1,
    "fields": [
      {
        "key": "dancer_name",
        "label": "舞名",
        "type": "text",
        "required": true
      },
      {
        "key": "level",
        "label": "程度",
        "type": "single_select",
        "required": true,
        "options": ["初學", "中級", "進階"]
      }
    ]
  },
  "is_active": true
}
```
- **回應 201**：
```json
{ "form": { "...EventFormResponse" } }
```

---

### 名單與核銷

#### `GET /api/v1/organizer/events/:event_id/attendees`

查看活動參加者名單。

- **權限**：Org member（owner/admin/staff 皆可）
- **Query Parameters**：

| 參數 | 型別 | 說明 |
|------|------|------|
| `query` | string | 搜尋關鍵字 |

- **回應 200**：
```json
{
  "items": [
    {
      "ticket_id": "uuid",
      "user_id": "uuid",
      "status": "issued",
      "checked_in_at": null,
      "ticket_type_id": "uuid",
      "answers": { "dancer_name": "B-Boy Ken" },
      "ticket_type_name": "一般票",
      "user_display_name": "Ken"
    }
  ]
}
```

---

#### `POST /api/v1/organizer/events/:event_id/attendees/:ticket_id/resend`

主辦方替參加者重寄票券 Email。

- **權限**：Org member
- **回應 200**：
```json
{ "ok": true }
```

---

#### `POST /api/v1/organizer/events/:event_id/checkin/verify`

驗證 QR Code（不執行核銷，僅回傳票券資訊）。

- **權限**：Org member
- **Rate Limit**：60 per minute
- **Request Body**（三選一）：
```json
{ "ticket_id": "uuid", "qr_secret": "abc123" }
```
或：
```json
{ "qr_payload": "ticket_id:qr_secret" }
```
- **回應 200**：票券詳情（status、user 資訊等）
- **錯誤**：`QR_MISMATCH`(400)、`TICKET_NOT_FOUND`(404)

---

#### `POST /api/v1/organizer/events/:event_id/checkin/commit`

確認核銷（更新 `checked_in_at`）。

- **權限**：Org member
- **Rate Limit**：60 per minute
- **Request Body**：同 verify
- **回應 200**：核銷結果
- **錯誤**：`INVALID_STATUS`(409)（已核銷或已取消）

---

### Comp 票（公關票）

#### `POST /api/v1/organizer/events/:event_id/comp-ticket`

手動補票。提供 `email` 或 `user_id` 其一。

- **權限**：Org owner/admin
- **Request Body**：
```json
{
  "ticket_type_id": "uuid",
  "email": "vip@example.com",
  "note": "VIP 公關票"
}
```
- **回應 201**：
```json
{ "ticket": { "..." } }
```
- **副作用**：寫入 `audit_logs`

---

### 圖片上傳

#### `POST /api/v1/organizer/events/:event_id/media`

上傳活動圖片（Supabase Storage）。

- **權限**：Org owner/admin
- **Content-Type**：`multipart/form-data`
- **Body**：`file` 欄位（max 5MB）
- **回應 201**：
```json
{ "media": { "id": "uuid", "event_id": "uuid", "path": "event-media/...", "sort_order": 0 } }
```

---

### 成員管理（MVP-3.1）

#### `GET /api/v1/organizer/organizations/:org_id/members`

列出主辦方成員。

- **權限**：Org owner/admin
- **回應 200**：
```json
{
  "items": [
    { "user_id": "uuid", "org_id": "uuid", "role": "owner", "created_at": "..." },
    { "user_id": "uuid", "org_id": "uuid", "role": "staff", "created_at": "..." }
  ]
}
```

---

#### `POST /api/v1/organizer/organizations/:org_id/members`

新增成員。

- **權限**：Org owner/admin
- **Request Body**：
```json
{
  "user_id": "uuid",
  "role": "staff"
}
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `user_id` | UUID | 要新增的使用者 |
| `role` | string | `admin` 或 `staff`（不可直接新增 owner） |

- **回應 201**：
```json
{ "member": { "user_id": "uuid", "org_id": "uuid", "role": "staff" } }
```

---

#### `PATCH /api/v1/organizer/organizations/:org_id/members/:user_id`

更新成員角色。

- **權限**：Org owner/admin（admin 不可修改 owner）
- **Request Body**：
```json
{ "role": "admin" }
```
- **回應 200**：
```json
{ "member": { "..." } }
```
- **錯誤**：`FORBIDDEN`(403)（admin 嘗試修改 owner）

---

#### `DELETE /api/v1/organizer/organizations/:org_id/members/:user_id`

移除成員。

- **權限**：Org owner/admin
- **回應 204**：
```json
{ "ok": true }
```
- **錯誤**：`FORBIDDEN`(403)（嘗試移除唯一 owner）

---

### 結算與提款（MVP-3.3）

#### `GET /api/v1/organizer/settlements`

列出自己組織的結算。

- **權限**：Auth（自動篩選到自己所屬 org）
- **回應 200**：
```json
{
  "items": [
    {
      "id": "uuid",
      "org_id": "uuid",
      "period_start": "...",
      "period_end": "...",
      "gross_cents": 500000,
      "platform_fee_cents": 25000,
      "net_cents": 475000,
      "status": "finalized",
      "created_at": "..."
    }
  ]
}
```

---

#### `GET /api/v1/organizer/settlements/:settlement_id`

單筆結算明細。

- **權限**：Auth（需屬於該 org）
- **回應 200**：結算詳情

---

#### `POST /api/v1/organizer/payout-requests`

申請提款。

- **權限**：Auth（需屬於該 org）
- **Request Body**：
```json
{
  "org_id": "uuid",
  "amount_cents": 475000
}
```
- **回應 201**：
```json
{
  "payout_request": {
    "id": "uuid",
    "org_id": "uuid",
    "amount_cents": 475000,
    "status": "pending",
    "requested_at": "..."
  }
}
```

---

## Admin

所有路徑前綴 `/api/v1/admin`。所有端點需 `@require_auth` + `_ensure_admin()`。

### 活動管理

#### `GET /api/v1/admin/events`

全站活動列表。

- **Query Parameters**：

| 參數 | 型別 | 說明 |
|------|------|------|
| `q` | string | 關鍵字搜尋 |
| `from` | ISO datetime | 開始時間下限 |
| `to` | ISO datetime | 開始時間上限 |
| `org_id` | UUID | 篩選主辦方 |

- **回應 200**：
```json
{ "items": [ { "...EventResponse" } ] }
```

---

#### `PATCH /api/v1/admin/events/:event_id`

下架活動。

- **Request Body**：
```json
{ "status": "disabled" }
```

`status` 僅接受 `disabled` 或 `cancelled`。

- **回應 200**：
```json
{ "event": { "..." } }
```
- **副作用**：下架/取消時觸發參加者通知 Email、寫入 `audit_logs`

---

### 訂單管理

#### `GET /api/v1/admin/orders`

全站訂單查詢（分頁）。

- **Query Parameters**：

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `q` | string | — | 關鍵字 |
| `status` | string | — | 訂單狀態篩選 |
| `from` | ISO datetime | — | 建立時間下限 |
| `to` | ISO datetime | — | 建立時間上限 |
| `org_id` | UUID | — | 篩選主辦方 |
| `event_id` | UUID | — | 篩選活動 |
| `limit` | int | 50 | 每頁筆數（max 100） |
| `offset` | int | 0 | 跳過筆數 |

- **回應 200**：
```json
{ "items": [ { "...order data" } ] }
```

---

#### `POST /api/v1/admin/orders/:order_id/refund`

全額退款。

- **回應 200**：退款結果
- **副作用**：建立 `refunds` 記錄、寫入 `audit_logs`

---

### 組織管理（MVP-3.2）

#### `GET /api/v1/admin/organizations`

主辦方列表。

- **Query Parameters**：

| 參數 | 型別 | 說明 |
|------|------|------|
| `status` | string | `pending`、`approved` 或 `rejected` |

- **回應 200**：
```json
{ "items": [ { "id": "uuid", "name": "...", "approval_status": "pending", "..." } ] }
```

---

#### `PATCH /api/v1/admin/organizations/:org_id/approval`

審核主辦方入駐。

- **Request Body**：
```json
{ "status": "approved" }
```
或：
```json
{ "status": "rejected", "rejection_reason": "資料不完整" }
```
- **回應 200**：
```json
{ "organization": { "..." } }
```

---

### 結算與提款（MVP-3.3）

#### `POST /api/v1/admin/settlements/generate`

產生結算批次。

- **Request Body**：
```json
{
  "period_start": "2025-03-01T00:00:00Z",
  "period_end": "2025-03-31T23:59:59Z"
}
```
- **回應 200**：
```json
{ "settlements": [ { "..." } ], "count": 3 }
```

---

#### `GET /api/v1/admin/payout-requests`

提款申請列表。

- **Query Parameters**：

| 參數 | 型別 | 說明 |
|------|------|------|
| `status` | string | 篩選狀態 |

- **回應 200**：
```json
{ "items": [ { "...PayoutRequestResponse" } ] }
```

---

#### `PATCH /api/v1/admin/payout-requests/:payout_id`

核准、退件或標記已付款。

- **Request Body**：
```json
{ "action": "approve" }
```
或：
```json
{ "action": "reject", "failure_reason": "帳戶資訊有誤" }
```
或：
```json
{ "action": "mark_paid" }
```
- **回應 200**：
```json
{ "payout_request": { "..." } }
```

---

### Comp 票

#### `POST /api/v1/admin/events/:event_id/comp-ticket`

Admin 手動補票（跳過組織權限檢查）。

- **Request Body**：同 Organizer comp-ticket
- **回應 201**：
```json
{ "ticket": { "..." } }
```

---

### 背景任務

#### `POST /api/v1/admin/compensate-paid-orders`

手動觸發 paid → issued 補償（處理出票失敗的訂單）。

- **回應 200**：
```json
{ "orders_compensated": 2 }
```

---

#### `POST /api/v1/admin/release-expired-holds`

手動觸發 hold 逾時釋放。

- **回應 200**：
```json
{ "orders_released": 5 }
```

---

## Internal Jobs

### `POST /internal/jobs/event-reminders`

活動提醒排程（前一天 + 前一小時）。由外部 cron 服務呼叫。

- **權限**：`X-Cron-Secret` header 需與 `CRON_SECRET` 環境變數一致
- **回應 200**：
```json
{ "1_day": 3, "1_hour": 1 }
```
- **回應 401**（無 secret 或不符）：
```json
{ "error": "Unauthorized" }
```

---

## 共通錯誤格式

所有 API 錯誤遵循統一格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { "...optional extra info" }
  }
}
```

完整 error code 對照表見 [error-codes.md](error-codes.md)。

---

## 訂單狀態機

```
created → holding → pending_payment → paid → issued
              ↓                         ↓
          cancelled                  refunded
```

| 狀態 | 說明 |
|------|------|
| `created` | 初始（目前不直接使用） |
| `holding` | 名額已保留，等待付款 |
| `pending_payment` | 已送出付款請求 |
| `paid` | 已收款，等待出票 |
| `issued` | 已出票完成 |
| `cancelled` | 已取消（手動或逾時） |
| `refunded` | 已退款 |

---

## Enum 值參考

### DanceStyle（舞風）
`hiphop`, `popping`, `locking`, `house`, `waacking`, `breaking`, `krump`, `voguing`, `freestyle`, `choreo`, `allstyle`

### EventType（活動類型）
`cypher`, `battle`, `group_battle`, `workshop`, `jam`, `showcase`, `audition`, `party`

### FormFieldType（表單欄位）
`text`, `number`, `email`, `phone`, `url`, `single_select`, `multi_select`, `dropdown`, `date`, `checkbox`
