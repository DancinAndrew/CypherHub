# CypherHub V2 — 街舞氛圍大改版

> 目標：一眼就愛上、想立刻報名、地下街舞／Cypher 圈氛圍

---

## 一、設計理念

- **氛圍**：地下 battle、club、街角 cypher — 深色、霓虹、高能
- **情緒**：想報名、想參加、想站進圈裡
- **視覺**：大膽、動態、有節奏感

---

## 二、視覺系統

### 色彩
| 用途 | 色碼 | 說明 |
|------|------|------|
| 背景深 | `#0a0a0f` | 主背景 |
| 背景淺 | `#16161d` | 卡片、區塊 |
| 主 accent | `#A855F7` violet-500 | 主 CTA、強調 |
| 次 accent | `#EC4899` pink-500 | 霓虹粉、hover |
| 第三 accent | `#22D3EE` cyan-400 | 螢光青、tag |
| 文字主 | `#fafafa` | 標題 |
| 文字次 | `#a1a1aa` zinc-400 | 內文、輔助 |

### 字體
- **Display**：Bebas Neue — 大標、數字、街頭感
- **Body**：DM Sans — 可讀、現代

### 動畫
- 首屏 Hero：gradient 流動、打字機效果（可選）
- 卡片：hover 上浮 + scale、stagger 進入
- 按鈕：glow、pulse on hover
- Scroll reveal：Intersection Observer 觸發 fade-up
- 背景：subtle gradient 流動、或 noise texture

### 組件風格
- 按鈕：圓角大、glow、hover 放大
- 卡片：深底、細 border (zinc-700)、hover 發光
- Input：深底、發光 focus
- Badge：霓虹色、粗邊

---

## 三、頁面規劃

### HomeView
- **Hero**：全屏 gradient + 大標「CYPHER」或「街舞，在這發生」+ 副標 + 搜尋 bar 發光
- **Marquee**：可選 — 舞風名稱橫向滾動
- **活動卡**：深卡、圖上、hover 上浮+glow、日期 badge 霓虹、stagger 動畫
- **空狀態**：插畫或動畫 placeholder

### EventDetailView
- **Hero 圖**：全寬、gradient overlay 底部、標題疊圖
- **兩欄**：左內容、右 sticky CTA 卡片（發光邊框）
- **區塊**：深卡、細分

### 導覽
- 深色透明、backdrop-blur、logo 霓虹 hover
- 登入按鈕：主色 glow

### Login / 表單
- 全屏深色、置中 card 發光邊框
- Input focus 時邊框發光
- 主按鈕 glow

---

## 四、實作清單（已完成）

- [x] tailwind.config.js — cypher 色板、font-street、shadow-glow、animation
- [x] index.html — Bebas Neue
- [x] style.css — card、btn-primary、btn-secondary、input-field、badge
- [x] App.vue — 深色 nav、font-street logo
- [x] HomeView — Hero 漸層、大標、搜尋、篩選、活動卡
- [x] EventDetailView — 深色版、sticky CTA
- [x] Login / Reset / Profile / MyTickets / Admin
- [x] DynamicForm、Organizer views
