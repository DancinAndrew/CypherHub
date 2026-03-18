# email_service 單元測試 驗證報告

> 依據 note.md 優先級：測試 `_is_resend_available()` 分支、send 失敗時 log 行為

---

## 一、測試範圍

| 項目 | 說明 |
|------|------|
| `_is_resend_available()` | 三種分支：有 key、無 key、resend 未 import |
| `send_registration_success_email` | stub、Resend 成功、Resend 失敗（log warning、不 raise） |
| `send_ticket_email` | stub、Resend 失敗（log warning、re-raise）、to_email 空時 skip |

---

## 二、測試案例與結果

| 測試 | 驗證內容 | 結果 |
|------|----------|------|
| `test_is_resend_available_true_when_api_key_set` | RESEND_API_KEY 有值 → True | ✅ |
| `test_is_resend_available_false_when_api_key_empty` | RESEND_API_KEY 空 → False | ✅ |
| `test_is_resend_available_false_when_resend_not_imported` | resend=None → False | ✅ |
| `test_send_registration_stub_logs_when_not_available` | stub 分支記錄 `[email_stub]` info | ✅ |
| `test_send_registration_resend_success_logs_info` | Resend 成功記錄 `[email]` info、呼叫 send | ✅ |
| `test_send_registration_resend_failure_logs_warning_no_raise` | Resend 失敗 log warning、不 raise | ✅ |
| `test_send_ticket_stub_logs_when_not_available` | stub 分支記錄 `[email_stub]` info | ✅ |
| `test_send_ticket_resend_failure_logs_warning_and_raises` | Resend 失敗 log warning、re-raise | ✅ |
| `test_send_ticket_skipped_when_no_email` | to_email 空時 skip、記錄 skipped log | ✅ |

---

## 三、驗證指令

```bash
cd backend
source .venv/bin/activate
pytest app/tests/test_email_service.py -v
```

**預期**：9 passed

---

## 四、實作摘要

1. **計畫**：`docs/development/plans/email-service-test-plan.md`
2. **測試檔**：`backend/app/tests/test_email_service.py`
3. **Mock 策略**：
   - `_is_resend_available`：`monkeypatch.setenv` / `setattr(resend, None)` 控制
   - send 分支：`monkeypatch.setattr(email_service, "_is_resend_available", lambda: True/False)`
   - Resend API：`monkeypatch.setattr("app.services.email_service.resend.Emails.send", MagicMock)`
   - Log 驗證：`monkeypatch.setattr(app, "logger", MagicMock())`，斷言 `info` / `warning` 呼叫與參數

4. **行為差異**：
   - `send_registration_success_email` 失敗時僅 log，不 raise
   - `send_ticket_email` 失敗時 log 並 re-raise
