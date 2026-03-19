# MVP-3 完整測試與驗證清單

> 對應 mvp3-master-plan.md。涵蓋主辦方細權限、入駐審核、結算提款、Audit 治理、使用者端擴充。
> **用途**：確保 MVP-3 無誤且可正常執行。含 Cursor 可執行之自動化測試與手動驗證步驟。

---

## 一、前置：環境準備

```bash
# 1. Migrations 已套用（含 MVP-3: 0024~0027）
cd backend
supabase db reset
# 或 supabase db push（若已有資料需保留）

# 2. 後端 .env 必填
SUPABASE_URL=<local_or_cloud>
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
ADMIN_ALLOWLIST=<admin_user_id_or_email>   # Admin 審核、全站訂單、提款審核
ORG_APPROVAL_REQUIRED=True                 # 入駐審核（可選，預設則免審）
PLATFORM_FEE_RATE=0.05                     # 平台抽成 5%（結算用）
CRON_SECRET=<secret>                       # event-reminders job 用

# 3. 安裝依賴
cd backend && uv sync
cd frontend && npm install

# 4. 啟動服務
# 終端 1: cd backend && flask run
# 終端 2: cd frontend && npm run dev
```

---

## 二、Cursor 可執行：自動化測試

### 2.1 執行指令（建議順序）

```bash
cd backend

# MVP-3.1 主辦方成員細權限
uv run pytest app/tests/test_mvp31_staff_permissions.py -v
uv run pytest app/tests/test_mvp3_staff_permission.py -v

# MVP-3.2 入駐審核
uv run pytest app/tests/test_mvp3_org_approval.py -v

# MVP-3.4 平台治理與 Audit
uv run pytest app/tests/test_mvp34_audit_comp_admin_orders.py -v

# MVP-3.5 使用者端擴充
uv run pytest app/tests/test_jobs_blueprint.py -v
uv run pytest app/tests/test_event_notification_service.py -v
uv run pytest app/tests/test_events_filters.py -v -k "hot"

# MVP-3.3 結算/提款、Audit
uv run pytest app/tests/test_mvp33_settlements_payouts.py app/tests/test_audit_service.py -v

# 一次跑完所有 MVP-3 相關測試（不含 integration，需網路）
uv run pytest app/tests/test_mvp3*.py app/tests/test_mvp31*.py app/tests/test_mvp33*.py app/tests/test_mvp34*.py app/tests/test_audit_service.py app/tests/test_jobs_blueprint.py app/tests/test_event_notification_service.py app/tests/test_events_filters.py -v -m "not integration"
```

### 2.2 測試覆蓋對照表

| 子階段 | 測試檔 | 涵蓋範圍 |
|--------|--------|----------|
| MVP-3.1 | test_mvp31_staff_permissions.py | staff 不能建活動、票種；非 admin 不可看成員 |
| MVP-3.1 | test_mvp3_staff_permission.py | staff 權限相關 |
| MVP-3.2 | test_mvp3_org_approval.py | org 未審核不可建活動；Admin 審核 API |
| MVP-3.3 | test_mvp33_settlements_payouts.py | settlements/payouts API、generate_settlements integration |
| MVP-3.4 | test_audit_service.py | audit log 寫入（log_refund, log_comp_ticket 等） |
| MVP-3.4 | test_mvp34_audit_comp_admin_orders.py | comp-ticket 權限、Admin orders |
| MVP-3.5 | test_jobs_blueprint.py | event-reminders X-Cron-Secret |
| MVP-3.5 | test_event_notification_service.py | run_event_reminders、notify_event_cancelled |
| MVP-3.5 | test_events_filters.py | sort=hot 傳遞 |

### 2.3 Integration 測試（需 Supabase）

```bash
cd backend
# 需設定 SUPABASE_* 環境變數
uv run pytest -m integration -v
```

---

## 三、手動驗證清單

### 3.1 MVP-3.1 主辦方成員細權限

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 以 staff 登入主辦方後台 | 僅見「核銷」「名單」，無「建立活動」「成員管理」入口 |
| 2 | staff 呼叫 `POST /api/v1/organizer/events` | 403，error.code=STAFF_CANNOT_MANAGE |
| 3 | staff 呼叫 `POST .../ticket-types` | 403 STAFF_CANNOT_MANAGE |
| 4 | staff 呼叫 `GET .../attendees` | 200 |
| 5 | staff 進行核銷（verify + commit） | 200，可成功核銷 |
| 6 | owner/admin 呼叫 `GET /organizer/organizations/:orgId/members` | 200，可看成員 |
| 7 | owner/admin 呼叫 `POST .../members` 新增 admin/staff | 201 |
| 8 | owner 呼叫 `PATCH .../members/:userId` 改 role | 200 |
| 9 | admin 嘗試改 owner 的 role | 403 |
| 10 | owner/admin 呼叫 `DELETE .../members/:userId` | 200（不可刪自己為唯一 owner） |

** curl 範例**：
```bash
# staff 建活動 → 應 403
curl -X POST http://localhost:8000/api/v1/organizer/events \
  -H "Authorization: Bearer $STAFF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"<org_id>","title":"Test","start_at":"2025-06-01T10:00:00Z","end_at":"2025-06-01T12:00:00Z"}'
# 預期：{"error":{"code":"STAFF_CANNOT_MANAGE"}}
```

---

### 3.2 MVP-3.2 主辦方入駐審核

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 新帳號 apply_organizer（ORG_APPROVAL_REQUIRED=True） | org approval_status=pending |
| 2 | pending org 主辦方呼叫 `POST /organizer/events` | 403 ORG_NOT_APPROVED |
| 3 | Admin 呼叫 `GET /admin/organizations` | 200，含 pending org |
| 4 | Admin 呼叫 `PATCH /admin/organizations/:id/approval` body: `{status:"approved"}` | 200 |
| 5 | 審核通過後主辦方建活動 | 201 |
| 6 | Admin `PATCH .../approval` body: `{status:"rejected", rejection_reason:"..."}` | 200 |
| 7 | rejected org 建活動 | 403 |

** curl 範例**：
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<admin_email>","password":"<pass>"}' | jq -r '.access_token')

curl -X PATCH "http://localhost:8000/api/v1/admin/organizations/<org_id>/approval" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"approved"}'
```

---

### 3.3 MVP-3.3 結算與提款

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | DB：確認 settlements、ledger_entries、payout_requests 表存在 | `\d settlements` 等 |
| 2 | Admin 呼叫 `POST /admin/settlements/generate` body: `{period_start, period_end}` | 201 或 200 |
| 3 | 檢查 settlements 表 | 有對應紀錄，gross_cents/platform_fee_cents/net_cents 正確 |
| 4 | 主辦方呼叫 `GET /organizer/settlements` | 200，含自己的結算 |
| 5 | 主辦方呼叫 `GET /organizer/settlements/:id` | 200，含明細 |
| 6 | 主辦方呼叫 `POST /organizer/payout-requests` body: `{amount_cents}` | 201 |
| 7 | Admin 呼叫 `GET /admin/payout-requests` | 200 |
| 8 | Admin 呼叫 `PATCH /admin/payout-requests/:id` body: `{status:"approved"}` | 200 |
| 9 | 再次核准已 approved 的 request | 應回錯或冪等 |

** curl 範例**：
```bash
# 主辦方申請提款
curl -X POST http://localhost:8000/api/v1/organizer/payout-requests \
  -H "Authorization: Bearer $ORGANIZER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount_cents":10000}'

# Admin 審核
curl -X PATCH "http://localhost:8000/api/v1/admin/payout-requests/<id>" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"approved"}'
```

---

### 3.4 MVP-3.4 平台治理與 Audit

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | DB：確認 audit_logs 表存在 | `\d audit_logs` |
| 2 | 執行退款 | refund_service 完成後，audit_logs 有 refund 紀錄 |
| 3 | 主辦方/Admin 呼叫 `POST /organizer/events/:id/comp-ticket` body: `{ticket_type_id, email}` | 201，ticket 建立 |
| 4 | 檢查 audit_logs | action=comp_ticket，resource_type=ticket |
| 5 | Admin 下架活動 `PATCH /admin/events/:id` status=disabled | 200，audit 有 unpublish |
| 6 | Admin 呼叫 `GET /admin/orders?q=&status=&from=&to=&org_id=&event_id=&limit=20&offset=0` | 200，回傳 orders + payments + refunds |
| 7 | GET /admin/orders 分頁 | offset 變化時結果正確 |

** curl 範例**：
```bash
# Comp 票
curl -X POST "http://localhost:8000/api/v1/organizer/events/<ev_id>/comp-ticket" \
  -H "Authorization: Bearer $ORGANIZER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ticket_type_id":"<tt_id>","email":"guest@example.com"}'

# 全站訂單
curl -s "http://localhost:8000/api/v1/admin/orders?limit=5&offset=0" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.items | length'
```

---

### 3.5 MVP-3.5 使用者端擴充

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 首頁「依時間」「熱門」切換 | 列表排序變化 |
| 2 | `curl "http://localhost:8000/api/v1/events?sort=hot"` | 依售票數排序，有 total_sold_count |
| 3 | `POST /internal/jobs/event-reminders` 無 header | 401 |
| 4 | `POST /internal/jobs/event-reminders` -H "X-Cron-Secret: wrong" | 401 |
| 5 | `POST /internal/jobs/event-reminders` -H "X-Cron-Secret: $CRON_SECRET" | 200，`{1_day, 1_hour}` |
| 6 | Admin 下架活動或主辦方改 status=cancelled | 參加者收到取消信 |
| 7 | 主辦方修改活動 start_at/end_at | 參加者收到異動信 |

** curl 範例**：
```bash
# 熱門排序
curl -s "http://localhost:8000/api/v1/events?sort=hot" | jq '.items[0] | keys'

# event-reminders（路徑為 /internal/jobs/event-reminders，無 api/v1 前綴）
curl -X POST http://localhost:8000/internal/jobs/event-reminders \
  -H "X-Cron-Secret: $CRON_SECRET"
```

---

## 四、DB 結構快速驗證

```sql
-- MVP-3 相關表與欄位
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'organizations' AND column_name IN ('approval_status','approved_at','approved_by','rejection_reason','payout_bank_info');
SELECT column_name FROM information_schema.columns WHERE table_name = 'settlements';
SELECT column_name FROM information_schema.columns WHERE table_name = 'ledger_entries';
SELECT column_name FROM information_schema.columns WHERE table_name = 'payout_requests';
SELECT column_name FROM information_schema.columns WHERE table_name = 'audit_logs';
```

---

## 五、Smoke Test 一鍵腳本（可選）

以下指令可複製貼上，假設已設定 `ADMIN_TOKEN`、`ORGANIZER_TOKEN`：

```bash
# 健康檢查
curl -s http://localhost:8000/api/v1/health | jq .

# 公開活動（含熱門）
curl -s "http://localhost:8000/api/v1/events?sort=hot&limit=2" | jq '.items | length'

# Admin 訂單（需 ADMIN_TOKEN）
curl -s "http://localhost:8000/api/v1/admin/orders?limit=1" -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.items | length'

# 主辦方結算（需 ORGANIZER_TOKEN）
curl -s "http://localhost:8000/api/v1/organizer/settlements" -H "Authorization: Bearer $ORGANIZER_TOKEN" | jq '.items // .settlements // .'
```

---

## 六、驗收完成條件總表

- [ ] **MVP-3.1**：staff 不可建活動/票種/表單；可核銷、可看名單；owner/admin 成員管理正常；前端依 role 導航
- [ ] **MVP-3.2**：pending org 不可建活動；Admin 可審核；payout_bank_info 欄位存在
- [ ] **MVP-3.3**：settlements/ledger/payouts 表存在；可產生結算；主辦方可申請提款；Admin 可審核
- [ ] **MVP-3.4**：audit_logs 有退款/comp/unpublish 等紀錄；Admin 全站訂單 API；Comp 票可發放
- [ ] **MVP-3.5**：sort=hot、event-reminders job、異動/取消信正常

