# 金流開發 Best Practices

> **必讀**：開發 MVP-2 金流（ECPay、Stripe、PayPal 等）相關功能前，請完整閱讀本文。金流涉及金錢與資安，任何疏漏可能導致損失或爭議。

**參考來源**：ECPay 官方文件、AGENTS.md §10、note.md、develop.md、Stripe Webhook 規範、業界實務。

---

## 一、ECPay 文件與知識預備

### 1.1 官方文件入口

| 用途 | 連結 | 重點 |
|------|------|------|
| API 下載 | [綠界金流 API 文件](https://www.ecpay.com.tw/Service/API_Dwnld) | 下載「一般交易」「回傳規格」完整 PDF |
| 檢查碼機制 | [檢查碼機制](https://developers.ecpay.com.tw/29998/) | CheckMacValue 計算公式、SHA256 |
| 付款結果通知 | [付款結果通知](https://developers.ecpay.com.tw/28010/) | ReturnURL 回傳參數、RtnCode、SimulatePaid |
| 介接注意事項 | [介接注意事項](https://developers.ecpay.com.tw/2858/) | HashKey/HashIV 禁放前端、驗簽流程、防火牆 |
| 交易訊息代碼 | [交易訊息代碼表](https://developers.ecpay.com.tw/?p=28032) | RtnCode 失敗代碼對照 |

### 1.2 CheckMacValue 驗簽（必須實作）

**公式**：
```
CheckMacValue = SHA256(URLEncode(HashKey + Data明文 + HashIV))
```

**計算步驟**（依序、不可跳步）：
1. 將傳遞參數 **Data 明文**以字串取出（JSON 格式）
2. **前面**加 HashKey、**後面**加 HashIV
3. 整串做 **URL encode**（Python: `urllib.parse.quote(s, safe='')`；.NET 用 `Uri.EscapeDataString`）
4. 轉為**小寫**
5. 以 **SHA256** 壓碼產生雜湊值
6. 再轉**大寫** → 即為 CheckMacValue

**驗證時**：用收到的參數依上述步驟計算，與綠界回傳的 `CheckMacValue` 比對，**必須一致**才可信任 payload。未驗簽即處理，等同接受任意假造通知。

### 1.3 Form 參數（建立付款）

- 產生導向綠界金流頁的 Form，需包含：MerchantID、MerchantTradeNo、TradeAmt、ItemName、ReturnURL、NotifyURL、ChoosePayment、CheckMacValue 等
- CheckMacValue 計算方式同上，Data 為要傳送的參數鍵值依字母排序後組成的字串（詳見官方 PDF）
- **HashKey、HashIV 絕不可出現在前端**（JavaScript、HTML、CSS、env 暴露給 client）

### 1.4 付款完成通知（ReturnURL / NotifyURL）

- 綠界以 **Server POST** 方式傳送付款結果
- **Content-Type**：`application/json`（新 API）或 `application/x-www-form-urlencoded`（依實際文件）
- **必須**：
  1. 驗算 CheckMacValue，相符才處理
  2. 判斷 `RtnCode === 1` 才視為付款成功；非 1 勿出貨、勿更新為 paid
  3. 若 `SimulatePaid === 1`：為模擬付款，**不可出貨**，綠界不會撥款
  4. 正確處理完後，回傳字串 `1|OK` 給綠界（不可 `"1|OK"` 多餘引號、不可空白、不可 `1\OK` 等錯誤）
- **未正確回 1|OK**：綠界會 5~15 分鐘後重發，當天重複四次
- **external_event_id**：使用 `MerchantTradeNo`（特店交易編號）作為冪等去重鍵

### 1.5 環境與網路

- **測試**：申請 sandbox MerchantID，使用測試環境 URL
- **正式**：postgate.ecpay.com.tw、payment.ecpay.com.tw；防火牆需放行 TCP 443
- **ReturnURL**：不支援中文網址（需 punycode）；避免指定 port；建議 HTTPS

---

## 二、Webhook 冪等（Idempotency）

### 2.1 為何必須冪等

金流方（ECPay、Stripe、PayPal）在網路不穩定或我方回應異常時會**重送**同一筆通知。若未去重，同一筆付款可能被重複處理 → 重複出票、重複記帳、超賣。

### 2.2 實作方式（本專案已備）

`webhook_events` 表（見 `0017_mvp2_orders_payments_webhooks.sql`）：

| 欄位 | 用途 |
|------|------|
| provider | `'ecpay'`, `'stripe'` 等 |
| external_event_id | 金流方唯一識別（ECPay: MerchantTradeNo） |
| event_type | 如 `payment.success` |
| payload | 原始 payload（可除敏後存，勿 log 完整信用卡） |
| processed_at | 處理完成時間，NULL 表示尚未處理 |

**UNIQUE(provider, external_event_id)**：同一 provider + external_event_id 只能存在一筆。

### 2.3 處理流程（必須遵守）

1. 收到 Webhook → **先驗簽**（失敗則 4xx，不寫入任何資料）
2. 取 `external_event_id`（ECPay: `MerchantTradeNo`）
3. `INSERT INTO webhook_events (provider, external_event_id, event_type, payload) VALUES (...)`  
   **ON CONFLICT (provider, external_event_id) DO NOTHING**
4. 若 `INSERT` 影響 **0 列** → 已處理過，**直接回 200**（或 1|OK），不做任何業務邏輯
5. 若成功寫入 → 依 event_type 處理（更新 order、出票）、設 `processed_at`

**禁止**：先查詢再決定是否處理。必須用 INSERT + ON CONFLICT 的原子性，避免 race。

---

## 三、Payment Provider 介面設計

### 3.1 為何要抽象

- 未來可能支援 Stripe、PayPal
- 測試時可 mock，不呼叫真實金流
- 簽章邏輯、錯誤碼、重試策略各 provider 不同，集中介面較易維護

### 3.2 建議介面（Python）

```python
# 概念示意，非強制實作順序
class PaymentProvider(Protocol):
    def create_checkout_params(self, order_id: UUID, amount_cents: int, ...) -> dict: ...
    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool: ...
    def parse_webhook_payload(self, raw: bytes) -> WebhookPayload: ...
```

- `create_checkout_params`：回傳導向金流頁所需的參數或 form HTML
- `verify_webhook_signature`：驗簽，**失敗則不信任 payload**
- `parse_webhook_payload`：解析出 event_id、amount、status 等

各 provider（ECPayProvider、StripeProvider）實作此介面，`PaymentService` 依設定選用。

---

## 四、安全檢查清單

### 4.1 Secrets

- [ ] HashKey、HashIV、API Key 僅存在後端環境變數，**絕不**出現在前端、log、Git
- [ ] `.env.example` 僅放 placeholder，不填真實值
- [ ] 生產環境使用獨立 key，與測試環境分離

### 4.2 Webhook

- [ ] 收到 Webhook 先驗簽，未通過不回 200/1|OK，避免攻擊者誤導「已處理」
- [ ] 使用 `webhook_events` + `external_event_id` 做冪等，重送不重複出票
- [ ] Log 時不記錄完整信用卡號、CVV、完整 token

### 4.3 業務邏輯

- [ ] 僅 `RtnCode=1`（或對應成功碼）才將 order 更新為 paid
- [ ] `SimulatePaid=1` 時**不可出貨**，可標記為測試訂單或忽略
- [ ] 僅 `paid` 可轉 `issued`；hold timeout 需安全釋放名額（原子更新）

### 4.4 回應綠界

- [ ] 回傳 `1|OK` 時格式正確（無多餘空白、引號、換行）
- [ ] 建議先寫入 DB 再回 1|OK，避免回完後處理失敗卻無法重試

---

## 五、本專案相關檔案

| 檔案 | 說明 |
|------|------|
| `supabase/migrations/0017_mvp2_orders_payments_webhooks.sql` | orders、payments、webhook_events 表 |
| `backend/app/services/payment_service.py` | 目前為 stub，待實作 provider 介面 |
| `backend/app/blueprints/payments.py` | 付款相關 route stub |
| [../note.md](../note.md) | Webhook 冪等流程、ECPay 步驟草稿 |
| [../develop.md](../develop.md) | MVP-2.2 結帳流程、訂單狀態機 |
| [mvp2-readiness-checklist.md](./mvp2-readiness-checklist.md) | 進入 MVP-2 前檢查 |

---

## 六、參考連結

- [ECPay 檢查碼機制](https://developers.ecpay.com.tw/29998/)
- [ECPay 付款結果通知](https://developers.ecpay.com.tw/28010/)
- [ECPay 介接注意事項](https://developers.ecpay.com.tw/2858/)
- [綠界金流 API 下載](https://www.ecpay.com.tw/Service/API_Dwnld)
- [Stripe Webhook 驗證](https://stripe.com/docs/webhooks/signatures)（若未來支援 Stripe）
