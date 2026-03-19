# MVP-3.2 主辦方入駐審核 — 詳細規劃

> 對應 develop.md 647-656、mvp3-master-plan.md §三。

---

## 一、規格摘要

| 項目 | 說明 |
|------|------|
| 申請狀態 | pending / approved / rejected |
| Admin 審核 | 通過/退件 API |
| 通過後 | 才可建立活動 |
| 收款資訊 | payout_bank_info jsonb（審核時或通過後填寫，可選） |
| 免審核模式 | 環境變數 `ORG_APPROVAL_REQUIRED=false` 時，新申請直接 approved（向後相容） |

---

## 二、DB 變更

### 2.1 organizations 新增欄位

| 欄位 | 型別 | 預設 | 說明 |
|------|------|------|------|
| approval_status | text | 'approved' | pending / approved / rejected |
| approved_at | timestamptz | NULL | 審核通過時間 |
| approved_by | uuid | NULL | Admin user_id |
| rejection_reason | text | NULL | 退件原因 |
| payout_bank_info | jsonb | NULL | 收款資訊（銀行代碼、帳號等） |

### 2.2 Migration 0024

- 既有 org 設為 `approved`
- 新欄位加 `IF NOT EXISTS` 避免重複

---

## 三、後端流程

### 3.1 apply_organizer

- 若 `ORG_APPROVAL_REQUIRED=true` → `approval_status='pending'`
- 否則 → `approval_status='approved'`（維持現狀）

### 3.2 create_event

- 取得 org 的 `approval_status`
- 若非 `approved` → 回傳 `ORG_NOT_APPROVED` 409

### 3.3 Admin API

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /admin/organizations | 列表，query: status=pending\|approved\|rejected |
| PATCH | /admin/organizations/:id/approval | body: { status, rejection_reason? } |

---

## 四、檔案變更

| 檔案 | 變更 |
|------|------|
| supabase/migrations/0024_mvp3_org_approval.sql | 新增欄位 |
| backend/config.py | ORG_APPROVAL_REQUIRED |
| backend/app/services/events_service.py | apply 寫入 status、create_event 檢查 |
| backend/app/domain/schemas.py | AdminOrgApprovalRequest |
| backend/app/blueprints/admin.py | GET organizations、PATCH approval |
| backend/app/services/organizations_service.py | 新建：list_admin_orgs、approve_org |
| docs/development/develop.md | MVP-3.2 Done |

---

## 五、驗收

- [x] 新申請 org，ORG_APPROVAL_REQUIRED=true 時為 pending
- [x] Admin 可 GET /admin/organizations?status=pending
- [x] Admin 可 PATCH 通過/退件
- [x] 僅 approved 的 org 可建立活動（create_event 檢查）
- [x] get_my_organizer_summary 含 approval_status，前端可顯示審核中
