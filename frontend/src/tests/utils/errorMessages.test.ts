import { describe, it, expect } from "vitest";
import { toApiErrorMessage, toAuthErrorMessage } from "../../utils/errorMessages";

// ─── helper：建構 axios-like error ──────────────────────────────────────────
function makeApiError(status: number, code: string, message: string, details?: unknown) {
  return {
    response: {
      status,
      data: { error: { code, message, details } },
    },
  };
}

function makeStatusError(status: number) {
  return { response: { status } };
}

// ─── toApiErrorMessage ───────────────────────────────────────────────────────
describe("toApiErrorMessage", () => {
  it("HTTP 429 → rate limit 訊息（不管 body）", () => {
    const msg = toApiErrorMessage(makeStatusError(429), "fallback");
    expect(msg).toBe("操作過於頻繁，請稍後再試。");
  });

  it("已知 code SOLD_OUT → 對應中文", () => {
    const err = makeApiError(400, "SOLD_OUT", "sold out");
    expect(toApiErrorMessage(err, "fallback")).toBe("票券已售完。");
  });

  it("已知 code EVENT_NOT_FOUND → 對應中文", () => {
    const err = makeApiError(404, "EVENT_NOT_FOUND", "not found");
    expect(toApiErrorMessage(err, "fallback")).toBe("找不到此活動。");
  });

  it("已知 code FORBIDDEN → 對應中文", () => {
    const err = makeApiError(403, "FORBIDDEN", "forbidden");
    expect(toApiErrorMessage(err, "fallback")).toBe("您沒有權限執行此操作。");
  });

  it("未知 code，有 message → <message> (<CODE>)", () => {
    const err = makeApiError(400, "SOME_UNKNOWN", "未知錯誤");
    expect(toApiErrorMessage(err, "fallback")).toBe("未知錯誤 (SOME_UNKNOWN)");
  });

  it("raw details 含 PERMISSION DENIED FOR FUNCTION → RPC 權限訊息", () => {
    const err = makeApiError(400, "DB_ERROR", "db error", { raw: "permission denied for function foo" });
    expect(toApiErrorMessage(err, "fallback")).toBe(
      "目前登入身分沒有執行此操作的權限，請重新登入後再試。",
    );
  });

  it("raw details 含 COULD NOT FIND THE FUNCTION → RPC 不存在訊息", () => {
    const err = makeApiError(400, "DB_ERROR", "db error", { raw: "could not find the function bar" });
    expect(toApiErrorMessage(err, "fallback")).toBe(
      "後端 RPC 函式不存在或版本不一致，請確認 migration 已完整套用。",
    );
  });

  it("raw details 字串含 SOLD_OUT → 票券已售完", () => {
    const err = makeApiError(400, "RPC_ERROR", "rpc failed", { raw: "SOLD_OUT: capacity exhausted" });
    expect(toApiErrorMessage(err, "fallback")).toBe("票券已售完。");
  });

  it("VALIDATION_ERROR + array details → 欄位名稱 + msg", () => {
    const err = makeApiError(422, "VALIDATION_ERROR", "驗證失敗", [
      { loc: ["body", "email"], msg: "field required" },
    ]);
    expect(toApiErrorMessage(err, "fallback")).toBe("驗證失敗: body.email field required");
  });

  it("VALIDATION_ERROR + object details with field → 欄位訊息", () => {
    const err = makeApiError(422, "VALIDATION_ERROR", "驗證失敗", { field: "ticket_type_id" });
    expect(toApiErrorMessage(err, "fallback")).toBe("驗證失敗: ticket_type_id");
  });

  it("有 message 但 code 為空 → 直接回傳 message", () => {
    const err = { response: { status: 500, data: { error: { code: "", message: "server exploded" } } } };
    expect(toApiErrorMessage(err, "fallback")).toBe("server exploded");
  });

  it("完全無 response，有 error.message → 回傳 error.message", () => {
    expect(toApiErrorMessage(new Error("network error"), "fallback")).toBe("network error");
  });

  it("完全無 response 且無 message → 回傳 fallback", () => {
    expect(toApiErrorMessage({}, "fallback")).toBe("fallback");
  });

  it("error 為 null → 回傳 fallback", () => {
    expect(toApiErrorMessage(null, "fallback")).toBe("fallback");
  });
});

// ─── toAuthErrorMessage ──────────────────────────────────────────────────────
describe("toAuthErrorMessage", () => {
  it("HTTP 429 → rate limit 訊息", () => {
    expect(toAuthErrorMessage(makeStatusError(429), "signin")).toBe(
      "操作過於頻繁，請稍後再試。",
    );
  });

  it("code AUTH_FAILED → 帳密錯誤訊息", () => {
    const err = makeApiError(401, "AUTH_FAILED", "auth failed");
    expect(toAuthErrorMessage(err, "signin")).toBe("登入失敗：帳號或密碼不正確。");
  });

  it("signin + HTTP 401（無 code）→ 帳密錯誤訊息", () => {
    expect(toAuthErrorMessage(makeStatusError(401), "signin")).toBe(
      "登入失敗：帳號或密碼不正確。",
    );
  });

  it("raw message invalid login credentials → 帳密錯誤訊息", () => {
    expect(toAuthErrorMessage({ message: "Invalid login credentials" }, "signin")).toBe(
      "登入失敗：帳號或密碼不正確。",
    );
  });

  it("raw message email not confirmed → 未驗證信箱訊息", () => {
    expect(toAuthErrorMessage({ message: "Email not confirmed" }, "signin")).toBe(
      "此帳號尚未完成信箱驗證，請先到信箱點擊確認連結。",
    );
  });

  it("raw message user already registered → 已註冊訊息", () => {
    expect(toAuthErrorMessage({ message: "User already registered" }, "signup")).toBe(
      "此 Email 已註冊，請直接 Sign In。",
    );
  });

  it("raw message password should be at least → 密碼太短", () => {
    expect(toAuthErrorMessage({ message: "Password should be at least 6 characters." }, "signup")).toBe(
      "密碼長度不足，至少需要 6 個字元。",
    );
  });

  it("無匹配，mode forgot → 預設重設密碼失敗訊息", () => {
    expect(toAuthErrorMessage({}, "forgot")).toBe(
      "無法寄送重設密碼信，請確認 Email 是否已註冊。",
    );
  });
});
