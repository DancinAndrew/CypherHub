# API 整合測試計畫

> 依據 note.md 低優先級建議：選 1–2 個關鍵 public endpoint 做**未 mock**整合測試。**已實作完成**。驗證見 [api-integration-test-report.md](../../verification/reports/api-integration-test-report.md)。

---

## 一、目標

| Endpoint | 說明 | Mock 狀態 |
|----------|------|------------|
| `GET /api/v1/events` | 列表公開活動 | **不 mock**，直連 Supabase |
| `POST /api/v1/events/<id>/register` | 免費報名（需 auth） | **不 mock**，直連 Supabase |

---

## 二、現況

- **GET /events**：現有 `test_events_filters.py` 使用 `monkeypatch` mock `events_service.list_public_events`，非整合測試
- **POST /register**：現有 `test_register_route_unit.py` mock `supabase_client`、`forms_service`、RPC，非整合測試
- **conftest**：Flask test client，無 dotenv 自動載入
- **CI**：`pytest -q` 預設不帶 Supabase env，會導致整合測試需跳過

---

## 三、策略

### 3.1 觸發條件

- 使用 `pytest.mark.integration`
- 當 `SUPABASE_URL` 未設定時，**跳過**整合測試（CI 預設）
- 本地開發：載入 `.env` 或手動 export，有 Supabase 時才跑

### 3.2 GET /events

- **無需 mock**：直接呼叫 endpoint
- **無需 seed**：空 DB 回 `{"items": []}` 亦為有效結果
- 驗證：`status_code == 200`、`items` 為 list、可選驗證 filter 參數

### 3.3 POST /register

- **無需 mock**：直連 Supabase
- **需 seed**：org → event (published) → ticket_type (free)
- **需 JWT**：用 `TEST_USER_EMAIL`、`TEST_USER_PASSWORD` 登入取得
- 若未設定上述 env，則**跳過** POST 整合測試

---

## 四、測試案例

| 測試 | Endpoint | 前置 | 驗證 |
|------|----------|------|------|
| `test_get_events_integration` | GET /events | SUPABASE_URL 已設 | 200、items 為 list |
| `test_post_register_integration` | POST /register | SUPABASE_URL + TEST_USER_* 已設 | 200、tickets 有資料 |

---

## 五、檔案變更

| 檔案 | 變更 |
|------|------|
| `backend/pyproject.toml` | 新增 `integration` marker |
| `backend/app/tests/conftest.py` | 若存在 `.env` 則載入（可選） |
| `backend/app/tests/test_api_integration.py` | **新增** 整合測試 |
| `.github/workflows/ci.yml` | 可選：integration  job（需 secrets） |

---

## 六、執行方式

```bash
# 僅單元測試（預設，CI 用）
pytest -q -m "not integration"

# 含整合測試（需 SUPABASE_URL）
cd backend && source .venv/bin/activate
export SUPABASE_URL=... SUPABASE_ANON_KEY=... SUPABASE_SERVICE_ROLE_KEY=...
# POST 整合需額外：
export TEST_USER_EMAIL=... TEST_USER_PASSWORD=...
pytest -v
```
