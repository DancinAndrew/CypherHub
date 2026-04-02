import { describe, it, expect } from "vitest";
import { useErrorStore } from "../../stores/error";

describe("useErrorStore", () => {
  it("初始狀態 globalError 為 null", () => {
    const store = useErrorStore();
    expect(store.globalError).toBeNull();
  });

  it("setError(Error) → globalError 是 Error 實例且 message 正確", () => {
    const store = useErrorStore();
    store.setError(new Error("oops"));
    expect(store.globalError).toBeInstanceOf(Error);
    expect(store.globalError?.message).toBe("oops");
  });

  it("setError(string) → 包成 Error 實例", () => {
    const store = useErrorStore();
    store.setError("string error");
    expect(store.globalError).toBeInstanceOf(Error);
    expect(store.globalError?.message).toBe("string error");
  });

  it("clearError() → globalError 變 null", () => {
    const store = useErrorStore();
    store.setError(new Error("some error"));
    store.clearError();
    expect(store.globalError).toBeNull();
  });
});
