# Rate Limit 單元測試計畫

> 依據 note.md 中優先級：單元測試超過 limit 時回 429、不同 endpoint 各自 limit 正確。**已實作完成**。驗證見 [rate-limit-test-report.md](../../verification/reports/rate-limit-test-report.md)。

---

## 一、現況

| Endpoint | Limit | Blueprint |
|----------|-------|-----------|
| `POST /api/v1/auth/login` | 10/min | auth |
| `POST /api/v1/events/<id>/register` | 20/min | registrations |
| `POST /api/v1/organizer/events/<id>/checkin/verify` | 60/min | checkin |
| `POST /api/v1/organizer/events/<id>/checkin/commit` | 60/min | checkin |

- 使用 `flask-limiter`，`key_func=get_remote_address`
- `storage_uri="memory://"`（測試時與開發共用）
- 測試環境 `TESTING=True`，rate limiter 仍啟用

---

## 二、測試策略

### 2.1 隔離性
- 各 endpoint 有獨立 limit，測試彼此不影響
- 每個 test 只打單一 endpoint，連續請求直到超限

### 2.2 Mock 需求
- **login**：mock `auth._supabase_token`，避免呼叫 Supabase
- **register**：mock `supabase_client.get_user`、`call_rpc`、`forms_service.get_public_form`
- **checkin verify/commit**：mock `supabase_client.get_user`、`checkin_service`

### 2.3 驗證項目
1. 前 N 次請求回 200
2. 第 N+1 次請求回 429
3. 各 endpoint 之 N 符合預期（10 / 20 / 60）

---

## 三、測試案例

| 測試 | Endpoint | Limit | 請求數 | 預期 |
|------|----------|-------|--------|------|
| `test_auth_login_returns_429_over_limit` | POST /auth/login | 10/min | 11 | 第 11 次 429 |
| `test_register_returns_429_over_limit` | POST /events/<id>/register | 20/min | 21 | 第 21 次 429 |
| `test_checkin_verify_returns_429_over_limit` | POST /checkin/verify | 60/min | 61 | 第 61 次 429 |
| `test_checkin_commit_returns_429_over_limit` | POST /checkin/commit | 60/min | 61 | 第 61 次 429 |

---

## 四、實作結果（已完成）

- `backend/app/tests/test_rate_limit.py`：4 個測試皆通過
- `backend/app/__init__.py`：新增 `RateLimitExceeded` 處理，回傳 429 與 `RATE_LIMIT_EXCEEDED`、`操作過於頻繁，請稍後再試。`

---

## 五、實作注意

1. **flask-limiter 429 格式**：預設回 JSON `{"error": "Rate limit exceeded"}` 或類似，測 `status_code == 429` 即可
2. **checkin**：verify 與 commit 共用同一個 limit 或分開？依 decorator 各自獨立，故皆為 60/min
3. **test_client**：同一 test 內所有請求視為同一 IP，會共用該 endpoint 的 counter
