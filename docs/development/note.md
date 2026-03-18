# 使用者體驗

- [ ] **活動日曆與提醒**：集中檢視報名／參加的活動；比賽前 7 天／3 天／1 天／當天 自訂通知（Email + 站內可選）
  - 個人日曆視圖：月曆／週曆顯示已報名／已加入的活動
  - 可匯出 iCal（與 Google Calendar、Apple Calendar 同步）
- [ ] **街舞活動客製化**：附近抽煙地點、便利商店、小吃、聚餐餐廳推薦
  - 活動場地周邊資訊：抽煙區、便利商店、小吃、聚餐餐廳（依距離／評分排序）
  - 串接 Google Places API 或 OpenStreetMap／Overpass 取得周邊 POI
- [x] **導航整合**：活動頁面加入「導航」按鈕，串接 Google Map ✅
  - 開啟 Google Maps：`https://www.google.com/maps/dir/?api=1&destination={lat},{lng}`
  - 已實作：EventDetailView「導航」按鈕，map_url 或 lat/lng，見 [navigate-button-report.md](../verification/reports/navigate-button-report.md)
- [ ] **AI 活動推薦**：依使用者過往參與偏好推薦街舞活動
  - 基於：參加／報名過的活動（舞風、地區、主辦方、時間偏好）
  - 輸出：個人化街舞活動推薦列表
  - 可選：協同過濾、內容特徵 + 輕量 embedding
- [ ] **即時活動進度（參加者視角）**：參加者即時看到目前進度，減少「不知道比到哪」的狀況

---

# 主辦方／營運工具

- [ ] **即時活動進度**：主辦方可更新進度（如海選、晉級等），參加者可即時查看
  - 主辦方可即時更新階段：海選中 → 晉級公布 → 決賽等
  - 技術：WebSocket 或 SSE 即時推送、或短輪詢
- [ ] **計分統計**：評審對選手各項目的評分（如美味評審對美味選手），自動匯總、視覺化，避免手算
- [ ] **評分標準模版**：可設定權重（如基礎 40%、音樂性 20% 等）→ 自動計算總分與排名
- **計分計算方式（待研究，實作計分時必查）**
  - 非線性計分：log、加權曲線、縮放公式等 — 部分比賽規則特殊，需查實際計算邏輯

- [ ] **通行證／參加票核發（主辦方驗證制）**（構想）
  - 流程：用戶報名 → 用戶付款（免費活動也需等舉辦人驗證）→ 舉辦人驗證 → 驗證通過才發放參加票券／通行證
  - 票券核發權在 Organizer，非自動出票
  - 舉辦人驗證優化（可選）：
    - 篩選用戶基本資料（profiles、報名表 answers）
    - 顯示活動出席率（報名場次 vs 實際 check-in 比例）
    - 其他歷史參與資料輔助審核

---

# 系統擴展性

- **架構與併發**
  - 分散式系統（distributed systems）
  - 系統設計（system design）
  - 高併發處理（搶票、hold 逾時、冪等、鎖與佇列）
- **部署與上雲（個人 side project 最小化）**
  - 前端：Vercel（Vue/Vite 靜態站，Preview 分支）
  - 後端：選一即可 — Railway / Render / Fly.io（容器或直接跑 Flask）
  - DB/Auth：Supabase Cloud 已算上雲，不需自建
  - 網域與 DNS：Namecheap 買網域 + Cloudflare 或 Vercel 綁定
- **DevOps / 運維（簡單版）**
  - CI：GitHub Actions — 跑 pytest、ruff、前端 build，PR 時自動跑
  - 環境變數：各平台後台填（Vercel / Railway 等），勿 commit secrets
  - 日誌：先 stdout → 用平台內建 log 查；要集中再考慮 Logtail / Axiom（可選）
- **監控與儀表板**
  - 可用性：UptimeRobot — 對 API + 前端 URL 做 HTTP 偵測、故障告警
  - 錯誤：Sentry — 前/後端 exception、source map、release 對應
  - 產品分析（可選）：PostHog — 事件、漏斗、Session 錄影
  - 儀表板：個人專案用 UptimeRobot + Sentry 內建頁面即可；要自建再考慮 Grafana

工具細節與對照見 [Tools.md](./Tools.md)、[develop.md](./develop.md) 推薦套件章節。

---

# 與 MVP2 相關的技術債

| MVP2 功能 | 現有基礎 | 進入前可預先做的事 |
|-----------|----------|---------------------|
| Hold + 逾時 | 無 | 先設計 orders 表、訂單狀態機 schema 草稿 |
| Webhook 冪等 | 無 | 可先建 `webhook_events` 表與 idempotency key 欄位 |
| 金流 | 無 | 研讀 ECPay 文件、設計 payment_attempts / payments 表 |

---

## 詳細執行計畫

### 一、Hold + 逾時（訂單與狀態機）

**步驟 1.1** 建立 orders / order_items migration（`0016_mvp2_orders.sql`）

```sql
-- order_status enum
CREATE TYPE order_status AS ENUM (
  'created', 'holding', 'pending_payment', 'paid', 'issued', 'cancelled', 'refunded'
);

-- orders 表
CREATE TABLE orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id),
  status order_status NOT NULL DEFAULT 'created',
  total_cents int NOT NULL DEFAULT 0,
  currency text NOT NULL DEFAULT 'TWD',
  hold_expires_at timestamptz NULL,  -- holding 逾時時間
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- order_items 表
CREATE TABLE order_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  ticket_type_id uuid NOT NULL REFERENCES ticket_types(id),
  quantity int NOT NULL CHECK (quantity >= 1),
  price_cents int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ticket_types 新增 hold_count 欄位
ALTER TABLE ticket_types ADD COLUMN IF NOT EXISTS hold_count int NOT NULL DEFAULT 0;
-- 調整 constraint：sold_count + hold_count <= capacity
ALTER TABLE ticket_types DROP CONSTRAINT IF EXISTS ticket_types_sold_check;
ALTER TABLE ticket_types ADD CONSTRAINT ticket_types_inventory_check
  CHECK (sold_count >= 0 AND hold_count >= 0 AND sold_count + hold_count <= capacity);
```

**步驟 1.2** 訂單狀態機草稿（可寫成註解或 doc）

| 狀態 | 可轉換至 | 觸發條件 |
|------|----------|----------|
| created | holding | 用戶選票種，呼叫 hold API |
| holding | pending_payment, cancelled | 導向付款 or 逾時/手動取消 |
| pending_payment | paid, cancelled | Webhook 確認付款 or 逾時 |
| paid | issued | Webhook 收到後建立 tickets |
| issued | refunded | （MVP2 後期）退款 |
| cancelled | - | 終態 |
| refunded | - | 終態 |

**步驟 1.3** Hold 邏輯流程草稿

1. 檢查 `sold_count + hold_count + quantity <= capacity`
2. `hold_count += quantity`（原子更新）
3. 建立 order（status=holding）、order_items、`hold_expires_at = now() + 15min`
4. 逾時 job 定時掃描 `hold_expires_at < now() AND status = 'holding'` → 設 cancelled、`hold_count -= quantity`

**驗證 1.1**

```bash
cd supabase && supabase db reset  # 或 migrate
# 預期：migration 套用成功，無 constraint 錯誤
```

---

### 二、Webhook 冪等

**步驟 2.1** 建立 webhook_events 表（可併入 `0016` 或另開 `0017_mvp2_webhook_events.sql`）

```sql
CREATE TABLE webhook_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,           -- 'ecpay', 'stripe' 等
  external_event_id text NOT NULL,  -- 金流方回傳的 MerchantTradeNo / id
  event_type text NOT NULL,         -- 'payment.success' 等
  payload jsonb NULL,               -- 原始 payload（除敏後可選存）
  processed_at timestamptz NULL,    -- 處理完成時間
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(provider, external_event_id)
);

CREATE INDEX idx_webhook_events_provider_external ON webhook_events(provider, external_event_id);
```

**步驟 2.2** 處理流程草稿

1. 收到 Webhook → 驗簽
2. `INSERT INTO webhook_events (provider, external_event_id, event_type, payload) VALUES (...)` ON CONFLICT DO NOTHING
3. 若 `INSERT` 影響 0 列 → 已處理過，直接回 200
4. 若成功寫入 → 依 event_type 處理（更新 order、出票）、設 `processed_at`

**驗證 2.1**

- 手動插入重複 `(provider, external_event_id)` → 應觸發 UNIQUE 違規
- 模擬 Webhook 重送同一筆 → 第二次應被忽略、不重複出票

---

### 三、金流（ECPay）

> **詳見** [.cursor/skills/ecpay](../../.cursor/skills/ecpay) — ECPay 官方 Skill，含 AIO、CheckMacValue、Webhook。

**步驟 3.1** 研讀 ECPay 文件

- [綠界金流 API 文件](https://www.ecpay.com.tw/Service/API_Dwnld) — 下載「一般交易」「回傳規格」
- 重點：付款建立（產生 Form HTML/參數）、NotifyURL / ReturnURL、驗簽演算法（SHA256）
- 測試環境：綠界提供 sandbox，需申請測試 MerchantID

**步驟 3.2** 建立 payments 表（併入 `0016` 或 `0017`）

```sql
CREATE TABLE payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES orders(id),
  provider text NOT NULL DEFAULT 'ecpay',
  external_id text NULL,            -- 綠界 MerchantTradeNo
  amount_cents int NOT NULL,
  currency text NOT NULL DEFAULT 'TWD',
  status text NOT NULL,             -- 'pending', 'succeeded', 'failed', 'refunded'
  raw_response jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_payments_external ON payments(provider, external_id);
```

**步驟 3.3** API 設計草稿

| 端點 | 說明 |
|------|------|
| POST /api/v1/orders | 建立 hold 訂單，回傳 order_id |
| POST /api/v1/orders/:id/checkout | 產生 ECPay 表單參數，回傳 redirect_url 或 form_data |
| POST /api/v1/webhooks/ecpay | 接收綠界 NotifyURL，驗簽、冪等、更新 order + 出票 |

**步驟 3.4** 環境變數

```
ECPAY_MERCHANT_ID=
ECPAY_HASH_KEY=
ECPAY_HASH_IV=
ECPAY_API_URL=  # 測試 / 正式 URL
```

**驗證 3.1**

- 本地或 staging 跑 `supabase db reset` 確認 migration 正常
- 手動呼叫 checkout 取得 Form 參數，在綠界 sandbox 完成一筆測試付款
- 模擬 Webhook 回調 → 訂單應轉 paid、tickets 建立

---

### 四、執行順序建議

1. **第 1 週**：Migration 0016（orders, order_items, webhook_events, payments）+ RLS 草稿
2. **第 2 週**：Hold API 邏輯（不含逾時 job）、訂單狀態機實作
3. **第 3 週**：ECPay 串接（checkout + Webhook 驗簽、冪等）
4. **第 4 週**：逾時釋放 job（RQ/Redis 或 pg_cron）、補償出票 job

**檢查清單**

| 順序 | 項目 | 產出 | 驗證 |
|------|------|------|------|
| 1 | 0016 orders schema | orders、order_items、status enum、hold_count | migration up OK |
| 2 | 0017 webhook_events | 表 + idempotency unique | migration up OK |
| 3 | 0018 payments | payments 表、index | migration up OK |
| 4 | RLS 草稿 | orders/payments 的 select/insert 政策 | 可註解於 migration |
| 5 | ECPay 研讀 | 驗簽、NotifyURL 觸發時機紀錄 | develop.md 或 note |

**一鍵驗證**

```bash
cd /path/to/CypherHub && supabase db reset
# 預期：所有 migration 0016–0018 皆成功
```