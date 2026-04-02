import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { useAuthStore } from "../../stores/auth";

// mock Supabase client
vi.mock("../../api/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      setSession: vi.fn(),
      signOut: vi.fn(),
      signUp: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      updateUser: vi.fn(),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } },
      })),
    },
  },
}));

// mock authLogin from API client
vi.mock("../../api/client", () => ({
  authLogin: vi.fn(),
}));

import { supabase } from "../../api/supabase";
import { authLogin } from "../../api/client";

const mockSession = {
  access_token: "token-abc",
  refresh_token: "refresh-xyz",
  expires_in: 3600,
  token_type: "bearer",
  user: { id: "user-1", email: "test@example.com" },
};

describe("useAuthStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("初始狀態：accessToken 為 null，isAuthenticated 為 false", () => {
    const store = useAuthStore();
    expect(store.accessToken).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it("session 有 access_token → accessToken 正確回傳，isAuthenticated 為 true", async () => {
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });
    const store = useAuthStore();
    await store.refreshSession();
    expect(store.accessToken).toBe("token-abc");
    expect(store.isAuthenticated).toBe(true);
  });

  it("clearSession() → session 與 user 都變 null", async () => {
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });
    const store = useAuthStore();
    await store.refreshSession();
    expect(store.accessToken).toBe("token-abc"); // 確認 session 已設入
    store.clearSession();
    expect(store.accessToken).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it("signOut() 成功 → session 與 user 清空", async () => {
    (supabase.auth.signOut as Mock).mockResolvedValue({ error: null });
    const store = useAuthStore();
    await store.signOut();
    expect(store.accessToken).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it("signOut() Supabase 拋錯 → store re-throw", async () => {
    (supabase.auth.signOut as Mock).mockResolvedValue({ error: new Error("network") });
    const store = useAuthStore();
    await expect(store.signOut()).rejects.toThrow("network");
  });

  it("signIn() 全部 mock 成功 → session 有值", async () => {
    (authLogin as Mock).mockResolvedValue({
      access_token: "token-abc",
      refresh_token: "refresh-xyz",
    });
    (supabase.auth.setSession as Mock).mockResolvedValue({ data: {}, error: null });
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });
    const store = useAuthStore();
    await store.signIn("test@example.com", "password123");
    expect(authLogin).toHaveBeenCalledWith("test@example.com", "password123");
    expect(store.accessToken).toBe("token-abc");
  });

  it("signIn() authLogin mock 拋錯 → store re-throw", async () => {
    (authLogin as Mock).mockRejectedValue(new Error("auth failed"));
    const store = useAuthStore();
    await expect(store.signIn("test@example.com", "wrong")).rejects.toThrow("auth failed");
  });

  it("signUp() 有 session → requiresEmailConfirmation 為 false", async () => {
    (supabase.auth.signUp as Mock).mockResolvedValue({
      data: { session: mockSession, user: mockSession.user },
      error: null,
    });
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });
    const store = useAuthStore();
    const result = await store.signUp("new@example.com", "password123");
    expect(result.requiresEmailConfirmation).toBe(false);
  });

  it("signUp() 無 session → requiresEmailConfirmation 為 true", async () => {
    (supabase.auth.signUp as Mock).mockResolvedValue({
      data: { session: null, user: { id: "user-1" } },
      error: null,
    });
    (supabase.auth.getSession as Mock).mockResolvedValue({
      data: { session: null },
      error: null,
    });
    const store = useAuthStore();
    const result = await store.signUp("new@example.com", "password123");
    expect(result.requiresEmailConfirmation).toBe(true);
  });
});
