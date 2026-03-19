# MVP-2.4 庫存安全與背景任務 — 詳細規劃

> 對應 develop.md 579–589。Phase 3：逾時釋放、補償出票、Webhook 冪等、防超賣測試。

---

## 一、現狀盤點

| 項目 | 狀態 | 實作位置 |
|------|------|----------|
| 逾時釋放 | ✅ 已實作 | `0018` pg_cron、`release_expired_holds()` RPC、Admin API 手動觸發 |
| 補償出票 | ✅ 已實作 | `0018` pg_cron、`compensate_paid_orders()` RPC、Admin API |
| Webhook 冪等 | ✅ 已實作 | `webhook_events` (provider, external_event_id) UNIQUE、INSERT 去重 |
| 防超賣 | ⬜ 需補測 | `create_hold_order` RPC 用 `FOR UPDATE` 鎖定，需 pytest 併發驗證 |

---

## 二、Done 條件解讀

develop.md：`RQ/Redis 或類似 queue；上述 job 可執行；有併發測試。`

- **Queue**：專案採用 pg_cron（見 `background-tasks-analysis.md` 方案 C），等同「類似 queue」。
- **Job 可執行**：pg_cron 排程每 1 分鐘 / 每 5 分鐘；Admin API 可手動觸發。
- **併發測試**：需新增 pytest，驗證併發搶票不超賣。

---

## 三、待實作項目

### 3.1 Webhook 冪等單元測試

**目標**：同一 MerchantTradeNo 重送 → 僅處理一次，不回報錯。

**策略**：mock 驗簽、兩次 POST 相同 payload → 第二次回傳 `1|OK` 且不變更 DB（用 mock 或 spy 檢查 `issue_tickets_for_order` 僅被呼叫一次）。

| 步驟 | 說明 |
|------|------|
| 1 | Mock `verify_webhook_checkmac` 恆 True |
| 2 | 第一次 POST → 應成功、出票 |
| 3 | 第二次 POST 相同 payload → 回 `1|OK`，出票不再執行 |
| 4 | 可 mock `webhook_events.insert` 第二次拋出 UNIQUE 違規，驗證 handler 回傳 `1|OK` |

### 3.2 防超賣併發測試

**目標**：capacity=1 時，2 人同時 hold → 1 成功、1 SOLD_OUT。

**策略**：整合測試，需真實 Supabase（或 local）與 2 個測試用戶。

| 步驟 | 說明 |
|------|------|
| 1 | Fixture：建立 event、ticket_type（capacity=1, sold_count=0, hold_count=0） |
| 2 | 取得 2 個用戶 JWT（TEST_USER_1, TEST_USER_2 或 seed 用戶） |
| 3 | `ThreadPoolExecutor` 同時執行 2 次 `orders_service.create_hold_order(jwt, items)` |
| 4 | 斷言：1 個回傳 order_id，1 個 raise AppError(code="SOLD_OUT") |
| 5 | 可選：驗證 `hold_count == 1`、`sold_count == 0` |

**依賴**：需 `SUPABASE_URL`、`SUPABASE_ANON_KEY`、2 組可登入的測試帳密。無則 skip。

---

## 四、檔案變更清單

| 檔案 | 變更 |
|------|------|
| `backend/app/tests/test_webhook_idempotency.py` | 新增，Webhook 冪等測試 |
| `backend/app/tests/test_hold_concurrency.py` | 新增，防超賣併發測試（整合，可 skip） |
| `docs/development/develop.md` | MVP-2.4 Done 條件勾選、備註 pg_cron 為 queue 替代 |

---

## 五、驗收檢查表

- [x] Webhook 冪等單元測試通過（`test_webhook_idempotency.py`）
- [x] 防超賣併發測試（`test_hold_concurrency.py`）：有 Supabase + 網路時通過；沙盒/無網路時 skip
- [x] `uv run pytest app/tests/test_webhook_idempotency.py app/tests/test_hold_concurrency.py -v` 全過或合理 skip
