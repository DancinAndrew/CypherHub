# MVP-1 完整手動驗證流程

> 對應 `develop.md` 198–482 行規格。依序執行可驗收 MVP-1 全功能。

---

## 前置：環境準備

```bash
# 1. 啟動 Supabase（local）
docker compose -f infra/docker-compose.yml up -d
# 或 supabase start

# 2. 確認 migration 已套用
supabase db reset   # 或 supabase migration up

# 3. 啟動後端
cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && flask run

# 4. 啟動前端
cd frontend && npm install && npm run dev

# 5. 設定 .env（至少需）
# - SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
# - ADMIN_ALLOWLIST=（Admin 的 user_id 或 email，逗號分隔）
# - RESEND_API_KEY=（選填，有則報名成功會寄信）
```

---

## MVP-1.0 核心閉環

### 1.0.1 註冊 / 登入 / 登出

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 開啟 `/login` | 看到 Sign In / Sign Up |
| 2 | 點「Need an account? Sign up」→ 輸入 email + 密碼 → Submit | 註冊成功或收到驗證信提示 |
| 3 | 登入後造訪 `/tickets` | 可看到我的票券（或空列表） |
| 4 | 登出（若有登出按鈕）或清除 session | 造訪 `/tickets` 時 redirect 到 `/login?redirect=/tickets` |
| 5 | 再次登入 | 會回到原本要去的 `/tickets` |

### 1.0.2 公開活動列表與詳情

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 未登入開啟 `/` | 看到活動列表（僅 published） |
| 2 | `curl http://localhost:8000/api/v1/events` | JSON 有 `items` 陣列 |
| 3 | 點任一活動 | 進入 `/events/:id`，有時間、地點、票種 |
| 4 | 未登入開啟活動 URL | 可直接瀏覽，不需登入 |

### 1.0.3 免費報名

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 未登入時點活動詳情的報名鈕 | redirect 到 `/login?redirect=...` |
| 2 | 登入後回到活動頁 → 選票種 → Submit | 報名成功，收到票券 |
| 3 | 同一帳號對同一票種超過 per_user_limit 報名 | API 回 400，`PER_USER_LIMIT_EXCEEDED` |

### 1.0.4 我的票券與 QR

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 登入後開 `/tickets` | 看到已報名票券列表 |
| 2 | 每張票有 QR 與 Payload | 可顯示、可複製（Copy Payload） |
| 3 | 每張票的 `qr_secret` | 各不相同 |

### 1.0.5 主辦方申請與活動建立

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 登入 → `/organizer/apply` → 填主辦方名稱 → 送出 | 建立 org 成功 |
| 2 | `/organizer/events/create` → 建立活動（status=published） | 活動建立成功 |
| 3 | 活動詳情頁 → 建立 ticket type（capacity, per_user_limit） | 票種建立成功 |
| 4 | 回首頁 | 可看到剛建立的活動 |

### 1.0.6 QR 核銷

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 主辦方帳號 → `/organizer/checkin/:eventId` | 可選活動、輸入 ticket_id + qr_secret 或掃 QR |
| 2 | Verify | `valid=true`, `can_checkin=true` |
| 3 | Commit | 第一次 `ok=true`, `already_checked_in=false` |
| 4 | 再對同一張票 Commit | `ok=true`, `already_checked_in=true` |
| 5 | 非主辦方成員嘗試 Verify | `valid=false`, `reason=FORBIDDEN` |

---

## MVP-1.1 活動篩選

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 首頁點舞風或活動類型篩選 | 列表隨篩選變化 |
| 2 | `curl "http://localhost:8000/api/v1/events?styles=hiphop,popping"` | 回傳符合舞風的活動 |
| 3 | `curl "http://localhost:8000/api/v1/events?types=cypher,battle"` | 回傳符合類型的活動 |

---

## MVP-1.2 活動 Metadata 與私密備註

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | Guest 開活動詳情 | 無 internal_note |
| 2 | 主辦方開活動編輯頁 | 有 internal_note 欄位可編輯 |
| 3 | 活動詳情頁 | 有 registration_start_at/end_at, map_url, contact, socials, schedule |

---

## MVP-1.3 自訂報名表單

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 主辦方 → Form Builder → 建立表單（選票種或活動級） | 表單建立成功 |
| 2 | 用戶報名時 | 顯示動態表單欄位 |
| 3 | 主辦方 → Manage → Attendees | 可看到 answers |

---

## MVP-1.4 主辦方多頁流程

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | `/organizer` | 主辦方首頁，可進 Apply / Events / Forms / Checkin / Manage |
| 2 | 各子頁導覽 | 可從首頁到各子頁，返回正常 |

---

## MVP-1.5 收尾與穩定化

### 1.5.1 忘記密碼 / 重設密碼

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 登入頁點「忘記密碼？」 | 切到 forgot 模式 |
| 2 | 輸入 email → 寄送重設密碼信 | 顯示成功訊息 |
| 3 | 收信 → 點連結 | 導向 `/reset-password` |
| 4 | 輸入新密碼兩次 → 更新 | 密碼更新成功，導向首頁 |

**備註**：Supabase Auth → URL Configuration → Redirect URLs 需含  
`http://localhost:5173/reset-password`。

### 1.5.1b 個人資料編輯

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 登入 → `/profile` | 可編輯 display_name、手機、Instagram、Facebook |
| 2 | 修改 display_name → 儲存 | 儲存成功，顯示「已儲存。」 |

### 1.5.1c Email 寄送

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 設定 `RESEND_API_KEY`、`RESEND_FROM_EMAIL` | 報名成功後可寄信 |
| 2 | 報名成功 | 收信，內容含活動名稱與「前往我的票券」連結 |
| 3 | 未設定 Resend | 報名仍成功，後端 log 有 stub 訊息 |

### 1.5.2a 活動圖片管理

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 主辦方編輯活動 → 上傳圖片 | 上傳成功，寫入 event_media |
| 2 | 活動詳情頁有圖時 | 顯示圖片輪播 |

### 1.5.2b 主辦方資訊與其他活動

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 開活動詳情 | 有主辦方區塊（名稱、簡介、聯絡） |
| 2 | 同主辦方有其他 published 活動 | 顯示「同主辦方其他活動」列表，可點進 |

### 1.5.2c 主辦方代參加者重寄票券

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 主辦方 → Manage → 選活動 → Attendees | 看到參加者名單 |
| 2 | 對某張票點「重寄」 | 觸發重寄，參加者收信 |
| 3 | 非主辦方呼叫 API | 403 |

### 1.5.2d 核銷統計 Dashboard

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 主辦方 → Manage → 選活動 | 顯示「已入場 N / 未入場 M」及按票種統計 |

### 1.5.2e 進階搜尋與篩選

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | `curl "http://localhost:8000/api/v1/events?q=關鍵字"` | 依活動名 LIKE 搜尋 |
| 2 | `curl "http://localhost:8000/api/v1/events?from=2025-01-01&to=2025-12-31"` | 日期區間篩選 |
| 3 | 首頁 UI | ⚠️ 若尚無關鍵字/日期 UI，可僅驗證 API |

### 1.5.2f 活動分享連結 ✅

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 活動詳情頁 | 有「分享活動」按鈕 |
| 2 | 點分享 → 複製 URL | 可複製 `/events/:eventId` 永久網址 |
| 3 | 貼到新分頁 | 可開啟活動詳情 |

### 1.5.2g 活動編輯限制（主辦方防呆）

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 編輯已 published 活動的敏感欄位 | ⚠️ 需有警告或限制 |
| 2 | 將已售出票種的 capacity 改成小於 sold_count | API 或前端應阻擋 |
| 3 | 刪除已有 sold_count 的票種 | 應阻擋 |

### 1.5.3 平台治理

| 步驟 | 操作 | 預期 |
|------|------|------|
| 1 | 建立活動時選 status=draft | 草稿建立，首頁看不到 |
| 2 | 將 draft → published | 首頁可見 |
| 3 | 已 ended/cancelled 活動 | 不可報名、不可核銷 |
| 4 | Admin（allowlist 用戶）開 `/admin` | 可進，看到全站活動列表 |
| 5 | Admin 對 published 活動點「下架」 | status=disabled，首頁不再顯示 |
| 6 | 短時間大量報名/核銷請求 | 超過限額回 429 ✅（flask-limiter 已實作） |

---

## ⚠️ 已知可能缺口（需再確認）

| 項目 | 說明 |
|------|------|
| 1.5.2e 前端 | Backend 有 `q`, `from`, `to`，HomeView 若無搜尋與日期 UI 則需補上 |
| 1.5.2g 編輯限制 | 已上架活動的敏感欄位警告，以及 capacity &lt; sold_count 的 API/前端阻擋需確認 |

**近期已完成**：1.5.2f 分享鈕 ✅、1.5.3 步驟 6 Rate limit ✅、導航按鈕 ✅、Error boundary ✅

---

## 快速回歸指令（API 層）

```bash
# 公開活動列表（含篩選）
curl -s "http://localhost:8000/api/v1/events" | jq '.items | length'
curl -s "http://localhost:8000/api/v1/events?q=test&styles=hiphop" | jq

# 健康檢查
curl -s "http://localhost:8000/api/v1/health"
```
