# MVP-3 完整開發計畫

> 對應 develop.md 631-709。平台化：主辦方細權限、入駐審核、結算提款、Audit 治理。
> 本文件為開發主軸，所有實作、測試、驗收皆依此執行。

---

## 一、總覽與依賴

### 1.1 前置條件（必須已存在）

| 項目 | 狀態 | 備註 |
|------|------|------|
| MVP-1 核心閉環 | ✅ | 活動、報名、出票、核銷 |
| MVP-2 訂單/金流/退款 | ✅ | orders, payments, refunds |
| organizer_members.role | ✅ | 已有 owner/admin/staff enum |
| RLS org policies | ✅ | owner/admin 可管理，staff 經 is_event_member |
| organizations 表 | ✅ | owner_user_id, contact_email 等 |

### 1.2 執行順序（強依賴）

```
MVP-3.1 主辦方成員細權限
    ↓
MVP-3.2 主辦方入駐審核
    ↓
MVP-3.3 結算與提款
    ↓
MVP-3.4 平台治理與 Audit
    ↓
MVP-3.5 使用者端擴充（可選）
```

### 1.3 架構評估提醒

> develop.md：實作 MVP-3.4「全站訂單總覽、進階報表」時，若 REST endpoint 過多或參數過胖，需評估 GraphQL/BFF。  
> MVP-3 階段先以 REST 擴充；若單一列表 API 參數超過 10 個再考慮。

---

## 二、MVP-3.1 主辦方成員細權限

### 2.1 規格摘要

| 角色 | 可執行操作 | 限制 |
|------|------------|------|
| **owner** | 全權：建立/編輯活動、票種、表單、核銷、成員、結算設定 | 無 |
| **admin** | 管理活動、票種、表單、核銷、成員 | 不可改結算/收款設定 |
| **staff** | 僅核銷、查看名單 | 不可建立/編輯活動、票種、表單、成員 |

### 2.2 現況分析

| 項目 | 現況 | 待調整 |
|------|------|--------|
| organizer_members.role | owner/admin/staff 已存在 | - |
| RLS org_update_owner_admin | owner/admin 可更新 org | - |
| RLS org_members_insert_admin | owner/admin 可新增成員 | - |
| is_event_member | 任一 org 成員可核銷 | staff 也通過 ✅ |
| 建立活動 | apply_organizer 後即可 | 需加：非 staff 才可建立 |
| 編輯活動/票種/表單 | owner/admin 可 | staff 應 403 ✅ (RLS) |
| 結算設定 | 尚無 | MVP-3.3 再加；admin 限制屆時實作 |

### 2.3 待實作項目

1. **organizer_staff_events 表**（可選進階）
   - 若需「staff 僅能核銷指定活動」：`(org_id, user_id, event_id)` 限制範圍
   - MVP 簡化：staff 可核銷該 org 所有活動，不建此表

2. **API 權限檢查**
   - `POST /organizer/events`：role IN (owner, admin) 才可
   - `PATCH /organizer/events/:id`：同上
   - `POST /organizer/events/:id/ticket-types`：同上
   - `GET/POST/PATCH /organizer/events/:id/forms`：同上
   - `GET /organizer/events/:id/attendees`：owner/admin/staff 皆可
   - `POST verify/commit checkin`：owner/admin/staff 皆可（is_event_member）

3. **成員管理 API**
   - `GET /organizer/organizations/:orgId/members`：owner/admin 可看
   - `POST /organizer/organizations/:orgId/members`：owner/admin 可新增（role=admin|staff）
   - `PATCH /organizer/organizations/:orgId/members/:userId`：owner 可改 role；admin 不可改 owner
   - `DELETE /organizer/organizations/:orgId/members/:userId`：owner/admin 可刪（不可刪自己為唯一 owner）

4. **前端**
   - 主辦方後台：依 role 顯示/隱藏「建立活動」「成員管理」
   - staff 登入後僅見「核銷」「名單」，無活動建立入口

### 2.4 DB 變更

- 無 migration（若不做 organizer_staff_events）
- 若有：`0024_mvp3_organizer_staff_events.sql`

### 2.5 驗收檢查表

- [x] staff 無法呼叫建立活動 API → 403 STAFF_CANNOT_MANAGE
- [x] staff 可核銷、可看名單（RLS is_event_member 允許）
- [ ] admin 可管理活動、不可改結算（待 3.3 有結算欄位後驗證）
- [x] owner/admin 可新增/刪除成員、owner 可改 role（成員管理 API 已實作）
- [x] 前端依 role 顯示正確導航（OrganizerHomeView 依 canManage 隱藏建立/編輯/表單）

---

## 三、MVP-3.2 主辦方入駐審核

### 3.1 規格摘要

| 項目 | 說明 |
|------|------|
| 申請狀態 | pending / approved / rejected |
| Admin 審核 | 通過/退件 API |
| 通過後 | 才可建立活動 |
| 收款資訊 | 銀行帳戶等，審核時或通過後填寫 |

### 3.2 DB 設計

**organizations 擴充**

| 欄位 | 型別 | 說明 |
|------|------|------|
| approval_status | text | pending / approved / rejected |
| approved_at | timestamptz | 審核通過時間 |
| approved_by | uuid | Admin user_id |
| rejection_reason | text | 退件原因（可選） |

**organization_bank_accounts**（或 organizations 內 JSONB）

| 欄位 | 型別 | 說明 |
|------|------|------|
| org_id | uuid | FK organizations |
| bank_code | text | 銀行代碼 |
| branch_code | text | 分行代碼 |
| account_number | text | 帳號 |
| account_holder | text | 戶名 |
| is_default | bool | 預設收款帳戶 |

簡化：`organizations.payout_bank_info jsonb` 單一 JSON 儲存，MVP 足用。

### 3.3 Migration

**0024_mvp3_org_approval.sql**

```sql
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS approval_status text
  DEFAULT 'approved' CHECK (approval_status IN ('pending','approved','rejected'));
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS approved_at timestamptz;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS approved_by uuid;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS rejection_reason text;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS payout_bank_info jsonb;

-- 既有 org 設為 approved
UPDATE organizations SET approval_status = 'approved' WHERE approval_status IS NULL;
```

### 3.4 流程變更

1. **apply_organizer**：建立 org 時 `approval_status = 'pending'`（或保留免審核：預設 approved，由 config 決定）
2. **建立活動**：檢查 `approval_status = 'approved'`
3. **Admin API**：`PATCH /admin/organizations/:id/approval` body: `{ status: 'approved'|'rejected', rejection_reason?: string }`

### 3.5 驗收

- [x] 新申請 org → pending（ORG_APPROVAL_REQUIRED=True 時）
- [x] Admin 可審核通過/退件（GET /admin/organizations、PATCH /admin/organizations/:id/approval）
- [x] 僅 approved 可建立活動（_require_org_approved）
- [x] payout_bank_info 欄位已加（表單可選實作）

---

## 四、MVP-3.3 結算與提款

### 4.1 規格摘要

| 項目 | 說明 |
|------|------|
| settlements 表 | 週期、金額、平台費、淨額 |
| ledger_entries | 每筆交易分錄 |
| payout_requests | 提款申請 requested/approved/paid/failed |
| 平台抽成 | 可設定比例 |

### 4.2 DB 設計

**platform_settings**（或 env/config）

- platform_fee_rate: decimal 例如 0.05 = 5%
- 可建表或放 config，MVP 先用環境變數 `PLATFORM_FEE_RATE=0.05`

**settlements**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | uuid | PK |
| org_id | uuid | FK |
| period_start | timestamptz | 結算區間起 |
| period_end | timestamptz | 結算區間迄 |
| gross_cents | int | 總收入 |
| platform_fee_cents | int | 平台抽成 |
| net_cents | int | 淨額 |
| status | text | draft / finalized |
| created_at | timestamptz | |

**ledger_entries**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | uuid | PK |
| org_id | uuid | |
| event_id | uuid | 可選 |
| order_id | uuid | 可選 |
| type | text | sale / refund / platform_fee / payout |
| amount_cents | int | 正負 |
| settlement_id | uuid | 可選，歸屬哪個結算批次 |
| created_at | timestamptz | |

**payout_requests**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | uuid | PK |
| org_id | uuid | |
| settlement_id | uuid | 可選，或直接指定金額 |
| amount_cents | int | |
| status | text | requested / approved / paid / failed |
| requested_at | timestamptz | |
| processed_at | timestamptz | |
| failure_reason | text | |

### 4.3 流程

1. **結算批次**：定時或手動 job，將 period 內已付訂單彙總，計算 platform_fee，寫入 settlements + ledger_entries
2. **提款申請**：主辦方從可用餘額（ledger 加總 - 已 payout）申請，建立 payout_request status=requested
3. **Admin 審核**：核准 → approved，執行轉帳（或標記 paid 模擬）
4. **失敗**：status=failed，failure_reason

### 4.4 Migrations

- 0025_mvp3_settlements_ledger_payouts.sql

### 4.5 API

- `GET /organizer/settlements`：主辦方看自己結算列表
- `GET /organizer/settlements/:id`：結算明細
- `POST /organizer/payout-requests`：申請提款
- `GET /admin/payout-requests`：Admin 列表
- `PATCH /admin/payout-requests/:id`：approve / reject

### 4.6 驗收

- [x] 可產生結算批次（POST /admin/settlements/generate）
- [x] 主辦方可申請提款（POST /organizer/payout-requests）
- [x] Admin 可審核（GET/PATCH /admin/payout-requests）

---

## 五、MVP-3.4 平台治理與 Audit

### 5.1 規格摘要

| 項目 | 說明 |
|------|------|
| audit_logs | 退款、補票、結算、提款、下架等關鍵操作 |
| 異常告警 Dashboard | 付款成功未出票、核銷失敗率異常 |
| 全站訂單總覽 | Admin 可查全站訂單、付款、退款、Webhook |
| 手動補票 (Comp) | 主辦方/Admin 手動發放公關票，寫入 Audit |
| Admin 治理 | 活動下架、主辦方封鎖 |
| 平台設定 | 退款規則、Email 模板（可選） |
| 進階報表 | 銷售概覽、時間序列、匯出（可選） |

### 5.2 audit_logs 表

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | uuid | PK |
| actor_type | text | admin / organizer / system |
| actor_id | uuid | user_id |
| action | text | refund / comp_ticket / unpublish / payout_approve / ... |
| resource_type | text | order / ticket / event / payout_request |
| resource_id | uuid | |
| details | jsonb | 額外脈絡 |
| created_at | timestamptz | |

### 5.3 需寫入 audit 的操作

- 退款（refund_service）
- 手動補票（Comp）
- 活動下架（admin patch status=disabled）
- 主辦方封鎖（新增）
- 結算/提款審核

### 5.4 Comp 票流程

1. 主辦方/Admin 選活動+票種，輸入 email 或 user_id
2. API `POST /organizer/events/:id/comp-ticket` 或 `POST /admin/events/:id/comp-ticket`
3. 建立 ticket（status=issued），不建立 order
4. 寫入 audit_logs
5. 寄出票券 email

### 5.5 全站訂單 API

- `GET /admin/orders`：q, status, from, to, org_id, event_id
- 回傳 orders + 關聯 payments、refunds
- 分頁

### 5.6 Migrations

- 0026_mvp3_audit_logs.sql
- 0027_mvp3_organizer_blocked.sql（若做主辦方封鎖）

### 5.7 驗收

- [x] 關鍵操作有 audit 紀錄（退款、結算產生、提款核准/退件、活動下架、comp 票）
- [x] Admin 可查全站訂單（GET /admin/orders：q, status, from, to, org_id, event_id, limit, offset）
- [x] Comp 按鈕可發放公關票、audit 有紀錄（POST /organizer/events/:id/comp-ticket）

---

## 六、MVP-3.5 使用者端擴充（可選）✅

| 項目 | 說明 | 實作 |
|------|------|------|
| 熱門活動 | 首頁「熱門」標籤或排序（規則：售票數、報名數） | GET /events?sort=hot；依 ticket_types.sold_count 總和排序；前端「熱門」tab、badge |
| 活動提醒 Email | 前一天/前一小時 job | POST /internal/jobs/event-reminders（X-Cron-Secret）；前一天 23–25h、前一小時 55–65min 窗口 |
| 活動異動/取消通知 | 時間變更或取消時 Email 參加者 | update_event、admin_update_event_status 鈎入 notify_event_cancelled / notify_event_time_changed |

### 6.1 驗收檢查表

- [x] GET /events?sort=hot 依售票數排序，回傳 total_sold_count
- [x] 首頁「依時間」/「熱門」切換正常
- [x] POST /internal/jobs/event-reminders 需 X-Cron-Secret，回傳 {1_day, 1_hour}
- [x] Admin 下架或主辦方改 status 為 cancelled/disabled 時寄取消信
- [x] 主辦方修改 start_at/end_at 時寄異動信

---

## 七、檔案變更清單（總覽）

| 區塊 | 檔案 |
|------|------|
| MVP-3.1 | events_service, ticket_types blueprints, 前端 router/views |
| MVP-3.2 | 0024 migration, events_service, admin blueprint |
| MVP-3.3 | 0025 migration, settlement_service, payout_service, blueprints |
| MVP-3.4 | 0026 migration, audit_service, comp API, admin orders API |
| MVP-3.5 | events_service (sort=hot、異動/取消鈎入), email_service (reminder/change/cancelled), event_notification_service, jobs blueprint, HomeView (熱門 tab) |

---

## 八、測試策略

- 每子階段：unit test 覆蓋新 service / 權限邏輯
- Integration：需 Supabase 的標 `@pytest.mark.integration`
- 驗收前：手動 smoke test（前端 + API）

---

## 九、Commit 策略

- 每完成一個子項（如 3.1 API 權限）即 commit
- message：`feat(mvp3-1): enforce staff cannot create events`
- 不 push，依用戶要求
