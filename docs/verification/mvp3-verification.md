# MVP-3 驗證文件（測試清單 + MVP-3.5 報告）

> 合併自：mvp3-verification-checklist.md + mvp3.5-verification-report.md。
> 對應 mvp3-master-plan.md。主辦方細權限、入駐審核、結算提款、Audit 治理、使用者端擴充。
> **狀態（2025-03）**：程式與 DB 已實作完成，單元測試 48 筆全過。手動驗證待執行。

---

## 前置：環境準備

```bash
# 1. Migrations 已套用（含 MVP-3: 0024~0027）
supabase db reset  # 或 supabase db push

# 2. 後端 .env 必填
SUPABASE_URL=<local_or_cloud>
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
ADMIN_ALLOWLIST=<admin_user_id_or_email>
ORG_APPROVAL_REQUIRED=True       # 入駐審核
PLATFORM_FEE_RATE=0.05           # 平台抽成 5%
CRON_SECRET=<secret>             # event-reminders job

# 3. 安裝依賴 & 啟動
cd backend && uv sync
cd frontend && npm install
```

---

## 一、自動化測試

```bash
cd backend

# 一次跑完所有 MVP-3 相關測試
uv run pytest \
  app/tests/test_mvp31_staff_permissions.py \
  app/tests/test_mvp3_staff_permission.py \
  app/tests/test_mvp3_org_approval.py \
  app/tests/test_mvp33_settlements_payouts.py \
  app/tests/test_mvp34_audit_comp_admin_orders.py \
  app/tests/test_audit_service.py \
  app/tests/test_jobs_blueprint.py \
  app/tests/test_event_notification_service.py \
  -v -m "not integration"
```

**結果**：48 passed, 1 deselected

| 子階段 | 測試檔 | 涵蓋 |
|--------|--------|------|
| 3.1 權限 | test_mvp31_staff_permissions.py, test_mvp3_staff_permission.py | staff 不可建活動/票種 |
| 3.2 審核 | test_mvp3_org_approval.py | pending org 不可建活動、Admin 審核 |
| 3.3 結算 | test_mvp33_settlements_payouts.py | settlements/payouts API |
| 3.4 Audit | test_audit_service.py, test_mvp34_audit_comp_admin_orders.py | audit log、comp-ticket、Admin orders |
| 3.5 擴充 | test_jobs_blueprint.py, test_event_notification_service.py | reminders、異動通知 |

---

## 二、手動驗證清單

### 2.1 MVP-3.1 主辦方成員細權限

| 步驟 | 操作 | 預期 | 通過 |
|------|------|------|------|
| 1 | staff 登入主辦方後台 | 僅見核銷/名單，無建立活動入口 | [ ] |
| 2 | staff `POST /organizer/events` | 403 STAFF_CANNOT_MANAGE | [ ] |
| 3 | staff `GET .../attendees` | 200 | [ ] |
| 4 | staff verify + commit | 200，核銷成功 | [ ] |
| 5 | owner/admin `GET .../members` | 200 | [ ] |
| 6 | owner/admin `POST .../members` 新增 | 201 | [ ] |
| 7 | owner `PATCH .../members/:userId` 改 role | 200 | [ ] |
| 8 | admin 嘗試改 owner role | 403 | [ ] |

### 2.2 MVP-3.2 入駐審核

| 步驟 | 操作 | 預期 | 通過 |
|------|------|------|------|
| 1 | apply_organizer（ORG_APPROVAL_REQUIRED=True） | pending | [ ] |
| 2 | pending org 建活動 | 403 ORG_NOT_APPROVED | [ ] |
| 3 | Admin `GET /admin/organizations` | 含 pending org | [ ] |
| 4 | Admin PATCH approval → approved | 200 | [ ] |
| 5 | 通過後建活動 | 201 | [ ] |
| 6 | Admin PATCH → rejected | 200 | [ ] |

### 2.3 MVP-3.3 結算與提款

| 步驟 | 操作 | 預期 | 通過 |
|------|------|------|------|
| 1 | settlements/ledger/payouts 表存在 | SQL 確認 | [ ] |
| 2 | Admin `POST /admin/settlements/generate` | 201 | [ ] |
| 3 | 主辦方 `GET /organizer/settlements` | 自己的結算 | [ ] |
| 4 | 主辦方 `POST /organizer/payout-requests` | 201 | [ ] |
| 5 | Admin `PATCH /admin/payout-requests/:id` → approved | 200 | [ ] |

### 2.4 MVP-3.4 平台治理與 Audit

| 步驟 | 操作 | 預期 | 通過 |
|------|------|------|------|
| 1 | 退款後 audit_logs 有紀錄 | action=refund | [ ] |
| 2 | `POST /organizer/events/:id/comp-ticket` | 201，ticket 建立 | [ ] |
| 3 | comp 後 audit_logs 有紀錄 | action=comp_ticket | [ ] |
| 4 | Admin 下架活動 | audit 有 unpublish | [ ] |
| 5 | `GET /admin/orders` 分頁 | 正確回傳 | [ ] |

### 2.5 MVP-3.5 使用者端擴充

| 步驟 | 操作 | 預期 | 通過 |
|------|------|------|------|
| 1 | `GET /events?sort=hot` | 依售票數排序 | [ ] |
| 2 | 前端「熱門」tab | 排序變化、badge 顯示 | [ ] |
| 3 | event-reminders 無 secret | 401 | [ ] |
| 4 | event-reminders 有 secret | 200，{1_day, 1_hour} | [ ] |
| 5 | 下架/取消活動 | 參加者收取消信 | [ ] |
| 6 | 修改 start_at/end_at | 參加者收異動信 | [ ] |

---

## 三、MVP-3.5 驗證報告（已通過）

### 熱門活動 ✅

| 項目 | 備註 |
|------|------|
| GET /events?sort=hot | 依 sold_count 總和排序 |
| total_sold_count 回傳 | sort=hot 時每筆 event 含此欄位 |
| 前端 tab 切換 | HomeView sortMode |
| 熱門 badge | total_sold_count > 0 時顯示 |

### 活動提醒 Email ✅

| 項目 | 備註 |
|------|------|
| POST /internal/jobs/event-reminders | 需 X-Cron-Secret |
| 前一天窗口 23–25h | process_events |
| 前一小時窗口 55–65min | process_events |
| 回傳 {1_day, 1_hour} | 各窗口寄送數量 |

### 異動/取消通知 ✅

| 項目 | 備註 |
|------|------|
| Admin 下架 / 主辦方取消 | notify_event_cancelled |
| 修改 start_at/end_at | notify_event_time_changed |
| Email 來源 | auth.users 優先，fallback form_responses |

---

## 四、驗收完成條件

- [ ] **3.1**：staff 權限限制正確；成員管理 API 正常
- [ ] **3.2**：入駐審核流程完整
- [ ] **3.3**：結算/提款/平台費正確
- [ ] **3.4**：audit、comp、Admin 訂單正常
- [ ] **3.5**：熱門、提醒、異動通知正常
