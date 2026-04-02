import { defineStore } from "pinia";
import { ref } from "vue";

export const useErrorStore = defineStore("error", () => {
  const globalError = ref<Error | null>(null);

  function setError(err: unknown): void {
    globalError.value = err instanceof Error ? err : new Error(String(err));
    // TODO: when Sentry is added:
    // if (typeof Sentry !== 'undefined') Sentry.captureException(globalError.value);
  }

  function clearError(): void {
    globalError.value = null;
  }

  return {
    globalError,
    setError,
    clearError,
  };
});
