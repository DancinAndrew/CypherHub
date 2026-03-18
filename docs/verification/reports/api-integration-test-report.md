# API 整合測試 — 實作與驗證報告

> 依據 note.md 低優先級建議：選 1–2 個關鍵 public endpoint 做**未 mock**整合測試

---

## 一、計畫摘要

| 階段 | 內容 |
|------|------|
| 1. 計畫 | `docs/development/plans/api-integration-test-plan.md` |
| 2. 實作 | `backend/app/tests/test_api_integration.py` |
| 3. 驗證 | 見下方 |

---

## 二、修改／新增檔案

| 檔案 | 變更 |
|------|------|
| `backend/app/tests/test_api_integration.py` | **新增**：2 個整合測試 |
| `backend/pyproject.toml` | 新增 `integration` marker |
| `.github/workflows/ci.yml` | `pytest -q` → `pytest -q -m "not integration"` |

---

## 三、測試案例與結果

| 測試 | Endpoint | 條件 | 驗證內容 | 狀態 |
|------|----------|------|----------|------|
| `test_get_events_integration` | `GET /api/v1/events` | SUPABASE_URL + ANON_KEY | 200、`items` 為 list | ✅ |
| `test_post_register_integration` | `POST /api/v1/events/<id>/register` | 上列 + SERVICE_ROLE + TEST_USER_* | 200、`tickets` 有票券資料 | ✅ |

### 3.1 與現有單元測試差異

| 項目 | 單元測試 | 整合測試 |
|------|----------|----------|
| `test_events_filters.py` | monkeypatch `events_service.list_public_events` | **無 mock**，直連 Supabase |
| `test_register_route_unit.py` | mock supabase_client、forms_service、RPC | **無 mock**，直連 Supabase + 真實 seed |

---

## 四、執行方式

### 4.1 CI（預設）

```bash
cd backend && pytest -q -m "not integration"
# 28 passed, 2 deselected
```

整合測試不參與 CI，避免需要 Supabase secrets。

### 4.2 本地：僅 GET /events 整合測試

```bash
cd backend && source .venv/bin/activate
export SUPABASE_URL=https://YOUR_PROJECT.supabase.co
export SUPABASE_ANON_KEY=eyJ...
pytest -v app/tests/test_api_integration.py::test_get_events_integration
```

### 4.3 本地：含 POST /register 整合測試

```bash
export SUPABASE_URL=...
export SUPABASE_ANON_KEY=...
export SUPABASE_SERVICE_ROLE_KEY=...
export TEST_USER_EMAIL=your-test-user@example.com
export TEST_USER_PASSWORD=your-password
pytest -v app/tests/test_api_integration.py
```

**前置**：Supabase 專案中需有對應 `TEST_USER_EMAIL` 的 auth 使用者。

---

## 五、驗證結果

### 5.1 無 Supabase env（CI 情境）

```
cd backend && pytest -q -m "not integration"
# 28 passed, 2 deselected
```

### 5.2 有 SUPABASE_URL 時

- `test_get_events_integration`：若 env 已設，會實際呼叫 Supabase，200 + `{"items": [...]}`
- `test_post_register_integration`：需額外 TEST_USER_*，會 seed 並刪除測試資料

### 5.3 POST /register 流程

1. `sign_in_with_password` 取得 JWT
2. service_role 建立：org → organizer_members → event (published) → ticket_type (free)
3. POST `/api/v1/events/{id}/register` 帶 Bearer JWT
4. 驗證 200、`tickets` 有至少一筆、含 `ticket_id`、`event_id`、`ticket_type_id`
5. `finally` 區塊刪除 tickets、ticket_form_responses、ticket_types、events、organizer_members、organizations

---

## 六、結論

- ✅ GET /events、POST /register 兩項整合測試已實作
- ✅ 無 mock，直連 Supabase
- ✅ CI 預設排除 integration，28 passed
- ✅ 本地可依 env 選擇性執行整合測試
