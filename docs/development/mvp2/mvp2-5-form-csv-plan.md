# MVP-2.5 報名表單擴充 — 詳細規劃

> 對應 develop.md 592–600。Phase 4.1：新欄位型別、票種綁定、名單匯出 CSV。**已實作完成（2025-03）。**

---

## 一、現狀盤點

| 項目 | 狀態 | 實作位置 |
|------|------|----------|
| 新欄位型別 | ✅ 已支援 | `FormFieldType`：text, number, email, phone, url, date, single_select, dropdown, multi_select, checkbox |
| DynamicForm | ✅ 已支援 | `DynamicForm.vue` 對應上述型別 |
| 票種綁定 | ✅ 已支援 | `event_forms.ticket_type_id`、Form Builder 可選票種 |
| 名單匯出 CSV | ✅ 已實作 | `OrganizerManageView.vue`「匯出 CSV」按鈕、`exportAttendeesCsv()`，含 answers、安全跳脫 |

---

## 二、待實作項目

### 2.1 名單匯出 CSV

**目標**：主辦方在 OrganizerManageView（名單頁）可下載 CSV，含 ticket_id、user_id、狀態、核銷時間、報名答案欄位。

**策略**：前端匯出，無需後端變更。`organizerFetchAttendees` 已回傳 `answers`，於前端轉 CSV 並觸發下載。

| 步驟 | 說明 |
|------|------|
| 1 | OrganizerManageView 新增「匯出 CSV」按鈕 |
| 2 | 實作 `exportAttendeesToCsv(items)`：將 attendees 轉為 CSV 字串 |
| 3 | 欄位：ticket_id, user_id, status, checked_in_at, ticket_type_id + answers 各 key |
| 4 | 使用 `Blob` + `URL.createObjectURL` + `<a download>` 觸發下載 |

**CSV 欄位順序**：固定欄位先，動態 answers 以首筆出現的 key 順序（或字母排序）排列。

**檔名**：`attendees-{eventId 前8字}-{YYYYMMDD}.csv`

### 2.2 欄位型別驗證（可選）

- single_select / dropdown 目前皆以 `<select>` 渲染，行為一致。
- 若需區分「單選圓鈕」vs「下拉」，可為 single_select 改為 radio group。
- MVP-2.5 Done 條件以「主辦方可匯出 CSV」與「表單支援更多欄位型別」為準；現有型別已足。

---

## 三、檔案變更清單

| 檔案 | 變更 |
|------|------|
| `frontend/src/views/organizer/OrganizerManageView.vue` | 新增匯出 CSV 按鈕與 `exportAttendeesToCsv` |
| `docs/development/develop.md` | MVP-2.5 Done 條件勾選 |

---

## 四、驗收檢查表

- [ ] 主辦方選擇活動、載入名單後，可點「匯出 CSV」
- [ ] 下載的 CSV 含 ticket_id、user_id、status、checked_in_at、ticket_type_id
- [ ] CSV 含 answers 各欄位（如 full_name、phone、ig_account 等）
- [ ] 中文、逗號、換行正確 escape（RFC 4180）
