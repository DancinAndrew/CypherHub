# 資料庫 Schema 總覽

> 本文件記錄 CypherHub 所有資料表、欄位定義、關聯、RLS 策略、RPC 函式與 enum 值。
> 依 migration 順序（0001–0027）整理，標註各表所屬 MVP 階段。
> 對應原始碼：`supabase/migrations/`。

---

## 一、架構總覽

```
auth.users (Supabase 內建)
  │
  ├─── profiles              1:1   使用者資料
  ├─── organizer_members     1:N   組織成員關聯
  ├─── tickets               1:N   票券持有
  ├─── orders                1:N   訂單
  └─── ticket_form_responses 1:N   表單回答

organizations
  ├─── organizer_members     1:N   成員
  ├─── events                1:N   活動
  ├─── settlements           1:N   結算
  ├─── ledger_entries        1:N   帳務分錄
  └─── payout_requests       1:N   提款申請

events
  ├─── event_media           1:N   活動圖片
  ├─── event_internal_notes  1:1   私密備註
  ├─── event_forms           1:N   報名表單
  ├─── ticket_types          1:N   票種
  └─── tickets               1:N   票券

orders
  ├─── order_items           1:N   訂單項目
  ├─── payments              1:N   金流紀錄
  ├─── refunds               1:N   退款紀錄
  └─── tickets               1:N   訂單出票

audit_logs                         平台審計日誌
webhook_events                     Webhook 冪等去重
```

### 表與 MVP 階段對照

| MVP | 表 |
|-----|-----|
| MVP-1 | `profiles`, `organizations`, `organizer_members`, `events`, `event_media`, `ticket_types`, `tickets`, `event_internal_notes`, `event_forms`, `ticket_form_responses` |
| MVP-2 | `orders`, `order_items`, `payments`, `webhook_events`, `refunds` |
| MVP-3 | `settlements`, `ledger_entries`, `payout_requests`, `audit_logs` |

---

## 二、Enum 定義

### `organizer_role`

| 值 | 說明 |
|----|------|
| `owner` | 組織擁有者（最高權限） |
| `admin` | 管理員（可建活動、管成員） |
| `staff` | 工作人員（僅核銷與名單） |

### `event_status`

| 值 | 說明 |
|----|------|
| `draft` | 草稿（僅組織成員可見） |
| `published` | 已發布（公開可見） |
| `cancelled` | 已取消 |
| `ended` | 已結束 |
| `disabled` | 已下架（Admin 停用，0015 新增） |

### `ticket_status`

| 值 | 說明 |
|----|------|
| `issued` | 已出票 |
| `checked_in` | 已核銷 |
| `cancelled` | 已取消 |

### `order_status`（MVP-2，0017）

| 值 | 說明 |
|----|------|
| `created` | 初建（過渡狀態） |
| `holding` | 佔位中（名額已扣，等待付款） |
| `pending_payment` | 等待付款確認 |
| `paid` | 已付款（等待出票） |
| `issued` | 已出票完成 |
| `cancelled` | 已取消 |
| `refunded` | 已退款 |

### `payment_status`（MVP-2，0017）

| 值 | 說明 |
|----|------|
| `pending` | 等待中 |
| `completed` | 已完成 |
| `failed` | 失敗 |
| `refunded` | 已退款 |

### `dance_style`（MVP-1.1，0006）

| 值 |
|----|
| `hiphop`, `popping`, `locking`, `house`, `waacking`, `breaking`, `krump`, `voguing`, `freestyle`, `choreo`, `allstyle` |

### `event_type`（MVP-1.1，0006）

| 值 |
|----|
| `cypher`, `battle`, `group_battle`, `workshop`, `jam`, `showcase`, `audition`, `party` |

---

## 三、資料表定義

### 3.1 `profiles`（MVP-1，0001）

使用者個人資料，與 `auth.users` 1:1 對應。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | — | 等同 `auth.users.id` |
| `display_name` | `text` | NOT NULL | — | 顯示名稱 |
| `avatar_url` | `text` | NULL | — | 頭像 URL |
| `phone` | `text` | NULL | — | 電話 |
| `social_links` | `jsonb` | NULL | — | 社群連結（自由格式） |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | 自動更新（trigger） |

**FK**：`id` → `auth.users(id)` ON DELETE CASCADE

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `profiles_select_own` | SELECT | authenticated | `id = auth.uid()` |
| `profiles_update_own` | UPDATE | authenticated | `id = auth.uid()` |
| `profiles_insert_own` | INSERT | authenticated | `id = auth.uid()` |

---

### 3.2 `organizations`（MVP-1，0001 + 0024）

主辦方組織。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `name` | `text` | NOT NULL | — | 組織名稱 |
| `description` | `text` | NULL | — | 說明 |
| `logo_url` | `text` | NULL | — | Logo URL |
| `contact_email` | `text` | NULL | — | 聯絡信箱 |
| `owner_user_id` | `uuid` | NOT NULL | — | 建立者（FK → auth.users 無顯式定義） |
| `approval_status` | `text` | — | `'approved'` | `pending` / `approved` / `rejected`（0024） |
| `approved_at` | `timestamptz` | NULL | — | 審核通過時間（0024） |
| `approved_by` | `uuid` | NULL | — | 審核者（0024） |
| `rejection_reason` | `text` | NULL | — | 駁回原因（0024） |
| `payout_bank_info` | `jsonb` | NULL | — | 銀行帳戶資訊（0024） |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | 自動更新（trigger） |

**索引**：`idx_org_owner(owner_user_id)`

**Trigger**：`trg_org_insert_member` — INSERT 時自動加入 `organizer_members` 為 `owner`。

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `org_select_member` | SELECT | authenticated | `is_org_member(id)` 或 `owner_user_id = auth.uid()` |
| `org_select_public_via_published_event` | SELECT | anon, authenticated | 組織有 `published` 活動時公開可見（0013） |
| `org_insert_owner` | INSERT | authenticated | `owner_user_id = auth.uid()` |
| `org_update_owner_admin` | UPDATE | authenticated | `is_org_admin(id)` 或 `owner_user_id = auth.uid()` |

---

### 3.3 `organizer_members`（MVP-1，0001 + 0025）

組織成員（多對多：organization ↔ user）。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `org_id` | `uuid` PK | NOT NULL | — | FK → `organizations(id)` ON DELETE CASCADE |
| `user_id` | `uuid` PK | NOT NULL | — | FK → `auth.users(id)` ON DELETE CASCADE |
| `role` | `organizer_role` | NOT NULL | — | `owner` / `admin` / `staff` |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**PK**：`(org_id, user_id)` 複合主鍵

**索引**：`idx_org_members_user(user_id)`

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `org_members_select_self_or_admin` | SELECT | authenticated | `user_id = auth.uid()` 或 `is_org_admin(org_id)` |
| `org_members_insert_admin` | INSERT | authenticated | `is_org_admin(org_id)` |
| `org_members_delete_admin` | DELETE | authenticated | `is_org_admin(org_id)` |
| `org_members_update_admin` | UPDATE | authenticated | `is_org_admin(org_id)`（0025） |

---

### 3.4 `events`（MVP-1，0001 + 0006 + 0007）

活動主表。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `org_id` | `uuid` | NOT NULL | — | FK → `organizations(id)` ON DELETE CASCADE |
| `title` | `text` | NOT NULL | — | 活動名稱 |
| `description` | `text` | NULL | — | 詳細說明 |
| `short_desc` | `text` | NULL | — | 簡短描述（0007） |
| `start_at` | `timestamptz` | NOT NULL | — | 開始時間 |
| `end_at` | `timestamptz` | NOT NULL | — | 結束時間 |
| `timezone` | `text` | NULL | — | 時區 |
| `location_name` | `text` | NULL | — | 場地名稱 |
| `location_address` | `text` | NULL | — | 場地地址 |
| `map_url` | `text` | NULL | — | 地圖連結（0007） |
| `rules` | `text` | NULL | — | 比賽規則 |
| `refund_policy` | `text` | NULL | — | 退款政策 |
| `eligibility` | `text` | NULL | — | 參加資格（0007） |
| `event_language` | `text` | NULL | — | 活動語言（0007） |
| `contact_email` | `text` | NULL | — | 聯絡信箱（0007） |
| `contact_phone` | `text` | NULL | — | 聯絡電話（0007） |
| `socials` | `jsonb` | NOT NULL | `'{}'` | 社群連結（0007） |
| `schedule` | `jsonb` | NOT NULL | `'[]'` | 活動流程表（0007） |
| `registration_start_at` | `timestamptz` | NULL | — | 報名開始時間（0007） |
| `registration_end_at` | `timestamptz` | NULL | — | 報名截止時間（0007） |
| `checkin_open_at` | `timestamptz` | NULL | — | 核銷開放時間（0007） |
| `checkin_note` | `text` | NULL | — | 核銷備註（0007） |
| `dance_styles` | `dance_style[]` | NOT NULL | `'{}'` | 舞風標籤（0006） |
| `event_types` | `event_type[]` | NOT NULL | `'{}'` | 活動類型標籤（0006） |
| `status` | `event_status` | NOT NULL | `'draft'` | 活動狀態 |
| `published_at` | `timestamptz` | NULL | — | 發布時間 |
| `created_by` | `uuid` | NOT NULL | — | 建立者 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | 自動更新（trigger） |

**Check Constraint**：`events_time_check` — `end_at > start_at`

**索引**：`idx_events_status_start(status, start_at)`、`idx_events_org(org_id)`、`idx_events_dance_styles_gin` (GIN)、`idx_events_event_types_gin` (GIN)、`idx_events_reg_end`、`idx_events_reg_start`

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `events_select_published_public` | SELECT | anon, authenticated | `status = 'published'` |
| `events_select_org_members` | SELECT | authenticated | `is_org_member(org_id)` |
| `events_insert_org_admin` | INSERT | authenticated | `is_org_admin(org_id)` |
| `events_update_org_admin` | UPDATE | authenticated | `is_org_admin(org_id)` |

---

### 3.5 `event_media`（MVP-1，0001）

活動輪播圖片。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `event_id` | `uuid` | NOT NULL | — | FK → `events(id)` ON DELETE CASCADE |
| `path` | `text` | NOT NULL | — | Storage 路徑 |
| `sort_order` | `int` | NOT NULL | `0` | 排序 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `event_media_select_public` | SELECT | anon, authenticated | 活動 `status = 'published'` |
| `event_media_select_org` | SELECT | authenticated | `is_event_member(event_id)` |
| `event_media_mutate_admin` | ALL | authenticated | `is_event_admin(event_id)` |

---

### 3.6 `event_internal_notes`（MVP-1.5，0008）

活動私密備註（僅組織成員可見）。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `event_id` | `uuid` PK | NOT NULL | — | FK → `events(id)` ON DELETE CASCADE |
| `note` | `text` | NOT NULL | `''` | 備註內容 |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | 自動更新（trigger） |
| `updated_by` | `uuid` | NULL | — | FK → `auth.users(id)` ON DELETE SET NULL |

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `event_internal_notes_select_member` | SELECT | authenticated | `is_event_member(event_id)` |
| `event_internal_notes_insert_admin` | INSERT | authenticated | `is_event_admin(event_id)` |
| `event_internal_notes_update_admin` | UPDATE | authenticated | `is_event_admin(event_id)` |

---

### 3.7 `ticket_types`（MVP-1，0001 + 0017）

票種定義。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `event_id` | `uuid` | NOT NULL | — | FK → `events(id)` ON DELETE CASCADE |
| `name` | `text` | NOT NULL | — | 票種名稱 |
| `description` | `text` | NULL | — | 說明 |
| `price_cents` | `int` | NOT NULL | `0` | 價格（分）。`0` = 免費 |
| `currency` | `text` | NOT NULL | `'TWD'` | 幣別 |
| `capacity` | `int` | NOT NULL | — | 總容量 |
| `sold_count` | `int` | NOT NULL | `0` | 已售數量 |
| `hold_count` | `int` | NOT NULL | `0` | 佔位中數量（0017） |
| `per_user_limit` | `int` | NOT NULL | `1` | 每人限購 |
| `sale_start_at` | `timestamptz` | NULL | — | 開賣時間 |
| `sale_end_at` | `timestamptz` | NULL | — | 停賣時間 |
| `is_active` | `boolean` | NOT NULL | `true` | 是否啟用 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | 自動更新（trigger） |

**Check Constraints**：
- `ticket_types_capacity_check` — `capacity >= 0`
- `ticket_types_inventory_check` — `sold_count >= 0 AND hold_count >= 0 AND sold_count + hold_count <= capacity`（0017 取代原 `ticket_types_sold_check`）
- `ticket_types_limit_check` — `per_user_limit >= 1`

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `ticket_types_select_public` | SELECT | anon, authenticated | `is_active = true` 且活動 `status = 'published'` |
| `ticket_types_select_org` | SELECT | authenticated | `is_event_member(event_id)` |
| `ticket_types_mutate_admin` | ALL | authenticated | `is_event_admin(event_id)` |

---

### 3.8 `tickets`（MVP-1，0001 + 0018）

票券實體（每張票一筆紀錄）。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `event_id` | `uuid` | NOT NULL | — | FK → `events(id)` ON DELETE CASCADE |
| `ticket_type_id` | `uuid` | NOT NULL | — | FK → `ticket_types(id)` ON DELETE CASCADE |
| `user_id` | `uuid` | NOT NULL | — | FK → `auth.users(id)` ON DELETE CASCADE |
| `order_id` | `uuid` | NULL | — | FK → `orders(id)` ON DELETE SET NULL（0018，付費訂單用） |
| `qr_secret` | `text` | NOT NULL | — | QR 碼密鑰（unique） |
| `status` | `ticket_status` | NOT NULL | `'issued'` | 票券狀態 |
| `issued_at` | `timestamptz` | NOT NULL | `now()` | 出票時間 |
| `checked_in_at` | `timestamptz` | NULL | — | 核銷時間 |
| `checker_id` | `uuid` | NULL | — | FK → `auth.users(id)` ON DELETE SET NULL |
| `cancelled_at` | `timestamptz` | NULL | — | 取消時間 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**唯一索引**：`idx_tickets_qr_secret_unique(qr_secret)`

**索引**：`idx_tickets_user`、`idx_tickets_event`、`idx_tickets_type`、`idx_tickets_status`、`idx_tickets_order`

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `tickets_select_own` | SELECT | authenticated | `user_id = auth.uid()` |
| `tickets_select_event_members` | SELECT | authenticated | `is_event_member(event_id)` |

> Tickets 的 INSERT/UPDATE 僅透過 RPC（SECURITY DEFINER），不開放直接操作。

---

### 3.9 `event_forms`（MVP-1.5，0009）

報名表單定義。支援 event-level 或 ticket_type-level 表單。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `event_id` | `uuid` | NOT NULL | — | FK → `events(id)` ON DELETE CASCADE |
| `ticket_type_id` | `uuid` | NULL | — | FK → `ticket_types(id)` ON DELETE CASCADE。NULL = event-level |
| `schema` | `jsonb` | NOT NULL | — | 表單欄位定義 |
| `version` | `int` | NOT NULL | `1` | 版本號 |
| `is_active` | `boolean` | NOT NULL | `true` | 是否啟用 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | 自動更新（trigger） |

**唯一索引**（確保每個 level 只有一個 active form）：
- `idx_event_forms_active_event_level_unique(event_id)` WHERE `is_active = true AND ticket_type_id IS NULL`
- `idx_event_forms_active_ticket_type_unique(ticket_type_id)` WHERE `is_active = true AND ticket_type_id IS NOT NULL`

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `event_forms_select_public_active` | SELECT | anon, authenticated | `is_active` 且活動 published 且票種 active |
| `event_forms_select_org_member` | SELECT | authenticated | `is_event_member(event_id)` |
| `event_forms_insert_admin` | INSERT | authenticated | `is_event_admin(event_id)` |
| `event_forms_update_admin` | UPDATE | authenticated | `is_event_admin(event_id)` |

---

### 3.10 `ticket_form_responses`（MVP-1.5，0009）

報名表單回答（一張票對應一份回答）。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `ticket_id` | `uuid` PK | NOT NULL | — | FK → `tickets(id)` ON DELETE CASCADE |
| `event_id` | `uuid` | NOT NULL | — | FK → `events(id)` ON DELETE CASCADE |
| `ticket_type_id` | `uuid` | NOT NULL | — | FK → `ticket_types(id)` ON DELETE CASCADE |
| `user_id` | `uuid` | NOT NULL | — | FK → `auth.users(id)` ON DELETE CASCADE |
| `form_id` | `uuid` | NOT NULL | — | FK → `event_forms(id)` ON DELETE RESTRICT |
| `answers` | `jsonb` | NOT NULL | `'{}'` | 回答內容 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `ticket_form_responses_select_own` | SELECT | authenticated | `user_id = auth.uid()` |
| `ticket_form_responses_select_org_member` | SELECT | authenticated | `is_event_member(event_id)` |

---

### 3.11 `orders`（MVP-2，0017）

訂單。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `user_id` | `uuid` | NOT NULL | — | FK → `auth.users(id)` ON DELETE CASCADE |
| `status` | `order_status` | NOT NULL | `'created'` | 訂單狀態 |
| `total_cents` | `int` | NOT NULL | `0` | 總金額（分） |
| `currency` | `text` | NOT NULL | `'TWD'` | 幣別 |
| `hold_expires_at` | `timestamptz` | NULL | — | 佔位到期時間 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `updated_at` | `timestamptz` | NOT NULL | `now()` | 自動更新（trigger） |

**索引**：`idx_orders_user`、`idx_orders_status`、`idx_orders_hold_expires(hold_expires_at)` WHERE `status = 'holding'`

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `orders_select_own` | SELECT | authenticated | `user_id = auth.uid()` |
| `orders_insert_own` | INSERT | authenticated | `user_id = auth.uid()` |
| `orders_update_own` | UPDATE | authenticated | `user_id = auth.uid()` |

---

### 3.12 `order_items`（MVP-2，0017）

訂單項目（一個訂單可含多個票種）。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `order_id` | `uuid` | NOT NULL | — | FK → `orders(id)` ON DELETE CASCADE |
| `ticket_type_id` | `uuid` | NOT NULL | — | FK → `ticket_types(id)` |
| `quantity` | `int` | NOT NULL | — | 數量（CHECK `≥ 1`） |
| `price_cents` | `int` | NOT NULL | — | 單價（分） |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `order_items_select_via_order` | SELECT | authenticated | 訂單 `user_id = auth.uid()` |
| `order_items_insert_via_order` | INSERT | authenticated | 訂單 `user_id = auth.uid()` |

---

### 3.13 `payments`（MVP-2，0017）

金流紀錄（Webhook 寫入）。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `order_id` | `uuid` | NOT NULL | — | FK → `orders(id)` ON DELETE CASCADE |
| `provider` | `text` | NOT NULL | — | 金流提供者（如 `ecpay`） |
| `external_id` | `text` | NOT NULL | — | 外部交易編號 |
| `amount_cents` | `int` | NOT NULL | — | 金額（分） |
| `currency` | `text` | NOT NULL | `'TWD'` | 幣別 |
| `status` | `payment_status` | NOT NULL | `'pending'` | 付款狀態 |
| `raw_payload` | `jsonb` | NULL | — | 原始 Webhook payload |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**UNIQUE**：`(provider, external_id)`

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `payments_select_via_order` | SELECT | authenticated | 訂單 `user_id = auth.uid()` |

> INSERT/UPDATE 僅由 backend `service_role` 執行（Webhook 處理），不開放 authenticated。

---

### 3.14 `webhook_events`（MVP-2，0017）

Webhook 冪等去重表。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `provider` | `text` | NOT NULL | — | 來源（如 `ecpay`） |
| `external_event_id` | `text` | NOT NULL | — | 外部事件 ID |
| `event_type` | `text` | NOT NULL | — | 事件類型（如 `payment`） |
| `payload` | `jsonb` | NULL | — | 原始 payload |
| `processed_at` | `timestamptz` | NULL | — | 處理完成時間（NULL = 未處理） |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**UNIQUE**：`(provider, external_event_id)`

**RLS**：已啟用，無任何 policy → authenticated/anon 無法存取，僅 `service_role` bypass。

---

### 3.15 `refunds`（MVP-2，0023）

退款紀錄。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `order_id` | `uuid` | NOT NULL | — | FK → `orders(id)` ON DELETE CASCADE |
| `amount_cents` | `int` | NOT NULL | — | 退款金額（分） |
| `status` | `text` | NOT NULL | `'requested'` | `requested` / `refunded` / `failed` |
| `provider_trade_no` | `text` | NULL | — | ECPay TradeNo |
| `raw_response` | `jsonb` | NULL | — | ECPay 退款回應 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |
| `processed_at` | `timestamptz` | NULL | — | 處理完成時間 |

**RLS**：已啟用，無 policy → 僅 `service_role` 可存取。

---

### 3.16 `settlements`（MVP-3，0026）

結算紀錄（按期間彙總組織收入）。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `org_id` | `uuid` | NOT NULL | — | FK → `organizations(id)` ON DELETE CASCADE |
| `period_start` | `timestamptz` | NOT NULL | — | 結算期間起始 |
| `period_end` | `timestamptz` | NOT NULL | — | 結算期間結束 |
| `gross_cents` | `int` | NOT NULL | `0` | 總收入（分） |
| `platform_fee_cents` | `int` | NOT NULL | `0` | 平台手續費（分） |
| `net_cents` | `int` | NOT NULL | `0` | 淨額（分） |
| `status` | `text` | NOT NULL | `'draft'` | `draft` / `finalized` |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `settlements_select_org_member` | SELECT | authenticated | `is_org_member(org_id)` |

---

### 3.17 `ledger_entries`（MVP-3，0026）

帳務分錄（銷售、退款、手續費、提款）。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `org_id` | `uuid` | NOT NULL | — | FK → `organizations(id)` ON DELETE CASCADE |
| `event_id` | `uuid` | NULL | — | FK → `events(id)` ON DELETE SET NULL |
| `order_id` | `uuid` | NULL | — | FK → `orders(id)` ON DELETE SET NULL |
| `type` | `text` | NOT NULL | — | `sale` / `refund` / `platform_fee` / `payout` |
| `amount_cents` | `int` | NOT NULL | — | 金額（分，可為負） |
| `settlement_id` | `uuid` | NULL | — | FK → `settlements(id)` ON DELETE SET NULL |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `ledger_select_org_member` | SELECT | authenticated | `is_org_member(org_id)` |

---

### 3.18 `payout_requests`（MVP-3，0026）

提款申請。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `org_id` | `uuid` | NOT NULL | — | FK → `organizations(id)` ON DELETE CASCADE |
| `settlement_id` | `uuid` | NULL | — | FK → `settlements(id)` ON DELETE SET NULL |
| `amount_cents` | `int` | NOT NULL | — | 提款金額（分，CHECK `> 0`） |
| `status` | `text` | NOT NULL | `'requested'` | `requested` / `approved` / `paid` / `failed` |
| `requested_at` | `timestamptz` | NOT NULL | `now()` | |
| `processed_at` | `timestamptz` | NULL | — | 處理完成時間 |
| `failure_reason` | `text` | NULL | — | 失敗原因 |

**RLS 策略**：

| 策略名 | 操作 | 角色 | 條件 |
|--------|------|------|------|
| `payout_select_org_member` | SELECT | authenticated | `is_org_member(org_id)` |
| `payout_insert_org_admin` | INSERT | authenticated | `is_org_admin(org_id)` 且 `status = 'requested'` |

---

### 3.19 `audit_logs`（MVP-3，0027）

平台審計日誌。

| 欄位 | 型別 | Nullable | 預設值 | 說明 |
|------|------|----------|--------|------|
| `id` | `uuid` PK | NOT NULL | `gen_random_uuid()` | |
| `actor_type` | `text` | NOT NULL | — | `admin` / `organizer` / `system` |
| `actor_id` | `uuid` | NULL | — | 操作者（user UUID 或 NULL） |
| `action` | `text` | NOT NULL | — | 操作名稱（如 `refund_order`、`comp_ticket`） |
| `resource_type` | `text` | NOT NULL | — | 資源類型（如 `order`、`ticket`、`event`） |
| `resource_id` | `uuid` | NULL | — | 資源 ID |
| `details` | `jsonb` | NULL | — | 額外資訊 |
| `created_at` | `timestamptz` | NOT NULL | `now()` | |

**索引**：`idx_audit_logs_actor`、`idx_audit_logs_resource(resource_type, resource_id)`、`idx_audit_logs_created(created_at DESC)`、`idx_audit_logs_action`

**RLS**：已啟用但無 policy → 僅 `service_role` 可存取。

---

## 四、RPC 函式清單

### 4.1 MVP-1 RPC

| 函式 | 參數 | 回傳 | 權限 | 說明 |
|------|------|------|------|------|
| `register_free(p_ticket_type_id, p_quantity)` | `uuid`, `int DEFAULT 1` | `SETOF tickets` | authenticated | 免費報名：鎖定 ticket_type → 驗證 → 扣量 → 建票（0003，0005 修正 search_path） |
| `register_free_v2(p_ticket_type_id, p_quantity, p_answers)` | `uuid`, `int DEFAULT 1`, `jsonb DEFAULT '{}'` | `SETOF tickets` | authenticated | 含表單回答的免費報名（0011） |
| `verify_ticket_qr(p_event_id, p_ticket_id, p_qr_secret)` | `uuid`, `uuid`, `text` | `jsonb` | authenticated | 核銷驗證（不改狀態），檢查活動狀態（0003，0015 加 disabled 檢查） |
| `commit_checkin(p_event_id, p_ticket_id, p_qr_secret)` | `uuid`, `uuid`, `text` | `jsonb` | authenticated | 核銷確認（issued → checked_in），冪等（0003，0015 加 disabled 檢查） |
| `cancel_ticket(p_ticket_id)` | `uuid` | `SETOF tickets` | authenticated | 使用者取消票券，扣回 sold_count（0012） |

**`register_free` / `register_free_v2` 檢查順序**：

1. `auth.uid()` 非 NULL
2. `p_quantity > 0`
3. ticket_type 存在（`FOR UPDATE` 鎖定）
4. `price_cents = 0`（MVP-1 僅免費）
5. `is_active = true`
6. 活動 `status = 'published'`
7. 銷售窗口（`sale_start_at` / `sale_end_at`）
8. per-user limit
9. capacity（`sold_count + quantity ≤ capacity`）
10. 原子更新 `sold_count` + 建立 tickets

### 4.2 MVP-2 RPC

| 函式 | 參數 | 回傳 | 權限 | 說明 |
|------|------|------|------|------|
| `create_hold_order(p_items, p_hold_minutes)` | `jsonb`, `int DEFAULT 15` | `uuid` | authenticated | 建立 holding 訂單，原子扣 hold_count（0019） |
| `cancel_holding_order(p_order_id)` | `uuid` | `void` | authenticated | 取消 holding 訂單，釋放 hold_count（0021） |
| `issue_tickets_for_order(p_order_id)` | `uuid` | `int` | service_role | 付款後出票，hold→sold，冪等（0020，0022 修正） |
| `release_expired_holds()` | — | `int` | service_role | 逾時 holding → cancelled，釋放 hold_count（0018） |
| `compensate_paid_orders()` | — | `int` | service_role | 補償出票：paid 無票 → 建票 → issued（0018，0022 修正） |

**`create_hold_order` 的 `p_items` 格式**：

```json
[
  { "ticket_type_id": "uuid-string", "quantity": 2 },
  { "ticket_type_id": "uuid-string", "quantity": 1 }
]
```

**`create_hold_order` 檢查順序**：

1. `auth.uid()` 非 NULL
2. `p_items` 非空
3. `p_hold_minutes` 在 1–60 之間
4. 逐項鎖定 ticket_type → 驗證 active / published / sale window
5. capacity 檢查：`sold_count + hold_count + qty ≤ capacity`
6. per-user limit：已持有票券 + 未逾時 holding 數量 + qty ≤ limit
7. 建立 order（status=holding）+ order_items
8. 更新 `hold_count`

### 4.3 RLS Helper Functions

| 函式 | 參數 | 回傳 | 說明 |
|------|------|------|------|
| `is_org_member(p_org_id)` | `uuid` | `boolean` | 當前使用者是否為組織成員 |
| `is_org_admin(p_org_id)` | `uuid` | `boolean` | 當前使用者是否為 owner/admin |
| `is_event_member(p_event_id)` | `uuid` | `boolean` | 當前使用者是否為活動所屬組織的成員 |
| `is_event_admin(p_event_id)` | `uuid` | `boolean` | 當前使用者是否為活動所屬組織的 owner/admin |

所有 helper function 為 `SECURITY DEFINER` + `STABLE`，供 RLS policy 使用。

### 4.4 Utility Functions

| 函式 | 說明 |
|------|------|
| `set_updated_at()` | Trigger function：自動設定 `updated_at = now()` |
| `handle_new_organization()` | Trigger function：建立組織時自動加入 owner 為成員 |
| `rls_auto_enable()` | Event trigger：新建 public schema 表時自動啟用 RLS（0004） |

---

## 五、pg_cron 排程（MVP-2，0018）

| 排程名 | 頻率 | 執行函式 | 說明 |
|--------|------|----------|------|
| `release-expired-holds` | 每分鐘 | `release_expired_holds()` | 釋放逾時的 holding 訂單 |
| `compensate-paid-orders` | 每 5 分鐘 | `compensate_paid_orders()` | 補償已付款但未出票的訂單 |

> 後端另有 Admin API `POST /api/v1/admin/release-expired-holds` 和 `POST /api/v1/admin/compensate-paid-orders` 可手動觸發。

---

## 六、Storage Bucket

| Bucket | 公開 | 大小限制 | 允許 MIME | 說明 |
|--------|------|----------|-----------|------|
| `event-media` | `true` | 5 MB | `image/jpeg`, `image/png`, `image/webp`, `image/gif` | 活動圖片（0014） |

Storage RLS：`event_media_public_read` — 所有人可讀 `bucket_id = 'event-media'`（0016）。

---

## 七、Migration 索引

| # | 檔案 | MVP | 內容摘要 |
|---|------|-----|----------|
| 0001 | `mvp1_init.sql` | 1.0 | 核心表（profiles, organizations, organizer_members, events, event_media, ticket_types, tickets）+ enum + trigger |
| 0002 | `mvp1_rls.sql` | 1.0 | 所有 MVP-1 表的 RLS policy + helper function |
| 0003 | `mvp1_rpc.sql` | 1.0 | `register_free`, `verify_ticket_qr`, `commit_checkin` RPC |
| 0004 | `mvp1_patch_drift.sql` | 1.0 | `rls_auto_enable` event trigger |
| 0005 | `mvp1_patch_register_pgcrypto_search_path.sql` | 1.0 | 修正 `register_free` search_path 加 `extensions` |
| 0006 | `mvp11_event_taxonomy.sql` | 1.1 | `dance_style` / `event_type` enum + events 欄位 + GIN 索引 |
| 0007 | `mvp15a_event_metadata.sql` | 1.5 | events 新增 12 個 metadata 欄位 |
| 0008 | `mvp15a_event_internal_notes.sql` | 1.5 | `event_internal_notes` 表 + RLS |
| 0009 | `mvp15b_forms_tables.sql` | 1.5 | `event_forms` + `ticket_form_responses` 表 |
| 0010 | `mvp15b_forms_rls.sql` | 1.5 | 表單相關 RLS policy |
| 0011 | `mvp15b_register_free_v2_rpc.sql` | 1.5 | `register_free_v2`（含 answers）RPC |
| 0012 | `cancel_ticket_rpc.sql` | 1.5 | `cancel_ticket` RPC |
| 0013 | `org_public_select_for_published_events.sql` | 1.5 | organizations 公開 SELECT（有 published 活動時） |
| 0014 | `storage_event_media_bucket.sql` | 1.5 | `event-media` Storage bucket |
| 0015 | `platform_governance.sql` | 1.5 | event_status 加 `disabled`；verify/commit_checkin 加活動狀態檢查 |
| 0016 | `storage_event_media_public_read.sql` | 1.5 | Storage 公開讀取 policy |
| 0017 | `mvp2_orders_payments_webhooks.sql` | 2.1 | `orders`, `order_items`, `payments`, `webhook_events` 表 + `hold_count` + inventory constraint + RLS |
| 0018 | `mvp2_background_tasks.sql` | 2.4 | tickets 加 `order_id`；`release_expired_holds` + `compensate_paid_orders` RPC；pg_cron 排程 |
| 0019 | `mvp2_create_hold_order_rpc.sql` | 2.1 | `create_hold_order` RPC |
| 0020 | `mvp2_issue_tickets_rpc.sql` | 2.3 | `issue_tickets_for_order` RPC |
| 0021 | `mvp2_cancel_holding_order_rpc.sql` | 2.1 | `cancel_holding_order` RPC |
| 0022 | `mvp23_fix_hold_count_idempotent.sql` | 2.3 | 修正 `issue_tickets_for_order` / `compensate_paid_orders` hold_count 冪等 |
| 0023 | `mvp2_refunds_table.sql` | 2.6 | `refunds` 表 + RLS |
| 0024 | `mvp3_org_approval.sql` | 3.2 | organizations 新增審核欄位 |
| 0025 | `mvp31_organizer_members_update.sql` | 3.1 | organizer_members UPDATE policy |
| 0026 | `mvp3_settlements_ledger_payouts.sql` | 3.3 | `settlements`, `ledger_entries`, `payout_requests` 表 + RLS |
| 0027 | `mvp3_audit_logs.sql` | 3.4 | `audit_logs` 表 |
