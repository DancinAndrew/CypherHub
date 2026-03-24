# MVP-2 驗證文件（計畫 + 報告）

> 合併自：mvp2-verification-plan.md + mvp2-verification-report.md。
> 對應 develop.md 503–578。訂單、綠界金流、出票補償。
> **狀態（2025-03）**：程式與 DB 已就緒，單元測試通過。綠界 E2E、Hold 逾時需手動驗證。

---

## 前置：環境準備

```bash
# 1. Migrations 已套用（含 0022）
supabase db push   # 或 repair 後 push

# 2. 後端 .env 必填（綠界測試）
ECPAY_MERCHANT_ID=3002607
ECPAY_HASH_KEY=pwFHCqoQZGmho4w6
ECPAY_HASH_IV=EkRm7iFT261dpevs
ECPAY_RETURN_URL=https://<ngrok-url>/api/v1/webhooks/ecpay
ECPAY_STAGE=1
ADMIN_ALLOWLIST=<admin_email_or_id>

# 3. ngrok（本地測試綠界 ReturnURL 必用）
ngrok http 8000

# 4. 啟動服務
# backend: flask run
# frontend: npm run dev
```

---

## 一、自動化測試（已通過）

```bash
cd backend
uv run pytest app/tests/test_order_state_machine.py app/tests/test_compensate_paid_orders.py -v
```

**結果**：14 passed, 1 skipped

| 測試檔 | 內容 |
|--------|------|
| test_order_state_machine.py | 狀態轉換合法/非法、can_transition |
| test_compensate_paid_orders.py | Admin JWT 必備、回傳 orders_compensated |

### CheckMacValue 驗證

- `ecpay.py`：`_ecpay_url_encode`、`_compute_checkmac`、`verify_webhook_checkmac`
- 建立訂單：`exclude_empty=True`（略過空值）
- 驗證 Webhook：`exclude_empty=False`（含空值）
- 與官方 SHA256 test-vectors 一致 ✅

---

## 二、手動驗證清單

### 2.1 DB 與模型

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| orders / order_items / payments 表 | `supabase db push` 成功 | [ ] |
| RLS | 登入後 GET orders 僅自己、他人 403/404 | [ ] |

### 2.2 Hold 與逾時

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| 建立 order → status=holding | 選付費票種 → 建立訂單 | [ ] |
| hold 扣名額 | ticket_type `hold_count` +quantity | [ ] |
| 逾時釋放 | 15 分鐘不付款 → `release_expired_holds` → cancelled | [ ] |
| 釋放後可再買 | 同票種他人可再 hold | [ ] |

### 2.3 綠界金流 ECPay（端到端）

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| 建立付款 | POST checkout → 取得 form_params + cashier_url | [ ] |
| 導向金流頁 | 跳轉 payment-stage.ecpay.com.tw | [ ] |
| 測試卡 | 輸入 `4311-9522-2222-2222`、CVV 任意 | [ ] |
| ReturnURL 可達 | ngrok POST 回 backend | [ ] |
| Webhook 驗簽 | CheckMacValue 正確 | [ ] |
| 冪等 | 同 MerchantTradeNo 重送不重複出票 | [ ] |
| 出票 | RtnCode=1 → paid → issued → tickets 建立 | [ ] |

**端到端流程**：登入 → 選付費票 → 建立訂單 → 前往付款 → 綠界測試卡 → 付款成功 → 確認 order=issued、tickets 建立、我的票券有該票。

### 2.4 出票與補償

| 項目 | 驗證方式 | 通過 |
|------|----------|------|
| paid → issued | Webhook 成功後自動建立 tickets | [ ] |
| 補償 API | `POST /admin/compensate-paid-orders` 回傳 `orders_compensated` | [ ] |
| 冪等 | 已 issued 不重複建立 | [ ] |

---

## 三、Migrations

| Migration | 內容 |
|-----------|------|
| 0017 | orders, order_items, payments, webhook_events |
| 0018 | compensate_paid_orders RPC |
| 0019 | create_hold_order RPC |
| 0020 | issue_tickets_for_order, hold_count |
| 0021 | cancel_holding_order RPC |
| 0022 | hold_count 冪等修正 |
| 0023 | refunds 表 |

---

## 四、程式結構

| 模組 | 路徑 |
|------|------|
| ECPay provider | `backend/app/providers/ecpay.py` |
| Payment service | `backend/app/services/payment_service.py` |
| Webhook 藍圖 | `backend/app/blueprints/webhooks.py` |
| 前端結帳 | `frontend/src/views/EventDetailView.vue` |
| API 客戶端 | `frontend/src/api/client.ts` |

---

## 五、驗收完成條件

- [ ] DB 表存在，RLS 正常
- [ ] Hold 建立、逾時釋放、名額可再賣
- [ ] 綠界端到端：結帳 → 付款 → Webhook → 出票
- [ ] 訂單狀態機（holding → paid → issued）
- [ ] 補償 API 可處理漏單
