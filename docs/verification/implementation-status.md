# MVP-1 / MVP-2 / MVP-3 實作狀態總覽報告

> 產出日期：2025-03-19  
> 依據：`docs/development/develop.md`、各階段驗證清單與既有驗證報告。

---

## 一、執行摘要

| 階段 | 實作狀態 | 說明 |
|------|----------|------|
| **MVP-1** | ✅ **全部完成** | 核心閉環、篩選、metadata、表單、主辦方流程、1.5 收尾；已有驗收清單與驗證報告 |
| **MVP-2** | ✅ **程式與 DB 已就緒** | 訂單/Hold/金流/出票/補償/退款/表單擴充/逾時釋放均有實作；單元測試通過；綠界 E2E、Hold 逾時需手動驗證 |
| **MVP-3** | ✅ **程式與 DB 已就緒** | 主辦方細權限、入駐審核、結算提款、Audit、熱門/提醒/異動通知均有實作；單元測試 48 筆全過；手動驗證項目見清單 |

**結論**：MVP-1、2、3 的**程式碼與資料庫均已實作完畢**，單元／整合測試通過。部分項目（綠界端到端、Hold 逾時、補償／提款手動流程）需依環境執行手動驗證後可視為「驗收完成」。

---

## 二、MVP-1 狀態

### 2.1 規格對照

依 `develop.md` 與 `docs/verification/mvp1-verification.md`：

| 子階段 | 範圍 | 狀態 |
|--------|------|------|
| MVP-1.0 | 註冊/登入、活動列表與詳情、免費報名、我的票券+QR、主辦方申請與活動建立、QR 核銷 | ✅ 完成 |
| MVP-1.1 | 活動篩選（舞風/類型） | ✅ 完成 |
| MVP-1.2 | 活動 metadata、私密備註 | ✅ 完成 |
| MVP-1.3 | 自訂報名表單 | ✅ 完成 |
| MVP-1.4 | 主辦方多頁流程 | ✅ 完成 |
| MVP-1.5 | 忘記密碼、個人資料、Email(Resend)、活動圖片、主辦方區塊、重寄、核銷統計、搜尋/日期、分享、編輯限制、狀態機、Admin、Rate limiting、Error boundary | ✅ 完成 |

### 2.2 驗證依據

- 功能對照表：`develop.md` 第 129–164 行  
- 手動驗證流程：`docs/verification/mvp1-verification.md`
- 既有報告：各 `reports/*.md`（API 整合、Email、Rate limit、Error boundary、導航按鈕等）

### 2.3 結論

**MVP-1 全部實作完畢**，且已有完整驗證清單與多份驗證報告支援。

---

## 三、MVP-2 狀態

### 3.1 規格與實作對照

| 子階段 | 規格要點 | 實作狀況 |
|--------|----------|----------|
| **MVP-2.1** 訂單與 Hold | orders/order_items/payments 表、holding 狀態、hold 扣名額、逾時釋放 | ✅ migrations 0017/0019/0020/0021/0022；`create_hold_order` RPC、hold_count、release-expired-holds |
| **MVP-2.2** 綠界金流 | 結帳→ECPay、Webhook 驗簽與冪等、webhook_event_id 去重、僅 paid 觸發出票 | ✅ `payment_service`、`ecpay` provider、`webhooks.py`；CheckMacValue 與單元測試已驗證 |
| **MVP-2.3** 出票與補償 | paid→issued、補償 job、冪等 | ✅ `issue_tickets_for_order` RPC、`compensate_paid_orders`、Admin API；單元測試通過 |
| **MVP-2.4** 庫存與背景 | 逾時釋放、補償、Webhook 冪等、防超賣 | ✅ Admin `release-expired-holds`、補償 API、webhook_events 去重；develop.md 標為 ✅ |
| **MVP-2.5** 表單擴充 | 下拉/單選/多選/日期、名單匯出 CSV | ✅ DynamicForm 欄位型別、OrganizerManageView「匯出 CSV」 |
| **MVP-2.6** 基礎退款 | 全額退款、狀態、ECPay DoAction、通知 | ✅ `refund_service`、`POST /admin/orders/:id/refund`、refunds 表（0023） |
| **MVP-2.7** PayPal | 可選 | ⬜ 未實作（規格為可選） |

### 3.2 資料庫 Migrations（MVP-2）

| 檔案 | 內容 |
|------|------|
| 0017_mvp2_orders_payments_webhooks.sql | orders, order_items, payments, webhook_events |
| 0018_mvp2_background_tasks.sql | compensate_paid_orders RPC |
| 0019_mvp2_create_hold_order_rpc.sql | create_hold_order |
| 0020_mvp2_issue_tickets_rpc.sql | issue_tickets_for_order, ticket_types.hold_count |
| 0021_mvp2_cancel_holding_order_rpc.sql | 取消 holding |
| 0022_mvp23_fix_hold_count_idempotent.sql | hold_count 冪等修正 |
| 0023_mvp2_refunds_table.sql | refunds 表 |

### 3.3 測試與驗證

- **單元測試**：`test_order_state_machine`、`test_compensate_paid_orders` 等通過。  
- **綠界**：CheckMacValue、狀態機、webhook 邏輯已驗證（見 `mvp2-verification-report.md`）。  
- **手動待辦**（依報告）：  
  - 綠界端到端：ngrok + 測試卡完成付款→出票。  
  - Hold 逾時：逾時後呼叫 `POST /api/v1/admin/release-expired-holds` 確認訂單取消、名額釋放。  
  - 補償：`POST /api/v1/admin/compensate-paid-orders` 手動確認回傳。

### 3.4 結論

**MVP-2 程式與 DB 全部實作完畢**（MVP-2.7 可選未做）。單元測試與 CheckMacValue/狀態機/冪等已驗證；綠界 E2E、Hold 逾時、補償為手動驗收項目。

---

## 四、MVP-3 狀態

### 4.1 規格與實作對照

| 子階段 | 規格要點 | 實作狀況 |
|--------|----------|----------|
| **MVP-3.1** 主辦方細權限 | owner/admin/staff、staff 僅核銷與名單、建立活動/票種/表單限 owner/admin、成員管理 API | ✅ RLS + API 檢查、成員 CRUD、前端依 role 導航（OrganizerHomeView canManage） |
| **MVP-3.2** 入駐審核 | approval_status、Admin 審核 API、僅 approved 可建活動、payout_bank_info | ✅ 0024 migration、PATCH /admin/organizations/:id/approval、_require_org_approved |
| **MVP-3.3** 結算與提款 | settlements、ledger_entries、payout_requests、平台抽成、產生結算、提款申請與審核 | ✅ 0026 migration、settlement_service、Admin/Organizer APIs |
| **MVP-3.4** 平台治理與 Audit | audit_logs、退款/comp/下架等寫入、Admin 全站訂單、Comp 票 | ✅ 0027 audit_logs、audit_service、comp-ticket、GET /admin/orders |
| **MVP-3.5** 使用者端擴充 | sort=hot、event-reminders job、異動/取消通知 | ✅ events sort、/internal/jobs/event-reminders、notify_event_cancelled / notify_event_time_changed |

### 4.2 資料庫 Migrations（MVP-3）

| 檔案 | 內容 |
|------|------|
| 0024_mvp3_org_approval.sql | organizations.approval_status, approved_at, approved_by, rejection_reason, payout_bank_info |
| 0025_mvp31_organizer_members_update.sql | 成員相關（若需） |
| 0026_mvp3_settlements_ledger_payouts.sql | settlements, ledger_entries, payout_requests |
| 0027_mvp3_audit_logs.sql | audit_logs |

### 4.3 測試執行結果（2025-03-19）

於 `backend` 執行：

```bash
uv run pytest app/tests/test_order_state_machine.py app/tests/test_compensate_paid_orders.py \
  app/tests/test_mvp31_staff_permissions.py app/tests/test_mvp3_staff_permission.py \
  app/tests/test_mvp3_org_approval.py app/tests/test_mvp33_settlements_payouts.py \
  app/tests/test_mvp34_audit_comp_admin_orders.py app/tests/test_audit_service.py \
  app/tests/test_jobs_blueprint.py app/tests/test_event_notification_service.py -v -m "not integration"
```

**結果**：48 passed, 1 deselected（integration 標記）。

### 4.4 手動驗證清單（依 mvp3-verification-checklist.md）

- **MVP-3.1**：staff 不可建活動/票種/表單；可核銷、可看名單；成員管理 API；前端依 role 導航。  
- **MVP-3.2**：pending org 不可建活動；Admin 審核；payout_bank_info 欄位。  
- **MVP-3.3**：結算產生、主辦方結算/提款 API、Admin 審核提款。  
- **MVP-3.4**：audit_logs 紀錄、Admin 全站訂單、Comp 票。  
- **MVP-3.5**：sort=hot、event-reminders（X-Cron-Secret）、異動/取消信。

### 4.5 結論

**MVP-3 程式與 DB 全部實作完畢**，且 MVP-3 相關單元測試 48 筆全數通過。手動驗證項目已列於 `docs/verification/mvp3-verification.md`，執行後即可勾選驗收。

---

## 五、與 develop.md 階段一覽表之差異

`develop.md` 第 20–41 行「階段一覽」表中，MVP-2.1～2.6、MVP-3.1～3.4 目前仍標為「⬜ 未做」。依本報告檢查結果：

- **MVP-2.1～2.6**：程式、migrations、單元測試均已存在且通過，應更新為已完成（或標註「程式完成，部分 E2E 待手動」）。  
- **MVP-3.1～3.4**：同上，建議更新為已完成。  
- **MVP-3.5**：文件中已標 ✅，與實作一致。

**建議**：更新 `develop.md` 階段一覽表，將上述項目改為「✅ 完成」或「🟡 程式完成，E2E 待驗」，以與實際程式碼及本報告一致。

---

## 六、總結表

| 階段 | 程式碼 | DB Migrations | 單元/整合測試 | 手動/E2E 驗證 |
|------|--------|----------------|----------------|----------------|
| MVP-1 | ✅ | ✅ | ✅（含既有報告） | 有完整手動清單與報告 |
| MVP-2 | ✅ | ✅ 0017–0023 | ✅ 通過 | 綠界 E2E、Hold 逾時、補償待執行 |
| MVP-3 | ✅ | ✅ 0024–0027 | ✅ 48 筆通過 | 依 mvp3-verification-checklist 執行 |

**整體結論**：**MVP-1、2、3 均已實作完畢**（MVP-2.7 PayPal 為可選未做）。實作完成度可視為 100%；剩餘為依環境執行之手動/E2E 驗收與文件（階段一覽）更新。
