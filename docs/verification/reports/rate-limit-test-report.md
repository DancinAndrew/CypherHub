# Rate Limit 單元測試 — 實作與驗證報告

> 依據 note.md 優先級：單元測試超過 limit 時回 429、不同 endpoint 各自 limit 正確

---

## 一、計畫摘要

| 階段 | 內容 |
|------|------|
| 1. 計畫 | `docs/development/plans/rate-limit-test-plan.md` |
| 2. 實作 | `backend/app/tests/test_rate_limit.py` + `app/__init__.py` 429 handler |
| 3. 驗證 | `pytest app/tests/test_rate_limit.py -v` 全部通過 |

---

## 二、修改檔案清單

| 檔案 | 變更 |
|------|------|
| `backend/app/__init__.py` | 新增 `RateLimitExceeded` import，於 Exception handler 內處理並回傳 429，訊息「操作過於頻繁，請稍後再試。」 |
| `backend/app/tests/test_rate_limit.py` | 新增 4 個 rate limit 單元測試 |
| `docs/development/plans/rate-limit-test-plan.md` | 新增測試計畫與實作紀錄 |

---

## 三、測試案例與結果

| 測試 | Endpoint | Limit | 驗證內容 | 結果 |
|------|----------|-------|----------|------|
| `test_auth_login_returns_429_over_limit` | `POST /api/v1/auth/login` | 10/min | 前 10 次 200，第 11 次 429 | ✅ PASS |
| `test_register_returns_429_over_limit` | `POST /api/v1/events/<id>/register` | 20/min | 前 20 次 200，第 21 次 429 | ✅ PASS |
| `test_checkin_verify_returns_429_over_limit` | `POST /api/v1/organizer/events/<id>/checkin/verify` | 60/min | 前 60 次 200，第 61 次 429 | ✅ PASS |
| `test_checkin_commit_returns_429_over_limit` | `POST /api/v1/organizer/events/<id>/checkin/commit` | 60/min | 前 60 次 200，第 61 次 429 | ✅ PASS |

---

## 四、Bug 修復（429 → 500）

**現象**：Rate limit 觸發時回傳 500，而非預期 429。

**原因**：Flask app 未處理 `flask_limiter.errors.RateLimitExceeded`，被通用 `Exception` handler 攔截並回傳 500。

**修正**：在 `handle_unexpected_error` 中先判斷 `isinstance(error, RateLimitExceeded)`，若是則回傳 429 與 `RATE_LIMIT_EXCEEDED`。

---

## 五、429 回應格式

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "操作過於頻繁，請稍後再試。",
    "details": null
  }
}
```

與前端 `errorMessages.ts` 中 429 處理一致。

---

## 六、驗證指令

```bash
cd backend && source .venv/bin/activate
pytest app/tests/test_rate_limit.py -v
# 4 passed

pytest -q
# 19 passed（全 suite）
```

---

## 七、結論

- ✅ 超過 limit 時回傳 429
- ✅ 各 endpoint limit 正確（10 / 20 / 60 per minute）
- ✅ 429 回應結構與前端預期一致
- ✅ 全體 pytest 通過
