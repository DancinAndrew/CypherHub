# CypherHub 功能驗證報告

與常見購票網站（Accupass、KKTIX、Eventbrite）流程對照，確認 MVP-1 功能一致性与正確性。

---

## 一、購票平台標準流程對照表

| 流程階段 | 常見網站行為 | CypherHub 實作 | 一致性 |
|----------|--------------|----------------|--------|
| **1. 瀏覽活動** | 公開活動列表、篩選（類型/日期/地區） | 首頁 `GET /events`，篩選 dance_styles / event_types | ✓ |
| **2. 活動詳情** | 標題、時間地點、描述、票種（名稱/價格/剩餘/限購） | EventDetailView：完整 metadata、ticket_types（capacity、sold_count、per_user_limit） | ✓ |
| **3. 登入／註冊** | Email + 密碼，必要時 OAuth | Supabase Auth（signIn / signUp） | ✓ |
| **4. 選票／報名** | 選擇票種 → 填表單（主辦自訂）→ 送出 | 選票種 → DynamicForm（主辦 JSON schema）→ Register | ✓ |
| **5. 防超賣** | 原子扣量、限購檢查 | register_free_v2：FOR UPDATE + sold_count、per_user_limit、capacity | ✓ |
| **6. 出票** | 成功後顯示票券／QR、寄送 Email | 回傳 ticket_id + qr_secret，My Tickets 顯示 QR | ✓ |
| **7. 我的票券** | 票券列表、QR Code、可重寄 | MyTicketsView：QR、Copy Payload、Resend（Stub） | ✓ 註 |
| **8. 入場核銷** | 掃 QR → 一次性核銷、可重複掃（已核銷） | verify → commit，idempotent（already_checked_in），相機掃碼或手動 | ✓ |
| **9. 主辦管理** | 建立活動、票種、名單、核銷 | Apply → Events → Form Builder → Attendees → Check-in | ✓ |

註：Resend Email 目前為 stub（log），未串真實郵件服務，為 MVP-1 已知限制。

---

## 二、業務邏輯驗證（register_free_v2 RPC）

| 檢查項目 | 預期行為 | 實作 | 狀態 |
|----------|----------|------|------|
| 未登入 | 拒絕 | `auth.uid()` 為空 → AUTH_REQUIRED | ✓ |
| 數量 ≤ 0 | 拒絕 | INVALID_QUANTITY | ✓ |
| 票種不存在 | 拒絕 | TICKET_TYPE_NOT_FOUND | ✓ |
| 付費票 | 拒絕（MVP-1） | PAID_TICKET_NOT_ALLOWED_IN_MVP1 | ✓ |
| 票種停售 | 拒絕 | TICKET_TYPE_INACTIVE | ✓ |
| 活動未發佈 | 拒絕 | EVENT_NOT_PUBLISHED | ✓ |
| 報名未開始 | 拒絕 | SALE_NOT_STARTED | ✓ |
| 報名已結束 | 拒絕 | SALE_ENDED | ✓ |
| 超過每人限購 | 拒絕 | PER_USER_LIMIT_EXCEEDED | ✓ |
| 名額已滿 | 拒絕 | SOLD_OUT | ✓ |
| 原子扣量 | 不超賣 | FOR UPDATE + sold_count 同交易 | ✓ |
| 表單答案 | 存檔 | ticket_form_responses | ✓ |

---

## 三、核銷邏輯驗證（verify_ticket_qr / commit_checkin）

| 檢查項目 | 預期行為 | 實作 | 狀態 |
|----------|----------|------|------|
| 未登入 | 拒絕 | AUTH_REQUIRED | ✓ |
| 非 organizer | 拒絕 | is_event_member → FORBIDDEN | ✓ |
| 票券不屬於該活動 | 拒絕 | event_id 比對 | ✓ |
| QR 不匹配 | 拒絕 | qr_secret 比對 | ✓ |
| 首次核銷 | 成功、status→checked_in | atomic UPDATE | ✓ |
| 重複核銷 | 冪等、回傳 already_checked_in | idempotent，不報錯 | ✓ |

---

## 四、與常見網站差異（MVP-1 範圍內）

| 差異 | 說明 | 備註 |
|------|------|------|
| 無購物車 | 直接選票種報名，無「加入購物車 → 結帳」 | MVP-2 付費才需購物車／訂單 |
| 無金流 | 僅免費票 | MVP-2 才做 |
| quantity=1 UI | 前端目前固定 1 張，API 支援多張 | 可選在 UI 開放數量選擇 |
| 無訂單頁 | 成功後直接到 My Tickets | 免費報名通常不需要訂單摘要 |
| 無票券轉讓 | 不支援 | MVP-3 可再評估 |
| Resend 為 stub | 未寄真實 Email | 需串 SMTP／SendGrid 等 |

---

## 五、建議手動驗證清單

執行以下流程確認端到端正常：

1. **觀眾流程**  
   - 首頁瀏覽活動 → 篩選 → 點進詳情  
   - 選票種 → 填表單（若有）→ 送出  
   - 到 My Tickets 確認 QR  
   - 複製 payload 到核銷頁測試  

2. **主辦流程**  
   - 登入 → Organizer Apply  
   - 建立活動（published）→ 建立免費票種  
   - Form Builder 設定報名表單（可選）  
   - Attendees 查名單  
   - Check-in 手動輸入或掃碼核銷  

3. **邊界測試**  
   - 同用戶超過 per_user_limit 再報名 → 應失敗  
   - 名額滿後再報名 → 應 SOLD_OUT  
   - 同一張票核銷兩次 → 第二次應顯示 already_checked_in  

---

## 六、結論

MVP-1 流程與常見購票平台一致，包含：

- 活動瀏覽與篩選  
- 活動詳情與票種資訊  
- 登入／註冊  
- 選票、填表、報名  
- 防超賣與原子扣量  
- 票券與 QR 顯示  
- 核銷（驗證＋提交、冪等）  
- 主辦建立活動、票種、表單、名單與核銷  

已知限制（Resend stub、無金流、無購物車）均在 AGENTS.md 與 README 範圍內，不影響 MVP-1 核心流程驗證。
