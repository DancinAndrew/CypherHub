# CypherHub UI/UX 優化方案（基於設計原則研究）

> 參考：WCAG、POUR、視覺階層、Fitts's Law、Hick's Law、認知負載

---

## 一、設計原則研究總結

### A. 無障礙（Accessibility）- POUR + WCAG

| 原則 | 說明 | 實作重點 |
|------|------|----------|
| **Perceivable 可感知** | 內容可見、可理解 | 對比 4.5:1、alt 文字、語義化 |
| **Operable 可操作** | 鍵盤導覽、輔助科技 | focus 狀態、點擊區域 |
| **Understandable 可理解** | 清晰、可預測 | 一致用語、明確錯誤訊息 |
| **Robust 穩健** | 與輔助科技相容 | 語義 HTML、ARIA |

**WCAG 對比要求：**
- 一般文字：≥ 4.5:1（AA）
- 大文字（≥18px 或 14px 粗體）：≥ 3:1
- 純黑 #000 on 白 #FFF = 21:1
- 避免：slate-100/200/300 等淺色文字在淺底上

### B. 視覺階層（Visual Hierarchy）

| 層級 | 用途 | 建議 |
|------|------|------|
| **Primary** | H1 主標 | 大、粗、留白多 |
| **Secondary** | H2/H3 區塊 | 中尺寸、適度粗 |
| **Body** | 內文、說明 | 清晰可讀、行高 1.5 |
| **Muted** | 輔助資訊 | 灰階、較小，但 ≥ 4.5:1 對比 |

**Type scale**：使用數學比例（1.25、1.5）維持階層一致。

### C. UI/UX 核心原則

| 原則 | 說明 | 實作 |
|------|------|------|
| **Clarity & Simplicity** | 介面簡潔、目的明確 | 減少冗餘、白空間 |
| **Consistency** | 視覺與操作一致 | 統一按鈕、間距、術語 |
| **User Control** | 可撤銷、可導航 | 返回鍵、確認對話框 |
| **Feedback** | 操作有回應 | loading、success、error 狀態 |
| **Accessibility-First** | 無障礙優先 | 對比、鍵盤、語義 |
| **Minimalism** | 精簡 | 有限色彩、字體、導航 |

### D. 認知心理學

| 法則 | 說明 | 應用 |
|------|------|------|
| **Hick's Law** | 選項越多，決策越慢 | 收合篩選、分類、分步 |
| **Fitts's Law** | 目標越大越近，點擊越快 | 主 CTA 大、位置明顯 |
| **Cognitive Load** | 認知負載有限 | 分步表單、漸進揭露 |

---

## 二、現況問題對照

| 問題 | 違反原則 | 修正方向 |
|------|----------|----------|
| 步驟 2/3 標題看不清 | WCAG 對比 | text-gray-900 |
| slate-100/200/300 在淺底 | Perceivable | 改用 gray-800/700/600 |
| brand-300 用於主內容 | 對比不足 | 改 brand-700 |
| 表單 label 過淡 | Perceivable | 至少 gray-700 |
| 主 CTA 可能不夠大 | Fitts's Law | 加大、sticky |
| 篩選一次全開 | Hick's Law | 已收合 ✓ |
| 步驟編號圓圈對比不足 | 對比 | text-brand-700 |

---

## 三、優化執行項目

### Phase 1：對比修正（已完成）
- [x] 步驟 2/3 標題 text-gray-900
- [x] 所有 slate-100/200/300 → gray-900/800/600
- [x] 步驟圓圈數字 text-brand-700
- [x] MyTicketsView、OrganizerManageView 標題
- [x] OrganizerApplyView 成功訊息、連結

### Phase 2：視覺階層與間距（已完成）
- [x] H1/H2/H3 比例：tailwind display-xl/lg/md
- [x] section 間距：mb-6 ~ mb-12 依區塊
- [x] 表單 label：font-medium text-gray-700

### Phase 3：可訪問性（已完成）
- [x] 主 CTA min-height 44px（btn-primary、btn-secondary）
- [x] focus-visible:ring-2 outline-brand-500
- [x] 錯誤/成功訊息 role="alert"
- [x] Skip link「跳至主內容」、main#main-content

### Phase 4：一致性（已完成）
- [x] 統一「返回」連結 .link-back
- [x] card 內 padding p-6
- [x] 按鈕禁用態 disabled:opacity-50

---

## 四、Tailwind 對比參考

| 用途 | 安全組合（淺底） | 避免 |
|------|------------------|------|
| 主標題 | text-gray-900 | text-slate-100/200 |
| 副標題 | text-gray-800 | text-slate-300 |
| 內文 | text-gray-700 | text-slate-400（小字時） |
| 輔助 | text-gray-600 | text-slate-500（需確認對比） |
| 品牌強調 | text-brand-700 | text-brand-300/400 |
| 連結 | text-brand-600 hover:text-brand-700 | text-brand-300 |
