# CypherHub 設計參考文件

> 彙整：V2 深色改版、UI 改善方案、UX 無障礙優化。**全部已實作完成。**

---

## 一、V2 深色改版（街舞氛圍）

### 設計理念

- **氛圍**：地下 battle、club、街角 cypher — 深色、霓虹、高能
- **情緒**：想報名、想參加、想站進圈裡
- **視覺**：大膽、動態、有節奏感

### 色彩系統

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

### 動畫與組件

- Hero：gradient 流動、打字機效果
- 卡片：hover 上浮 + scale、stagger 進入
- 按鈕：glow、pulse on hover
- Scroll reveal：Intersection Observer fade-up
- 組件風格：深底、細 border (zinc-700)、hover 發光、霓虹 badge

### 頁面實作（全部完成）

- [x] tailwind.config.js — cypher 色板、shadow-glow、animation
- [x] HomeView — Hero 漸層、大標、搜尋、篩選、活動卡
- [x] EventDetailView — 深色版、sticky CTA
- [x] Login / Reset / Profile / MyTickets / Admin
- [x] DynamicForm、Organizer views

---

## 二、UI 改善方案（參考 Luma / Eventbrite / Accupass）

### 參考平台共通最佳實踐

1. **Above the fold**：活動名、日期、地點、CTA 不滾動就看見
2. **CTA 重複**：導覽列 sticky、內文分段後再放 CTA
3. **圖片優先**：活動卡以圖為主，資訊附屬
4. **可掃描**：清晰層級、足夠留白、區塊分明
5. **Mobile first**：60%+ 流量來自手機

### 已實作改善

| 頁面 | 改善項目 |
|------|----------|
| HomeView | Hero 區 + 搜尋 bar、篩選收合、活動卡含圖片區 + 日期 badge |
| EventDetailView | 兩欄佈局、sticky 右側 CTA 卡片、明確 section 分區 |
| 導覽 | 深色透明 + backdrop-blur、主色 CTA 按鈕 |
| 表單 | 全屏深色置中 card、focus 發光邊框 |

---

## 三、UX 無障礙優化（WCAG + 認知心理學）

### 設計原則

| 原則 | 說明 |
|------|------|
| WCAG 對比 | 一般文字 ≥ 4.5:1（AA）、大文字 ≥ 3:1 |
| Fitts's Law | 主 CTA 大且位置明顯 |
| Hick's Law | 收合篩選、分類、分步表單 |
| 認知負載 | 漸進揭露、分步操作 |

### Tailwind 對比安全組合（淺底）

| 用途 | 安全組合 | 避免 |
|------|----------|------|
| 主標題 | text-gray-900 | text-slate-100/200 |
| 副標題 | text-gray-800 | text-slate-300 |
| 內文 | text-gray-700 | text-slate-400 |
| 品牌強調 | text-brand-700 | text-brand-300/400 |

### 已完成優化

- [x] Phase 1：對比修正（步驟標題、slate→gray、品牌色）
- [x] Phase 2：視覺階層與間距（H1/H2/H3 比例、section 間距）
- [x] Phase 3：可訪問性（CTA min-height 44px、focus-visible、role="alert"、skip link）
- [x] Phase 4：一致性（返回連結、card padding、disabled 態）
