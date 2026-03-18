# email_service 單元測試計畫

> 依據 note.md：測試 `_is_resend_available()` 分支、send 失敗時 log 行為

---

## 一、現況

`EmailService` 位於 `backend/app/services/email_service.py`：

| 方法 | 行為 |
|------|------|
| `_is_resend_available()` | 回傳 `bool(api_key and resend is not None)` |
| `send_ticket_email` | 有 key → 呼叫 Resend；無 key → log `[email_stub]`；Resend 失敗 → log warning + **raise** |
| `send_registration_success_email` | 有 key → 呼叫 Resend；無 key → log `[email_stub]`；Resend 失敗 → log warning + **不 raise** |

---

## 二、測試策略

### 2.1 `_is_resend_available()` 分支

| 情境 | api_key | resend | 預期 |
|------|---------|--------|------|
| 有 key、resend 已 import | 非空 | 有 | `True` |
| 無 key | 空 | 有 | `False` |
| resend 為 None | 非空 | None | `False` |

使用 `EmailService()` 新建實例，以 `monkeypatch.setenv` 控制 `RESEND_API_KEY`。resend 為 None 時需 patch `app.services.email_service.resend`。

### 2.2 send 失敗時 log 行為

| 方法 | 失敗時行為 | 驗證 |
|------|------------|------|
| `send_ticket_email` | log warning、**raise** | 需 assert 有 raise、有 warning log |
| `send_registration_success_email` | log warning、**不 raise** | 需 assert 無 raise、有 warning log |

Mock `resend.Emails.send` 使其 raise Exception；使用 `caplog` 或 mock logger 檢查 log 內容。

### 2.3 stub 分支（無 key）

當 `_is_resend_available()` 為 False 時，兩方法皆應 log `[email_stub]`，不呼叫 Resend。

---

## 三、測試案例

| 測試 | 描述 |
|------|------|
| `test_is_resend_available_true_when_key_set` | 有 RESEND_API_KEY → True |
| `test_is_resend_available_false_when_no_key` | 無 key → False |
| `test_is_resend_available_false_when_resend_none` | resend=None → False |
| `test_send_ticket_email_stub_logs_when_not_available` | 無 key 時 log [email_stub] |
| `test_send_ticket_email_raises_and_logs_on_resend_failure` | Resend 失敗時 log warning + raise |
| `test_send_registration_success_email_stub_logs_when_not_available` | 無 key 時 log [email_stub] |
| `test_send_registration_success_email_logs_warning_no_raise_on_failure` | Resend 失敗時 log warning、不 raise |

---

## 四、實作注意

1. **App context**：`current_app.logger` 需在 Flask app context 內，使用 `with app.app_context():` 或依賴 `client` 觸發的 context。
2. **Singleton**：`email_service` 為模組級 singleton，在 `__init__` 讀取 env。測試時可 patch `email_service._api_key` 或新建 `EmailService()` 並在 `setenv` 後再 import/建構。
3. **resend mock**：patch `app.services.email_service.resend` 的 `Emails.send`，避免呼叫真實 API。

---

## 五、實作結果（已完成）

- 測試檔：`backend/app/tests/test_email_service.py`
- 9 個測試全數通過
- Log 驗證改用 mock `app.logger`（比 caplog 穩定）
