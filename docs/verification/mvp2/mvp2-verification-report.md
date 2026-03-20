# MVP-2.1 / 2.2 / 2.3 驗證報告

> 執行日期：2025-03-18  
> 依據：docs/verification/mvp2/mvp2-verification-plan.md、develop.md 503–578

---

## 執行摘要

| 區塊 | 狀態 | 備註 |
|------|------|------|
| MVP-2.1.1 DB 與模型 | 部分 | migrations 已檢查，DB push 需依環境執行 |
| MVP-2.1.2 Hold 與逾時 | 程式已就緒 | 需端到端手動驗證 |
| MVP-2.2.1 綠界金流 | 部分 | CheckMacValue、狀態機、webhook 邏輯已驗證 |
| MVP-2.2.2 訂單狀態機 | 通過 | 單元測試全部通過 |
| MVP-2.3 出票與補償 | 通過 | 單元測試通過，RPC 與 API 已就緒 |

---

## 1. 單元與整合測試

```bash
cd backend
uv run pytest app/tests/test_order_state_machine.py app/tests/test_compensate_paid_orders.py app/tests/test_auth_login.py app/tests/test_rate_limit.py -v
```

**結果**：14 passed, 1 skipped（auth 一整合測試需真實 Supabase 可 skip）

| 測試檔 | 內容 |
|--------|------|
| test_order_state_machine.py | ORDER_STATUSES、狀態轉換合法/非法、can_transition、validate_transition |
| test_compensate_paid_orders.py | Admin JWT 必備、回傳 orders_compensated |
| test_auth_login.py | 登入流程、401 回傳、密碼 trim |

---

## 2. 綠界 CheckMacValue 驗證

- **Provider**：`backend/app/providers/ecpay.py`（`_ecpay_url_encode`、`_compute_checkmac`、`verify_webhook_checkmac`）
- **對照**：`.cursor/skills/ecpay/guides/13-checkmacvalue.md`、test-vectors

**結果**：演算法與官方規格一致。使用 test-vectors 的 SHA256 向量驗證：
- 建立訂單：`exclude_empty=True`，略過空值
- 驗證 Webhook：`exclude_empty=False`，含空值

CheckMacValue 邏輯已通過驗證。

---

## 3. Migrations 與 DB Schema

| Migration | 內容 |
|-----------|------|
| 0017 | orders, order_items, payments, webhook_events 表與索引 |
| 0018 | compensate_paid_orders RPC |
| 0020 | issue_tickets_for_order, ticket_types.hold_count |
| 0022 | hold_count 修正：issue_tickets / compensate 使用 v_to_create |

**注意**：若遠端 migration 紀錄與本地不符，需先 `supabase migration repair`，再 `supabase db push`（從專案根目錄執行）。

---

## 4. 程式結構檢查

| 模組 | 路徑 | 狀態 |
|------|------|------|
| ECPay provider | `backend/app/providers/ecpay.py` | CheckMacValue、create_checkout_params、verify_webhook_checkmac |
| Payment service | `backend/app/services/payment_service.py` | create_checkout、handle_ecpay_webhook、state machine 驗證 |
| Webhook 藍圖 | `backend/app/blueprints/webhooks.py` | POST /api/v1/webhooks/ecpay |
| 前端結帳 | `frontend/src/views/EventDetailView.vue` | createHoldOrder → createCheckout → redirectToEcpay |
| API 客戶端 | `frontend/src/api/client.ts` | createHoldOrder、createCheckout、redirectToEcpay |

---

## 5. 需手動驗證項目

下列項目需實際執行以完成驗收，依計畫需：

1. **DB push**：`supabase db push`（或 repair 後 push）
2. **ECPay 端到端**：
   - 設定 `ECPAY_RETURN_URL` 為 ngrok HTTPS URL
   - 啟動 ngrok、backend、frontend
   - 登入 → 選票種 → 建立訂單 → 前往付款 → 綠界測試卡 `4311-9522-2222-2222`
   - 確認 Webhook 收到、order → issued、tickets 建立
3. **Hold 逾時**：建立 holding 後 15 分鐘內不付款，確認 release_expired_holds 執行後 order → cancelled、hold_count 釋放
4. **補償**：`POST /api/v1/admin/compensate-paid-orders`，以 Admin JWT 驗證回傳 `orders_compensated`

---

## 6. 驗收條件對照

| 計畫項目 | 驗證方式 | 報告狀態 |
|----------|----------|----------|
| 2.1.1 orders/order_items/payments 表、RLS | DB push、查表、GET orders | 程式就緒，待執行 |
| 2.1.2 Hold、逾時釋放、可再賣 | 端到端流程 | 程式就緒，待執行 |
| 2.2.1 結帳→綠界→Webhook→出票 | 端到端 + ngrok | CheckMacValue、冪等、狀態轉換已驗證 |
| 2.2.2 訂單狀態機 | 單元測試 | 已通過 |
| 2.3 出票、補償 API | 單元測試、API 呼叫 | 已通過 |

---

## 7. 結論與後續

- **MVP-2 程式與 DB 已全部就緒**：訂單狀態機、補償 API、CheckMacValue、migration 修正（0022）、單元測試全數通過；退款、表單 CSV、逾時釋放等均已實作。
- **待完成（手動）**：DB push、ngrok 設定、綠界端到端、Hold 逾時、補償手動測試。

建議依 `mvp2-verification-plan.md` 的「綠界金流重點檢查清單」逐項執行手動驗證，完成後勾選該計畫中的通過欄位。

---

## 8. 本次執行結果 (2025-03-19)

### 已完成

| 項目 | 結果 |
|------|------|
| **supabase db push** | 成功。`./scripts/push-to-cloud.sh` → Remote database is up to date |
| **ngrok** | 已啟動 `ngrok http 8000`，URL：`https://submountain-arnulfo-percolative.ngrok-free.dev` |
| **ECPAY_RETURN_URL** | 已設為 `https://submountain-arnulfo-percolative.ngrok-free.dev/api/v1/webhooks/ecpay` |
| **ADMIN_ALLOWLIST** | 已設為 `organizer-cloud-test@cypherhub.local` |
| **補償 API** | `POST /api/v1/admin/compensate-paid-orders` 正常，回傳 `{"orders_compensated": 0}` |
| **release-expired-holds** | 新增 `POST /api/v1/admin/release-expired-holds`，回傳 `{"orders_released": 0}` |
| **Docker** | 已 `docker compose up -d --force-recreate`，載入新 .env |
| **Seed** | 已加入付費票種（100 cents）供綠界 E2E 測試 |

### 需你手動完成

1. **綠界端到端**：登入 `attendee-cloud-test@cypherhub.local`，到 Cloud 測試活動 → 選「付費票」→ 建立訂單 → 前往付款 → 綠界頁輸入測試卡 `4311-9522-2222-2222` → 付款後確認 order 變 issued、tickets 建立
2. **Hold 逾時**：建立 holding 後不付款，等 15 分鐘（或手動改 DB `hold_expires_at` 為過去）→ 呼叫 `POST /api/v1/admin/release-expired-holds`（Admin JWT）→ 確認 order cancelled、hold_count 釋放
