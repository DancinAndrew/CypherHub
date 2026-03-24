# 背景任務選型分析：Hold 逾時與補償出票

> MVP-2 需實作：hold 逾時釋放、paid→issued 補償、Webhook 冪等。本文分析 RQ、Celery、pg_cron 三種方案，供選型與實作參考。  
> **結論已採用**：pg_cron + SQL RPC（`release_expired_holds`、`compensate_paid_orders`），migration 0018；Admin API 可手動觸發。

---

## 一、業務需求摘要

| 任務 | 觸發方式 | 頻率 | 說明 |
|------|----------|------|------|
| **Hold 逾時釋放** | 定時掃描 | 每 1–2 分鐘 | `status='holding' AND hold_expires_at < now()` → cancelled，扣回 hold_count |
| **補償出票** | 定時掃描 | 每 5–10 分鐘 | `status='paid' AND 無對應 tickets` → 建立 tickets，status→issued |
| **Webhook 處理** | 即時（HTTP 回調） | 事件驅動 | 非定時，由 Flask API 直接處理；冪等由 webhook_events 表保證 |

本文聚焦 **Hold 逾時** 與 **補償出票** 的實作方式。

---

## 二、方案比較總表

| 維度 | RQ (Redis Queue) | Celery | pg_cron + DB / Edge |
|------|------------------|--------|---------------------|
| **依賴** | Redis | Redis / RabbitMQ / SQS | 僅 Postgres（Supabase 內建 pg_cron） |
| **架構** | Worker 常駐 + 定時 enqueue | Worker 常駐 + beat 排程 | DB 定時執行 SQL 或 HTTP |
| **複雜度** | 低 | 高 | 低（DB 內）～ 中（加 Edge） |
| **本地開發** | 需起 Redis | 需起 Redis + worker | `supabase start` 即可，Cloud 已有 |
| **部署** | 需額外跑 rq worker + Redis | 需 beat + worker + broker | 無額外 process（Cloud） |
| **延遲** | 秒級（取決於 enqueue 頻率） | 秒級 | 取決於 cron 間隔（可到 1 秒） |
| **適用情境** | 小型專案、已有 Redis | 大型、多 worker、需監控 | 全 Supabase、不想管 infra |

---

## 三、方案 A：RQ (Redis Queue)

### 3.1 概述

Python 輕量任務佇列，僅支援 Redis 作為 broker。Worker 常駐，定時 job 由外部排程（cron / APScheduler）enqueue。

### 3.2 優點

- 設定簡單、程式碼少
- 文件清楚，學習成本低
- 與 Flask 整合容易
- 不需 Celery beat，排程可自訂（如 APScheduler）

### 3.3 缺點

- 需自建/維護 Redis
- 僅支援 Redis
- 高併發時效能不如 Celery/thread mode
- 監控較陽春（可選 rq-dashboard）

### 3.4 Hold 逾時實作方式

```python
# tasks/hold_expiry.py
def release_expired_holds():
    """掃描逾時 holding 訂單，取消並釋放 hold_count。"""
    # 呼叫 service 或直接操作 DB
    pass

# 使用 APScheduler 或系統 cron 定時呼叫
# scheduler.add_job(release_expired_holds, 'interval', minutes=1)
```

Worker 啟動：`rq worker`，定時 enqueue 由 Flask-APScheduler 或 cron 觸發 `queue.enqueue(release_expired_holds)`。

### 3.5 部署需求

| 組件 | 說明 |
|------|------|
| Redis | Docker / Railway Add-on / ElastiCache |
| rq worker | 與 Flask 同機或分開，`rq worker default` |
| 定時 enqueue | APScheduler 在 Flask 內，或 crontab 呼叫 API |

---

## 四、方案 B：Celery

### 4.1 概述

功能完整的分散式任務佇列，支援多種 broker（Redis、RabbitMQ、SQS）與 backend。Beat 負責定時排程，Worker 執行任務。

### 4.2 優點

- 功能豐富：優先級、鏈式任務、重試、監控（Flower）
- 多 broker 選擇
- 社群大、案例多
- 效能佳（尤其 thread 模式）

### 4.3 缺點

- 設定複雜（broker、backend、beat、worker）
- 學習曲線陡
- 對 MVP 規模偏重

### 4.4 Hold 逾時實作方式

```python
# celery_app.py
@celery.task
def release_expired_holds():
    ...

# 在 beat 排程
CELERY_BEAT_SCHEDULE = {
    'release-expired-holds': {
        'task': 'app.tasks.hold_expiry.release_expired_holds',
        'schedule': crontab(minute='*/1'),  # 每分鐘
    },
}
```

### 4.5 部署需求

| 組件 | 說明 |
|------|------|
| Broker | Redis / RabbitMQ |
| Celery beat | 排程 process |
| Celery worker | 執行 process |

---

## 五、方案 C：pg_cron（Supabase）

### 5.1 概述

PostgreSQL 擴展，在 DB 內以 cron 語法排程執行 SQL 或呼叫 HTTP。Supabase Cloud 已內建 pg_cron，可搭配 pg_net 呼叫 Edge Functions。

### 5.2 優點

- **零額外 infra**：DB 已在 Supabase，不需 Redis/worker
- **與 DB 同地**：掃描、更新同一交易，延遲低
- **Cloud 內建**：Supabase 已啟用，無需安裝
- **適合定時掃描**：hold 逾時本質就是「掃表＋更新」

### 5.3 缺點

- 僅適合「定時觸發」，不適合事件驅動、即時 queue
- 精細度受 cron 間隔限制（最短約 1 分鐘，視方案而定）
- 邏輯在 SQL / Edge，與 Flask 分離，除錯需熟悉 DB 或 Deno

### 5.4 Hold 逾時實作方式

#### 選項 C1：純 SQL（推薦）

將邏輯寫成 RPC，由 pg_cron 定時呼叫：

```sql
-- 0018_mvp2_hold_expiry_rpc.sql
-- 流程：鎖定逾時 orders → 更新 status → 依 order_items 扣回各 ticket_type 的 hold_count
CREATE OR REPLACE FUNCTION public.release_expired_holds()
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_order_id uuid;
  v_count int := 0;
BEGIN
  FOR v_order_id IN
    SELECT id FROM orders
    WHERE status = 'holding' AND hold_expires_at < now()
    FOR UPDATE SKIP LOCKED
  LOOP
    UPDATE orders SET status = 'cancelled', updated_at = now() WHERE id = v_order_id;
    UPDATE ticket_types tt
    SET hold_count = tt.hold_count - sub.qty
    FROM (
      SELECT ticket_type_id, SUM(quantity)::int AS qty
      FROM order_items WHERE order_id = v_order_id
      GROUP BY ticket_type_id
    ) sub
    WHERE tt.id = sub.ticket_type_id;
    v_count := v_count + 1;
  END LOOP;
  RETURN v_count;
END;
$$;

-- pg_cron 排程（Supabase Dashboard 或 migration）
SELECT cron.schedule('release-expired-holds', '1 minute', $$
  SELECT release_expired_holds();
$$);
```

#### 選項 C2：pg_cron → Edge Function → Flask API

若希望邏輯留在 Python：

1. pg_cron 定時呼叫 Edge Function（透過 pg_net HTTP）
2. Edge Function 轉呼叫 Flask `/internal/jobs/release-expired-holds`（需 API key 保護）
3. Flask 執行相同邏輯

優點：邏輯集中、易測。缺點：多一跳、需保護內網 API。

---

## 六、Hold 逾時流程設計（與方案無關）

不論採哪一方案，核心邏輯一致：

```
1. 掃描：status='holding' AND hold_expires_at < now()
2. 鎖定：FOR UPDATE SKIP LOCKED（避免併發衝突）
3. 更新 orders：status = 'cancelled'
4. 更新 ticket_types：hold_count -= quantity（依 order_items）
5. 記錄（可選）：寫入 audit_logs
```

**注意**：需依 `order_items` 彙總每個 `ticket_type_id` 的 quantity，再扣回對應 `hold_count`。單一 order 可能含多個 ticket_type。

---

## 七、補償出票流程

`status='paid'` 但尚未建立 tickets 的訂單，需背景補償：

```
1. 掃描：orders.status='paid' 且無對應 tickets（依 order_items 檢查）
2. 對每筆：建立 tickets、更新 status='issued'、sold_count += quantity、hold_count 不變（已從 holding 轉 paid 時處理）
```

補償邏輯可與 hold 逾時共用同一種排程機制（RQ task / Celery task / pg_cron job）。

---

## 八、建議選型

| 情境 | 建議方案 | 理由 |
|------|----------|------|
| **純 Supabase Cloud，無自建 Redis** | **pg_cron + SQL RPC** | 零額外服務，邏輯在 DB 內，維護成本最低 |
| **已有 Redis（Docker / Add-on）** | **RQ** | 輕量、易整合 Flask，MVP 足夠 |
| **預期高併發、需監控與進階功能** | **Celery** | 成熟穩定，Flower 監控佳 |

**CypherHub 建議**：  
- 若後端部署在 Railway/Render 等，可加 Redis add-on，採 **RQ**。  
- 若希望簡化 infra，優先採 **pg_cron + SQL RPC**，與現有 Supabase 架構一致。

---

## 九、實作狀態（方案 C 已採用）

| 項目 | 檔案 | 說明 |
|------|------|------|
| Migration | `supabase/migrations/0018_mvp2_background_tasks.sql` | pg_cron 啟用、order_id、兩個 RPC、排程 |
| `release_expired_holds()` | 同上 | 每分鐘，逾時 holding → cancelled |
| `compensate_paid_orders()` | 同上 | 每 5 分鐘，paid 補償出票 |
| tickets.order_id | 同上 | 付費訂單出票時關聯，補償時依此檢查 |

**注意**：Cloud 若 migration 中 `CREATE EXTENSION pg_cron` 失敗，請先在 Dashboard > Integrations > Cron 啟用。

---

## 十、參考連結

- [RQ 官方文件](https://python-rq.org/)
- [Celery 官方文件](https://docs.celeryq.dev/)
- [Supabase pg_cron](https://supabase.com/docs/guides/database/extensions/pg_cron)
- [Supabase Cron 排程 Edge Functions](https://supabase.com/docs/guides/functions/schedule-functions)
