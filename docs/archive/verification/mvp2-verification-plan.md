# MVP-2.1 / 2.2 / 2.3 驗證計畫

> 對應 develop.md 503–578 行。依序執行可驗收訂單、綠界金流、出票補償。
> **特別著重綠界金流 ECPay 端到端流程。**
> **狀態（2025-03）**：程式與 DB 已就緒，單元測試通過；下列手動/E2E 項（DB push、ngrok、綠界端到端、Hold 逾時、補償）待執行即完成驗收。

---

## 前置：環境準備

```bash
# 1. Migrations 已套用（含 0022）
supabase db push   # 或 repair 後 push

# 2. 後端 .env 必填（綠界測試）
ECPAY_MERCHANT_ID=3002607
ECPAY_HASH_KEY=pwFHCqoQZGmho4w6
ECPAY_HASH_IV=EkRm7iFT261dpevs
ECPAY_RETURN_URL=https://<ngrok-url>/api/v1/webhooks/ecpay   # 須 ngrok 或正式網域
ECPAY_STAGE=1
ADMIN_ALLOWLIST=<admin_email_or_id>

# 3. ngrok（本地測試綠界 ReturnURL 必用）
ngrok http 8000
# 將 HTTPS URL 填入 ECPAY_RETURN_URL，例：https://abc123.ngrok-free.app/api/v1/webhooks/ecpay

# 4. 啟動服務
# backend: flask run
# frontend: npm run dev
```

---

## MVP-2.1.1 DB 與模型

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| orders 表 | `supabase db push` 成功；或 SQL：`SELECT * FROM orders LIMIT 1` | [ ] |
| order_items 表 | SQL：`SELECT * FROM order_items LIMIT 1` | [ ] |
| payments 表 | SQL：`SELECT * FROM payments LIMIT 1` | [ ] |
| RLS 設定 | 登入後 GET /api/v1/orders 可取得自己訂單；他人訂單無法取得 | [ ] |

**Done**：migrations 可套用，RLS 正常。

---

## MVP-2.1.2 Hold 與逾時

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| 選票種 → 建立 order | 活動詳情選付費票種 → 建立訂單 → GET order 為 `status=holding` | [ ] |
| hold 扣名額 | 建立 holding 後，ticket_type `hold_count` +quantity | [ ] |
| hold_timeout | 15 分鐘內不付款，`release_expired_holds` 將 order → cancelled、釋放 hold_count | [ ] |
| 釋放後可再買 | 逾時釋放後，同一票種其他人可再 hold | [ ] |

**驗證指令**：
```sql
-- 建立 holding 後檢查
SELECT status, hold_expires_at FROM orders WHERE id = '<order_id>';
SELECT hold_count FROM ticket_types WHERE id = '<ticket_type_id>';
```

**Done**：Hold 建立後不付款，逾時釋放名額，他人可再買。

---

## MVP-2.2 綠界金流 ECPay（重點）

### 2.2.1 結帳流程與 Webhook

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| **建立付款** | 前端 / POST checkout → 取得 form_params + cashier_url → POST 導向綠界 | [ ] |
| **導向金流頁** | 瀏覽器成功跳轉綠界測試頁（payment-stage.ecpay.com.tw） | [ ] |
| **選擇付款** | 綠界頁可選信用卡，輸入測試卡 `4311-9522-2222-2222` | [ ] |
| **ReturnURL 可達** | ngrok 正常，綠界可 POST 回 `ECPAY_RETURN_URL` | [ ] |
| **Webhook 驗簽** | CheckMacValue 正確，RtnCode=1 時才處理 | [ ] |
| **冪等** | webhook_events 去重，同一 MerchantTradeNo 重送不重複出票 | [ ] |
| **僅 paid 觸發出票** | RtnCode≠1 或驗簽失敗 → 回 `1|OK` 不更新；成功才 paid→issued | [ ] |

**綠界端到端流程（手動）**：

1. 登入 → 活動詳情 → 選付費票種 → 建立訂單（holding）
2. 點「前往付款」→ 取得 checkout form_params
3. 前端 POST 至 `payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5`
4. 綠界頁選擇信用卡 → 輸入 `4311-9522-2222-2222`、CVV 任意、有效期限未來
5. 付款成功 → 綠界 POST 至 ReturnURL（ngrok 轉發到 backend）
6. 檢查：order status → paid → issued；tickets 已建立；我的票券有該票

**Webhook 驗證（若無法真人付款）**：

```bash
# 用 ecpay skill test-vectors 或模擬 POST 至 /api/v1/webhooks/ecpay
# 需正確 CheckMacValue（HashKey/HashIV 與 params 一致）
# RtnCode=1, MerchantTradeNo=對應 payment 的 external_id
```

**Done**：前端結帳 → 綠界付款頁 → Webhook 驗簽、冪等、出票。

### 2.2.2 訂單狀態機

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| 狀態流 | holding → pending_payment → paid → issued | [ ] |
| 僅 paid→issued | 單元測試 `test_order_state_machine` 通過 | [ ] |
| cancelled | 取消 holding 或逾時 → cancelled | [ ] |

**Done**：狀態流符合規格，僅 paid 可轉 issued。

---

## MVP-2.3 出票與補償

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| paid→issued | Webhook 成功後自動建立 tickets，order→issued | [ ] |
| 補償任務 | POST /api/v1/admin/compensate-paid-orders（Admin JWT）可手動觸發 | [ ] |
| 冪等 | 已 issued 訂單再跑補償不重複建立 tickets | [ ] |

**補償手動驗證**：
```bash
# 1. 取得 Admin JWT（登入 admin 帳號）
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<admin_email>","password":"<password>"}' | jq -r '.access_token')

# 2. 觸發補償
curl -X POST http://localhost:8000/api/v1/admin/compensate-paid-orders \
  -H "Authorization: Bearer $TOKEN"

# 預期：{"orders_compensated": N}
```

**Done**：付款成功自動出票；補償 job 可處理漏單。

---

## 綠界金流重點檢查清單

| 檢查項 | 說明 | 通過 |
|--------|------|------|
| ReturnURL 可從外網連線 | localhost 無效，需 ngrok 或正式網域 | [ ] |
| CheckMacValue 演算法 | 符合 ecpay skill guides/13；排除空值建立訂單、含空值驗證 Webhook | [ ] |
| 回應格式 | Webhook 回傳精確 `1|OK`，無多餘字元 | [ ] |
| 冪等與去重 | webhook_events 以 external_event_id 去重；MerchantTradeNo 對應 payment | [ ] |
| 狀態轉換 | pending_payment→paid 經 state machine 驗證；cancelled 不轉 paid | [ ] |
| hold_count | 出票時 hold_count -= v_to_create，補償亦然（0022） | [ ] |

---

## 單元 / 整合測試（自動驗證）

```bash
cd backend
uv run pytest app/tests/test_order_state_machine.py -v
uv run pytest app/tests/test_compensate_paid_orders.py -v
# 若有 payment/checkout 單元測試一併執行
```

---

## 驗收完成條件

- [ ] 2.1.1：orders / order_items / payments 表存在，RLS 正常
- [ ] 2.1.2：Hold 建立、逾時釋放、名額可再賣
- [ ] 2.2.1：前端結帳 → 綠界付款頁 → Webhook 驗簽、冪等、出票
- [ ] 2.2.2：訂單狀態機符合規格
- [ ] 2.3：付款成功自動出票；補償 API 可處理漏單
