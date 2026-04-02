# Frontend: Vue 3 & TypeScript Standards

## 1. Vue 3 Composition API & 語法糖
- **`<script setup>`**：統一使用 `<script setup lang="ts">` 進行組件開發，提供更好的類型推斷與更簡潔的代碼。
- **響應式變數**：
  - 基本類型使用 `ref()`。
  - 複雜對象或需保持引用的狀態使用 `reactive()` (但須注意解構會失去響應性)。
- **生命週期與 Watchers**：避免濫用 `watch`，優先考慮是否能用 `computed` 解決。當使用 `watch` 時，務必清理相關的副作用。

## 2. 狀態管理 (Pinia)
- **模組化 Store**：依據業務領域劃分 Store (如 `useAuthStore`, `useEventStore`)。
- **避免外部修改**：僅在 Store 的 `actions` 中修改狀態，組件不應直接變更 Store 的 State。
- **Setup Syntax**：Pinia Store 應使用 Setup 語法 (返回 ref 與 function)，與組件風格保持一致。

## 3. TypeScript 嚴格模式
- **Interface & Type**：所有 API 響應、組件 Props、Emits 都必須定義明確的 Type 或 Interface。
- **避免 `any`**：嚴禁使用 `any`。遇到複雜類型應使用 `unknown` 並進行類型斷言或類型收窄 (Type Narrowing)。
- **Props & Emits 類型化**：使用 `defineProps<{ ... }>()` 與 `defineEmits<{ ... }>()`。

## 4. 組件設計 (Component Design)
- **Smart vs Dumb Components**：
  - 容器組件 (Smart)：負責與 API 溝通、讀寫 Store、處理複雜邏輯。
  - 展示組件 (Dumb)：僅依賴 Props 進行渲染，並透過 Emits 通知父組件，具備高可重用性。
- **單一文件大小**：Vue 組件行數不宜過長 (建議 < 300 行)。過長應拆分為子組件或抽取邏輯至 Composables (`useXxx.ts`)。

## 5. 樣式與 TailwindCSS
- **Utility-First**：優先使用 Tailwind 類名。避免編寫自定義 CSS，除非是複雜的動畫或特定覆蓋。
- **組件化樣式**：重複使用的樣式應抽取為 Vue 組件，而非使用 `@apply` 提取到全局 CSS，以保持 Tailwind 的效能優勢。
- **無障礙 (a11y)**：確保適當的顏色對比度、支援鍵盤導航 (focus states)、並為圖片與圖標提供 aria 標籤。

## 6. 效能優化 (Vite)
- **路由懶加載 (Lazy Loading)**：Vue Router 中的路由元件應使用動態導入 `() => import(...)`。
- **資源優化**：圖片應壓縮並使用 WebP 格式。利用 Vite 的 Chunk 策略拆分 vendor 庫。