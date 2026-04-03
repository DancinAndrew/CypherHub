# MVP-1 驗證文件（手動清單 + 邏輯驗證報告）

> 合併自：mvp1-manual-verification.md（手動清單）、mvp1-verification-checklist.md（步驟說明）、verification-report.md（邏輯分析）。
> 對應 `develop.md` 規格。依序執行可驗收 MVP-1 全功能。
>
> 勾選 `[ ]` 完成後改為 `[x]`。

---

## 一、前置：環境準備

- [ ] **1.1** 啟動 Supabase（local）
  ```bash
  docker compose -f infra/docker-compose.yml up -d
  # 或 supabase start
  ```

- [ ] **1.2** 確認 migration 已套用
  ```bash
  supabase db reset
  ```

- [ ] **1.3** 啟動後端
  ```bash
  cd backend && pip install -r requirements.txt && flask run
  ```
  - 預設 `http://localhost:8000`

- [ ] **1.4** 啟動前端
  ```bash
  cd frontend && npm install && npm run dev
  ```
  - 預設 `http://localhost:5173`

- [ ] **1.5** 設定 `.env`
  - `.env`：`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
  - `ADMIN_ALLOWLIST`：Admin 的 `user_id` 或 `email`（逗號分隔）
  - `RESEND_API_KEY`（選填，有則報名成功會寄信）

- [ ] **1.6** Supabase Auth Redirect URLs 含 `http://localhost:5173/reset-password`

---

## 二、MVP-1.0 核心閉環

### 2.1 使用者註冊 / 登入 / 登出

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | 開啟 `/login` | 看到 Sign In / Sign Up 切換 | [ ] |
| 2 | 點「Need an account? Sign up」→ 輸入 email + 密碼 → Submit | 註冊成功或提示收驗證信 | [ ] |
| 3 | 使用 Sign In 登入 | 成功導向首頁 | [ ] |
| 4 | 未登入狀態開啟 `/tickets` | 導向 `/login?redirect=/tickets` | [ ] |
| 5 | 登入後再開 `/tickets` | 可看到「我的票券」頁 | [ ] |
| 6 | 登出 | session 清除 | [ ] |
| 7 | 登出後造訪 `/tickets` → 登入 | 登入後自動導向 `/tickets` | [ ] |

### 2.2 公開活動列表與詳情

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | 未登入開啟 `/` | 看到活動列表（僅 published） | [ ] |
| 2 | `curl -s http://localhost:8000/api/v1/events \| jq '.'` | 回傳 `{ "items": [...] }` | [ ] |
| 3 | 點任一活動 → `/events/:eventId` | 有時間、地點、票種、描述 | [ ] |
| 4 | 未登入直接開活動 URL | 可瀏覽，不需登入 | [ ] |

### 2.3 免費報名

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | 未登入點活動頁報名鈕 | 導向 `/login?redirect=...` | [ ] |
| 2 | 登入後選票種 → 送出 | 報名成功 | [ ] |
| 3 | 開 `/tickets` | 看到剛報名的票券 | [ ] |
| 4 | 同帳號超過 `per_user_limit` | 400 `PER_USER_LIMIT_EXCEEDED` | [ ] |

### 2.4 我的票券與 QR

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | `/tickets` | 顯示已報名票券列表 | [ ] |
| 2 | 每張票有 QR + Copy Payload | 可顯示、可複製 | [ ] |
| 3 | 多張票的 `qr_secret` | 每張票不同 | [ ] |

### 2.5 主辦方申請與活動建立

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | `/organizer/apply` → 填名稱 → 送出 | 建立 org 成功 | [ ] |
| 2 | `/organizer/events/create` → 建立活動(published) | 活動建立成功 | [ ] |
| 3 | 建立票種（capacity, per_user_limit） | 票種建立成功 | [ ] |
| 4 | 回首頁 | 可看到剛建立的活動 | [ ] |

### 2.6 QR 核銷

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | 主辦方帳號 → `/organizer/checkin/:eventId` | 核銷頁 | [ ] |
| 2 | 輸入 ticket_id + qr_secret → Verify | `valid=true`, `can_checkin=true` | [ ] |
| 3 | Commit | `ok=true`, `already_checked_in=false` | [ ] |
| 4 | 同票再 Commit | `ok=true`, `already_checked_in=true`（冪等） | [ ] |
| 5 | 非主辦方成員 Verify | `valid=false`, `reason=FORBIDDEN` | [ ] |

---

## 三、MVP-1.1 ~ 1.5 功能

### 3.1 活動篩選（1.1）

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | 首頁點舞風/活動類型篩選 | 列表隨篩選變化 | [ ] |
| 2 | `?styles=hiphop,popping` | 回傳符合活動 | [ ] |
| 3 | `?types=cypher,battle` | 回傳符合活動 | [ ] |

### 3.2 Metadata 與私密備註（1.2）

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | Guest 開詳情 | 無 internal_note | [ ] |
| 2 | 主辦方編輯 | 有 internal_note 可編輯 | [ ] |
| 3 | 詳情頁 | 有報名時間、地圖、聯絡、社群、流程 | [ ] |

### 3.3 自訂報名表單（1.3）

| 序 | 操作 | 預期結果 | 勾選 |
|---|------|----------|------|
| 1 | 主辦方 → Form Builder 建立表單 | 成功 | [ ] |
| 2 | 用戶報名有表單票種 | 顯示動態表單 | [ ] |
| 3 | 主辦方 → Manage → Attendees | 可看到 answers | [ ] |

### 3.4 收尾功能（1.5）

| 序 | 項目 | 預期 | 勾選 |
|---|------|------|------|
| 1 | 忘記密碼 → 寄信 → 重設密碼 | 完整流程可走通 | [ ] |
| 2 | `/profile` 編輯個人資料 | 儲存成功 | [ ] |
| 3 | Email 寄送（有 Resend key） | 報名後收信 | [ ] |
| 4 | Email 寄送（無 key） | 報名成功、log stub | [ ] |
| 5 | 活動圖片上傳與輪播 | 可上傳、詳情顯示 | [ ] |
| 6 | 主辦方資訊 + 其他活動 | 詳情頁有主辦方區塊 | [ ] |
| 7 | 主辦方代重寄票券 | Manage → 重寄 → 參加者收信 | [ ] |
| 8 | 核銷統計 | 已入場/未入場、按票種 | [ ] |
| 9 | 搜尋（`?q=`）與日期篩選（`?from=&to=`） | 篩選正確 | [ ] |
| 10 | 分享活動按鈕 | 可複製 URL | [ ] |
| 11 | 編輯限制（capacity < sold_count 阻擋、已售票種不可刪） | 前端/API 阻擋 | [ ] |
| 12 | 活動狀態機（draft→published→ended/cancelled） | 流轉正確 | [ ] |
| 13 | Admin 後台（allowlist 帳號） | 可看全站活動 | [ ] |
| 14 | Admin 下架活動 | status=disabled，首頁不顯示 | [ ] |
| 15 | Rate Limiting（login 10/min、register 20/min、checkin 60/min） | 超限回 429 | [ ] |

---

## 四、業務邏輯驗證（register_free_v2 RPC）

| 檢查項目 | 預期行為 | 狀態 |
|----------|----------|------|
| 未登入 | AUTH_REQUIRED | ✓ |
| 數量 ≤ 0 | INVALID_QUANTITY | ✓ |
| 票種不存在 | TICKET_TYPE_NOT_FOUND | ✓ |
| 付費票 | PAID_TICKET_NOT_ALLOWED_IN_MVP1 | ✓ |
| 票種停售 | TICKET_TYPE_INACTIVE | ✓ |
| 活動未發佈 | EVENT_NOT_PUBLISHED | ✓ |
| 報名未開始 | SALE_NOT_STARTED | ✓ |
| 報名已結束 | SALE_ENDED | ✓ |
| 超過限購 | PER_USER_LIMIT_EXCEEDED | ✓ |
| 名額已滿 | SOLD_OUT | ✓ |
| 原子扣量 | FOR UPDATE + sold_count 同交易 | ✓ |
| 表單答案 | ticket_form_responses 存檔 | ✓ |

---

## 五、核銷邏輯驗證（verify_ticket_qr / commit_checkin）

| 檢查項目 | 預期行為 | 狀態 |
|----------|----------|------|
| 未登入 | AUTH_REQUIRED | ✓ |
| 非 organizer | is_event_member → FORBIDDEN | ✓ |
| 票券不屬於該活動 | event_id 比對 | ✓ |
| QR 不匹配 | qr_secret 比對 | ✓ |
| 首次核銷 | status→checked_in（atomic） | ✓ |
| 重複核銷 | 冪等、already_checked_in | ✓ |

---

## 六、與購票平台對照

| 流程階段 | 常見網站行為 | CypherHub 實作 | 一致 |
|----------|--------------|----------------|------|
| 瀏覽活動 | 公開列表、篩選 | `GET /events` + styles/types | ✓ |
| 活動詳情 | 時間地點、票種 | EventDetailView | ✓ |
| 登入 | Email + 密碼 | Supabase Auth | ✓ |
| 報名 | 選票 → 填表 → 送出 | DynamicForm → Register | ✓ |
| 防超賣 | 原子扣量 | FOR UPDATE + capacity check | ✓ |
| 出票 | QR + Email | ticket_id + qr_secret | ✓ |
| 核銷 | 掃 QR 一次性 | verify → commit（冪等） | ✓ |

**MVP-1 已知限制**：無購物車/金流（MVP-2）、無票券轉讓、Resend 可選。

---

## 七、驗證完成簽核

| 項目 | 日期 | 執行者 | 備註 |
|------|------|--------|------|
| MVP-1.0 核心閉環 | | | |
| MVP-1.1 活動篩選 | | | |
| MVP-1.2 Metadata | | | |
| MVP-1.3 報名表單 | | | |
| MVP-1.4 主辦方流程 | | | |
| MVP-1.5 收尾穩定化 | | | |

---

## 八、快速 API 驗證指令

```bash
curl -s http://localhost:8000/api/v1/health | jq
curl -s http://localhost:8000/api/v1/events | jq '.items | length'
curl -s "http://localhost:8000/api/v1/events?q=test&styles=hiphop" | jq
curl -s "http://localhost:8000/api/v1/events?from=2025-01-01&to=2025-12-31" | jq
```

---

## 九、相關驗證報告

| 報告 | 驗證內容 |
|------|----------|
| [api-integration-test-report.md](reports/api-integration-test-report.md) | GET /events、POST /register 無 mock 整合測試 |
| [email-service-test-report.md](reports/email-service-test-report.md) | email_service 單元測試（9 passed） |
| [rate-limit-test-report.md](reports/rate-limit-test-report.md) | Rate limiting 429 驗證 |
| [error-boundary-report.md](reports/error-boundary-report.md) | 前端 Error boundary |
| [navigate-button-report.md](reports/navigate-button-report.md) | 活動「導航」按鈕 |
