# 錯誤邊界實作 — 驗證報告

> 依據 note.md：前端 global error boundary，避免白屏；可搭配未來 Sentry

---

## 一、計畫摘要

| 階段 | 內容 |
|------|------|
| 1. 計畫 | `docs/development/plans/error-boundary-plan.md` |
| 2. 實作 | error store、main.ts global handlers、App.vue 整合、pre-mount fallback |
| 3. 驗證 | 手動測試 + build 通過 |

---

## 二、修改檔案清單

| 檔案 | 變更 |
|------|------|
| `frontend/src/stores/error.ts` | **新建** — Pinia store：`globalError`、`setError`、`clearError`，預留 Sentry 註解 |
| `frontend/src/main.ts` | `app.config.errorHandler`、`window.onerror`、`window.onunhandledrejection`；`app.mount()` try/catch + fallback HTML |
| `frontend/src/App.vue` | 改為使用 error store、`onErrorCaptured` 寫入 store、單一錯誤 UI |
| `frontend/src/router/index.ts` | 新增 dev-only 路由 `/__test-error`（用於驗證） |
| `frontend/src/views/ErrorBoundaryTestView.vue` | **新建** — 故意拋錯的測試組件（僅 dev 存在） |
| `docs/development/plans/error-boundary-plan.md` | **新建** — 實作計畫 |

---

## 三、錯誤捕獲層級

| 層級 | 處理器 | 覆蓋範圍 |
|------|--------|----------|
| Vue | `app.config.errorHandler` | render / watcher / 生命週期錯誤 |
| 組件 | `onErrorCaptured`（App.vue） | 子組件錯誤，寫入 store |
| JS sync | `window.onerror` | 未捕獲的同步錯誤 |
| JS async | `window.onunhandledrejection` | 未處理的 Promise rejection |
| 掛載失敗 | `main.ts` try/catch | `app.mount()` 拋錯時注入 fallback UI |

---

## 四、驗證步驟

### 1. Vue 組件錯誤

```bash
cd frontend && npm run dev
```

瀏覽器開啟 `http://localhost:5173/__test-error`（僅 dev 模式存在）

**預期**：顯示「頁面載入錯誤」卡片，錯誤訊息為「ErrorBoundary 測試：故意拋錯」，可點「返回首頁」恢復。

### 2. 未處理 Promise rejection

在瀏覽器 Console 執行：

```js
Promise.reject(new Error('Test unhandled rejection'));
```

**預期**：顯示錯誤 overlay，訊息為「Test unhandled rejection」。

### 3. 同步錯誤（可選）

```js
setTimeout(() => { throw new Error('Test sync error'); }, 0);
```

**預期**：顯示錯誤 overlay。

### 4. 掛載失敗（可選，破壞性測試）

在 `main.ts` 中暫時把 `app.mount("#app")` 改為 `throw new Error("mount failed")`：

- **預期**：頁面顯示「應用程式載入失敗」fallback UI，帶「返回首頁」連結。

### 5. Build 驗證

```bash
cd frontend && npm run build
```

**預期**：`vue-tsc --noEmit && vite build` 成功，`/__test-error` 不會出現在 production build。

---

## 五、Sentry 整合預留

在 `stores/error.ts` 的 `setError` 內已預留：

```ts
// TODO: when Sentry is added:
// if (typeof Sentry !== 'undefined') Sentry.captureException(this.globalError);
```

日後加入 Sentry 時，在此處補上即可集中上報所有已捕獲錯誤。

---

## 六、結論

- ✅ Vue 組件錯誤 → 顯示 overlay，不白屏  
- ✅ 未處理 Promise rejection → 顯示 overlay  
- ✅ 同步錯誤 → 顯示 overlay  
- ✅ 掛載失敗 → fallback UI 取代白屏  
- ✅ Sentry 整合點已預留  
- ✅ production build 不含測試路由  

---

狀態：已完成
