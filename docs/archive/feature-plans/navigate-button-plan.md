# 導航按鈕（零成本）計畫

> 依據 note.md：活動頁若已有 map_url 或 lat/lng，加「導航」按鈕開 Google Maps；為 note 待辦鋪路。**已實作完成**。驗證見 [navigate-button-report.md](../../verification/reports/navigate-button-report.md)。

---

## 一、現況

- `EventDetailView.vue` 地點區塊已有「開啟地圖 →」連結，`v-if="detail.event.map_url"`
- `EventItem` 型別有 `map_url`，**無** `latitude` / `longitude`
- note 待辦：`https://www.google.com/maps/dir/?api=1&destination={lat},{lng}`

---

## 二、零成本策略

1. **map_url**：已有欄位，直接使用
2. **lat/lng**：目前 API 無此欄位，預留擴展（computed 優先判斷 lat/lng，有則組 Google Maps 導航 URL）
3. **UI**：將「開啟地圖」改為「導航」按鈕，樣式與「分享活動」類似

---

## 三、導航 URL 邏輯

| 條件 | URL |
|------|-----|
| 有 latitude 且 longitude | `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}` |
| 有 map_url | 使用 map_url（通常為 Google Maps 連結） |
| 皆無 | 不顯示按鈕 |

---

## 四、實作範圍

- 檔案：`frontend/src/views/EventDetailView.vue`
- 變更：新增 computed `navigateUrl`；將地點區塊內連結改為按鈕「導航」，樣式比照 btn-secondary

---

## 五、實作結果（已完成）

- `navigateUrl`：優先 lat/lng → Google Maps 導航 URL；否則 map_url
- 按鈕：「🧭 導航」，邊框按鈕樣式
- Build 通過
