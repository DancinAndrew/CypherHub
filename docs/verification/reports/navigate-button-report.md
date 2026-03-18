# 導航按鈕（零成本）驗證報告

> 依據 note.md：活動頁若已有 map_url 或 lat/lng，加「導航」按鈕開 Google Maps；為 note 待辦鋪路

---

## 一、實作摘要

| 檔案 | 變更 |
|------|------|
| `frontend/src/api/client.ts` | EventItem 新增 `latitude?`, `longitude?`（預留） |
| `frontend/src/views/EventDetailView.vue` | 新增 computed `navigateUrl`；「開啟地圖」→「導航」按鈕 |
| `docs/development/plans/navigate-button-plan.md` | 計畫文件 |

---

## 二、導航 URL 邏輯

| 條件 | 結果 |
|------|------|
| `latitude`、`longitude` 皆為有效數字 | `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}` |
| 有 `map_url`（無 lat/lng） | 使用 `map_url` |
| 皆無 | 不顯示按鈕 |

---

## 三、UI 變更

- **原本**：文字連結「開啟地圖 →」
- **改為**：按鈕樣式「🧭 導航」，`btn-secondary` 風格，hover 有 accent 邊框

---

## 四、擴展性（為 note 待辦鋪路）

- 若後端日後回傳 `latitude`、`longitude`，前端無需改動即可改為使用 Google Maps 導航 URL
- EventItem 型別已預留 `latitude?: number | null`、`longitude?: number | null`

---

## 五、驗證

```bash
cd frontend && npm run build
# ✓ built successfully
```

**手動驗證**：進入有 `map_url` 的活動詳情頁 → 地點區塊應顯示「導航」按鈕 → 點擊在新分頁開啟地圖。
