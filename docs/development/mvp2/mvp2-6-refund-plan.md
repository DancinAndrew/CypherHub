# MVP-2.6 基礎退款 — 詳細規劃

> 對應 develop.md 604–613。Phase 4.2：全額退款、退款狀態、金流 API、Email 通知。

---

## 一、現狀盤點

| 項目 | 狀態 | 實作位置 |
|------|------|----------|
| 訂單狀態機 | ✅ 已支援 paid/issued → refunded | `order_state_machine.py` |
| payments.raw_payload | ✅ Webhook 儲存 TradeNo、PaymentType | `payment_service.handle_ecpay_webhook` |
| ECPay DoAction | ⬜ 未實作 | - |
| refunds 表 | ⬜ 無 | - |
| 退款 Email | ⬜ 無 | - |

**ECPay 限制**：DoAction 退款僅支援信用卡（`Credit_CreditCard`、`Credit_Flexible_Installment`、`ApplePay` 等）。ATM/超商代碼/條碼需綠界後台手動處理。測試環境因無法提供實際授權，DoAction **不可用**，須正式環境。

---

## 二、流程與狀態

### 2.1 退款流程

1. Admin 呼叫 `POST /api/v1/admin/orders/:id/refund`（主辦方核准 = Admin 觸發）
2. 後端驗證：訂單 status 為 paid 或 issued、payment 為 ecpay 且 completed
3. 從 `payments.raw_payload` 取得 `TradeNo`、`PaymentType`
4. 若 `PaymentType` 非信用卡類 → 回傳 `REFUND_NOT_SUPPORTED`，引導至綠界後台
5. 建立 `refunds` 記錄，status = `requested`
6. 呼叫 ECPay `CreditDetail/DoAction`，Action=R，TotalAmount=訂單全額
7. 成功：更新 refund status=refunded、order status=refunded、payment status=refunded、寄 Email
8. 失敗：更新 refund status=failed，記錄 raw_response

### 2.2 退款狀態

| 狀態 | 說明 |
|------|------|
| requested | 已建立退款記錄，尚未或正在呼叫金流 |
| refunded | 金流退款成功 |
| failed | 金流退款失敗（API 錯誤、非信用卡等） |

---

## 三、檔案變更清單

| 檔案 | 變更 |
|------|------|
| `supabase/migrations/0023_mvp2_refunds_table.sql` | 新增 refunds 表 |
| `backend/app/providers/ecpay.py` | 新增 `do_action_refund()` |
| `backend/app/services/refund_service.py` | 退款流程邏輯 |
| `backend/app/services/email_service.py` | 新增 `send_refund_complete_email()` |
| `backend/app/blueprints/admin.py` | `POST /orders/<id>/refund` |
| `docs/development/develop.md` | MVP-2.6 Done 勾選 |

---

## 四、技術細節

### 4.1 refunds 表

```sql
CREATE TABLE refunds (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  amount_cents int NOT NULL,
  status text NOT NULL DEFAULT 'requested' CHECK (status IN ('requested','refunded','failed')),
  provider_trade_no text,
  raw_response jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz
);
```

### 4.2 ECPay DoAction

- URL: `https://payment.ecpay.com.tw/CreditDetail/DoAction`（正式）/ `https://payment-stage.ecpay.com.tw/CreditDetail/DoAction`（Stage 不支援）
- Method: POST, Content-Type: application/x-www-form-urlencoded
- Params: MerchantID, MerchantTradeNo, TradeNo, Action=R, TotalAmount, CheckMacValue
- Response: `RtnCode|RtnMsg`（例：`1|OK`）

### 4.3 PaymentType 信用卡判斷

支援退款的開頭：`Credit_`、`ApplePay`、`Flexible_Installment`。實作以 `raw_payload.get("PaymentType","")` 檢查是否為信用卡類。

---

## 五、驗收檢查表

- [ ] refunds 表建立成功
- [ ] Admin 可發起訂單退款（paid/issued）
- [ ] 非信用卡回傳明確錯誤
- [ ] 退款成功後 order/payment 狀態更新
- [ ] 退款成功後寄出 Email
- [ ] 退款失敗時 refund status=failed、可查 raw_response
