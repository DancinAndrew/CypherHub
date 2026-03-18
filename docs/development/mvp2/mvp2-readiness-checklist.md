# MVP-2 就緒檢查清單

> 進入 MVP-2 開發前需完成的項目。依據 2025-03 全 repo 審計整理。

---

## 一、MVP-1.5 狀態 ✅

- [x] MVP-1.0 ～ MVP-1.5 功能皆已實作
- [x] 文件已同步（develop.md、README、verification reports）
- [x] Rate limiting、Error boundary、導航、分享等收尾完成

---

## 二、Blocker（進入 MVP-2 前必做）

| 項目 | 說明 | 狀態 |
|------|------|------|
| 本地 Python 版本 | 需 Python 3.12+，與 CI 一致 | 確認 `.python-version` 或 venv |
| pytest 全過 | `cd backend && pytest -q -m "not integration"` | 確認 |
| 前端 build | `cd frontend && npm run build` | 確認 |
| 文件一致性 | README migrations、AGENTS.md、SEC-3 已更新 | ✅ 已修正 |

---

## 三、MVP-2 前置準備

### 3.1 Schema 設計 ✅

| 項目 | 說明 | 狀態 |
|------|------|------|
| orders 表 | user_id, status, total_cents, hold_expires_at | ✅ 0017 |
| order_items 表 | order_id, ticket_type_id, quantity, price_cents | ✅ 0017 |
| payments 表 | order_id, provider, external_id, amount_cents, status | ✅ 0017 |
| webhook_events 表 | provider, external_event_id, UNIQUE 去重 | ✅ 0017 |
| ticket_types.hold_count | sold_count + hold_count ≤ capacity | ✅ 0017 |

### 3.2 背景任務 ✅

| 選項 | 說明 | 狀態 |
|------|------|------|
| **pg_cron + SQL RPC** | 全在 Supabase，零額外 infra | ✅ 已採用，見 [background-tasks-analysis.md](./background-tasks-analysis.md) |
| RQ + Redis | 輕量，hold 逾時、補償出票 | 備選 |
| Celery | 功能多，較重 | 進階需求 |

**實作**：`0018_mvp2_background_tasks.sql`
- `release_expired_holds()`：每分鐘掃描逾時 holding → cancelled，扣回 hold_count
- `compensate_paid_orders()`：每 5 分鐘補償 paid 但未出票的訂單

### 3.3 金流

| 項目 | 說明 | 狀態 |
|------|------|------|
| **Best practices** | 開發前必讀 [payment-best-practices.md](./payment-best-practices.md) | ⬜ |
| ECPay 文件 | 研讀 Webhook 驗簽、Form 參數 | ⬜ |
| payment_service | 抽出 provider 介面 | 目前為 stub |
| Webhook 冪等 | webhook_event_id 去重 | ⬜ |

---

## 四、可選整理（非 blocker）

| 項目 | 說明 |
|------|------|
| XSS 審查 | develop.md SEC-3 標「需審查」；目前無 `v-html` |
| Log 審查 | 確保不 log 密碼、完整 token |
| Sentry | error.ts 有 TODO 預留點 |
| Stub blueprints | orders/payments/settlements 已註冊空路由，MVP-2 會實作 |

---

## 五、結論

**MVP-1.5 已完成**，程式與文件狀態良好。**可進入 MVP-2** 條件：

1. 本地 pytest、frontend build 確認通過
2. 完成 orders / order_items / payments migration 設計並套用
3. ~~選定背景任務方案（RQ / pg_cron）~~ ✅ pg_cron + SQL RPC 已實作
4. 研讀 [payment-best-practices.md](./payment-best-practices.md) 與 ECPay 文件，規劃 Webhook 架構

建議先做 MVP-2.1（訂單與 hold）的 schema 與基本 flow，再接入 ECPay。
