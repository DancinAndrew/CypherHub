import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";
import { useErrorStore } from "./stores/error";
import { pinia } from "./stores/index";
import "./style.css";

const app = createApp(App);

app.use(pinia);
app.use(router);

const errorStore = useErrorStore(pinia);

app.config.errorHandler = (err: unknown) => {
  errorStore.setError(err);
};

function handleGlobalError(err: unknown): void {
  errorStore.setError(err);
}

window.onerror = (_message, _source, _lineno, _colno, err) => {
  handleGlobalError(err ?? new Error("Unknown error"));
  return true; // prevent default browser error handling
};

window.onunhandledrejection = (event: PromiseRejectionEvent) => {
  handleGlobalError(event.reason);
  event.preventDefault();
};

const authStore = useAuthStore(pinia);
authStore.bindAuthListener();
authStore.refreshSession().catch(() => {
  // non-fatal: auth state will be updated on first navigation
});

try {
  app.mount("#app");
} catch (err) {
  handleGlobalError(err);
  document.getElementById("app")!.innerHTML = `
    <div class="flex min-h-screen items-center justify-center bg-gray-950 p-6">
      <div class="max-w-lg rounded-xl border border-rose-500/50 bg-rose-950/80 p-6 text-rose-200">
        <p class="font-semibold text-rose-300">應用程式載入失敗</p>
        <p class="mt-2 text-sm">${(err instanceof Error ? err.message : String(err)).replace(/</g, "&lt;")}</p>
        <a href="/" class="mt-4 inline-block rounded bg-rose-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-400">返回首頁</a>
      </div>
    </div>
  `;
}
