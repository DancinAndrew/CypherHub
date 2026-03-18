import { defineStore } from "pinia";

export const useErrorStore = defineStore("error", {
  state: () => ({ globalError: null as Error | null }),
  actions: {
    setError(err: unknown): void {
      this.globalError = err instanceof Error ? err : new Error(String(err));
      // TODO: when Sentry is added:
      // if (typeof Sentry !== 'undefined') Sentry.captureException(this.globalError);
    },
    clearError(): void {
      this.globalError = null;
    },
  },
});
