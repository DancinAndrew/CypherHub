# 錯誤邊界實作計畫

## 目標

依 `note.md` 優先級建議：實現前端 global error boundary，避免白屏；可搭配未來 Sentry。

## 現狀

- `App.vue` 已使用 `onErrorCaptured` 捕獲子組件錯誤，並顯示「頁面載入錯誤」UI
- **缺口**：以下錯誤無法被捕捉，會導致白屏或未處理的錯誤
  1. `app.config.errorHandler` 未設定 — Vue 內部傳播出的錯誤
  2. `window.onerror` 未設定 — 全域未捕獲的 JS 錯誤
  3. `window.onunhandledrejection` 未設定 — 未處理的 Promise rejection
  4. `main.ts` 中 `app.mount()` 失敗 — 無 fallback UI

## 實作策略

| 層級 | 處理器 | 行為 |
|------|--------|------|
| Vue | `app.config.errorHandler` | 捕獲 render/component 錯誤，寫入 error store |
| JS | `window.onerror` | 捕獲未處理的 sync 錯誤，寫入 error store |
| JS | `window.onunhandledrejection` | 捕獲未處理的 Promise rejection，寫入 error store |
| 掛載 | `main.ts` try/catch | `app.mount()` 失敗時，注入最小 fallback UI 到 `#app` |
| UI | App.vue + error store | 顯示 global error  overlay，提供「返回首頁」恢復 |
| 未來 | Sentry 整合點 | 在各 handler 內預留 `Sentry.captureException(err)` 呼叫點 |

## 檔案變更

1. **`frontend/src/stores/error.ts`**（新建）— error store：`globalError`、`setError`、`clearError`
2. **`frontend/src/main.ts`** — 註冊 global handlers、mount try/catch
3. **`frontend/src/App.vue`** — 改為讀取 error store，與 `onErrorCaptured` 共用同一 UI

## Sentry 整合預留

在 `setError` 或各 handler 內加入註解：

```ts
// TODO: when Sentry is added:
// if (typeof Sentry !== 'undefined') Sentry.captureException(err);
```

---

狀態：已完成，見 `docs/verification/reports/error-boundary-report.md`
