type ApiErrorPayload = {
  code?: string;
  message?: string;
  details?: unknown;
};

function extractApiErrorPayload(error: unknown): ApiErrorPayload | null {
  const maybeResponse = (error as { response?: { data?: { error?: ApiErrorPayload } } })?.response;
  return maybeResponse?.data?.error ?? null;
}

export function toApiErrorMessage(error: unknown, fallback: string): string {
  const apiError = extractApiErrorPayload(error);
  if (apiError?.message) {
    const raw = String(
      ((apiError.details as { raw?: unknown } | undefined)?.raw ?? apiError.details ?? ""),
    ).toUpperCase();

    if (apiError.code === "RPC_PERMISSION_DENIED" || raw.includes("PERMISSION DENIED FOR FUNCTION")) {
      return "目前登入身分沒有執行報名 RPC 的權限，請先重新登入後再試。";
    }
    if (apiError.code === "RPC_NOT_FOUND" || raw.includes("COULD NOT FIND THE FUNCTION")) {
      return "後端 RPC 函式不存在或版本不一致，請確認 cloud migration 已完整套用。";
    }
    if (apiError.code === "DB_PATCH_REQUIRED" || raw.includes("FUNCTION GEN_RANDOM_BYTES") && raw.includes("DOES NOT EXIST")) {
      return "資料庫缺少 register_free 必要 patch（0005）。請先執行 `supabase db push` 後再報名。";
    }
    if (raw.includes("PER_USER_LIMIT_EXCEEDED")) {
      return "已達每人限購數量，無法重複報名此票種。";
    }
    if (raw.includes("SOLD_OUT")) {
      return "票券已售完。";
    }
    if (raw.includes("SALE_NOT_STARTED")) {
      return "票券尚未開賣。";
    }
    if (raw.includes("SALE_ENDED")) {
      return "票券販售已結束。";
    }
    if (raw.includes("EVENT_NOT_PUBLISHED")) {
      return "活動尚未發布，暫時不可報名。";
    }
    if (raw.includes("TICKET_TYPE_INACTIVE")) {
      return "票種目前未開放。";
    }

    if (apiError.code === "VALIDATION_ERROR" && Array.isArray(apiError.details)) {
      const first = apiError.details[0] as { loc?: unknown; msg?: string } | undefined;
      if (first) {
        const location = Array.isArray(first.loc) ? first.loc.join(".") : String(first.loc ?? "field");
        return `${apiError.message}: ${location} ${first.msg ?? ""}`.trim();
      }
    }
    if (apiError.code === "VALIDATION_ERROR" && apiError.details && typeof apiError.details === "object") {
      const field = (apiError.details as { field?: unknown }).field;
      if (field) {
        return `${apiError.message}: ${String(field)}`;
      }
    }
    return apiError.code ? `${apiError.message} (${apiError.code})` : apiError.message;
  }

  const message = (error as { message?: string })?.message;
  return message || fallback;
}

export function toAuthErrorMessage(error: unknown, mode: "signin" | "signup" | "forgot"): string {
  const rawMessage = ((error as { message?: string })?.message || "").toLowerCase();
  const code = ((error as { code?: string })?.code || "").toLowerCase();

  if (rawMessage.includes("email rate limit") || code.includes("over_email_send_rate_limit")) {
    return "註冊信寄送過於頻繁，請稍後再試（Supabase rate limit）。";
  }
  if (rawMessage.includes("invalid login credentials")) {
    return "登入失敗：帳號或密碼不正確。";
  }
  if (rawMessage.includes("email not confirmed")) {
    return "此帳號尚未完成信箱驗證，請先到信箱點擊確認連結。";
  }
  if (rawMessage.includes("user already registered")) {
    return "此 Email 已註冊，請直接 Sign In。";
  }
  if (rawMessage.includes("email address") && rawMessage.includes("invalid")) {
    return "Email 格式不正確，請輸入有效信箱（例如 name@example.com）。";
  }
  if (rawMessage.includes("password should be at least")) {
    return "密碼長度不足，至少需要 6 個字元。";
  }

  if (mode === "signup") {
    return (error as { message?: string })?.message || "註冊失敗，請確認輸入內容後重試。";
  }
  if (mode === "forgot") {
    return (error as { message?: string })?.message || "無法寄送重設密碼信，請確認 Email 是否已註冊。";
  }
  return (error as { message?: string })?.message || "登入失敗，請稍後重試。";
}
