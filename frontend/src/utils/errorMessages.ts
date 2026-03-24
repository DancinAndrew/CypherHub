type ApiErrorPayload = {
  code?: string;
  message?: string;
  details?: unknown;
};

function extractApiErrorPayload(error: unknown): ApiErrorPayload | null {
  const maybeResponse = (error as { response?: { data?: { error?: ApiErrorPayload } } })?.response;
  return maybeResponse?.data?.error ?? null;
}

/** 後端 error code → 使用者友善中文訊息 */
const ERROR_CODE_MAP: Record<string, string> = {
  // 認證
  AUTH_FAILED: "登入失敗：帳號或密碼不正確。",
  AUTH_REQUIRED: "請先登入後再操作。",
  AUTH_INVALID: "登入已過期，請重新登入。",
  FORBIDDEN: "您沒有權限執行此操作。",

  // 角色權限
  STAFF_CANNOT_MANAGE: "工作人員身分僅能核銷與查看名單，無法建立或編輯活動。",
  ORG_NOT_APPROVED: "組織尚未通過審核，無法執行此操作。",
  ORGANIZER_PERMISSION_CHECK_FAILED: "權限檢查失敗，請確認您有此組織的管理權限。",

  // 活動
  EVENT_NOT_FOUND: "找不到此活動。",
  EVENT_NOT_PUBLISHED: "活動尚未發布，暫時不可報名。",
  CREATE_EVENT_FAILED: "建立活動失敗，請稍後再試。",
  UPDATE_EVENT_FAILED: "更新活動失敗，請稍後再試。",

  // 票種
  TICKET_TYPE_NOT_FOUND: "找不到此票種。",
  TICKET_TYPE_INACTIVE: "票種目前未開放。",
  TICKET_TYPE_EVENT_MISMATCH: "票種不屬於此活動。",
  SOLD_OUT: "票券已售完。",
  SALE_NOT_STARTED: "票券尚未開賣。",
  SALE_ENDED: "票券販售已結束。",
  PER_USER_LIMIT_EXCEEDED: "已達每人限購數量，無法重複報名此票種。",
  CAPACITY_EXCEEDED: "票券容量已滿。",
  CREATE_TICKET_TYPE_FAILED: "建立票種失敗，請稍後再試。",
  UPDATE_TICKET_TYPE_FAILED: "更新票種失敗，請稍後再試。",
  DELETE_TICKET_TYPE_FAILED: "刪除票種失敗，請稍後再試。",

  // 票券
  TICKET_NOT_FOUND: "找不到此票券。",
  LIST_TICKETS_FAILED: "載入票券列表失敗，請稍後再試。",
  CANCEL_TICKET_FAILED: "取消票券失敗，請稍後再試。",
  RESEND_TICKET_FAILED: "重寄票券信件失敗，請稍後再試。",

  // 報名
  REGISTER_FAILED: "報名失敗，請稍後再試。",
  ATTENDEE_NO_EMAIL: "此參加者無 email，無法寄送票券。",

  // 訂單
  ORDER_NOT_FOUND: "找不到此訂單。",
  ORDERS_LIST_FAILED: "載入訂單列表失敗，請稍後再試。",
  ORDER_FETCH_FAILED: "載入訂單詳情失敗，請稍後再試。",
  HOLD_ORDER_CREATE_FAILED: "建立訂單失敗，請稍後再試。",
  CANCEL_ORDER_FAILED: "取消訂單失敗，請稍後再試。",
  ORDER_CANNOT_REFUND: "此訂單無法退款。",
  INVALID_ORDER_STATUS_TRANSITION: "訂單狀態轉換不合法。",

  // 金流
  PAYMENT_NOT_FOUND: "找不到付款紀錄。",
  PAYMENT_NOT_COMPLETED: "付款尚未完成。",
  ECPAY_CONFIG_MISSING: "金流設定遺失，請聯絡客服。",
  REFUND_NOT_SUPPORTED: "此付款方式不支援退款。",
  REFUND_CREATE_FAILED: "退款處理失敗，請稍後再試。",
  REFUND_API_FAILED: "金流退款 API 呼叫失敗，請稍後再試。",

  // 結算與提領
  SETTLEMENTS_LIST_FAILED: "載入結算列表失敗，請稍後再試。",
  SETTLEMENT_NOT_FOUND: "找不到此結算紀錄。",
  SETTLEMENT_FETCH_FAILED: "載入結算詳情失敗，請稍後再試。",
  INSUFFICIENT_BALANCE: "可用餘額不足，無法提領此金額。",
  PAYOUT_CREATE_FAILED: "提領申請失敗，請稍後再試。",
  PAYOUT_ALREADY_PROCESSED: "此提領申請已處理完畢。",
  PAYOUT_NOT_FOUND: "找不到此提領申請。",

  // 核銷
  CHECKIN_VERIFY_FAILED: "核銷驗證失敗，請重新掃描。",
  CHECKIN_COMMIT_FAILED: "核銷確認失敗，請重新操作。",
  QR_MISMATCH: "QR 碼資訊不符，請確認票券正確性。",

  // 組織
  ORGANIZATION_NOT_FOUND: "找不到此組織。",
  ORGANIZER_APPLY_FAILED: "主辦方申請失敗，請稍後再試。",
  MEMBER_NOT_FOUND: "找不到此成員。",

  // 表單
  FORM_SCHEMA_INVALID: "表單欄位設定格式不正確。",
  FORM_UPSERT_FAILED: "儲存表單失敗，請稍後再試。",

  // RPC / DB
  RPC_PERMISSION_DENIED: "目前登入身分沒有執行此操作的權限，請重新登入後再試。",
  RPC_NOT_FOUND: "後端 RPC 函式不存在或版本不一致，請確認 migration 已完整套用。",
  DB_PATCH_REQUIRED: "資料庫缺少必要 patch，請先執行 supabase db push。",

  // 通用
  RATE_LIMIT_EXCEEDED: "操作過於頻繁，請稍後再試。",
  NOT_FOUND: "找不到此資源。",
  METHOD_NOT_ALLOWED: "不支援此請求方法。",
};

export function toApiErrorMessage(error: unknown, fallback: string): string {
  const status = (error as { response?: { status?: number } })?.response?.status;
  if (status === 429) {
    return "操作過於頻繁，請稍後再試。";
  }
  const apiError = extractApiErrorPayload(error);

  // 直接匹配 error code
  if (apiError?.code && ERROR_CODE_MAP[apiError.code]) {
    return ERROR_CODE_MAP[apiError.code];
  }

  if (apiError?.message) {
    const raw = String(
      ((apiError.details as { raw?: unknown } | undefined)?.raw ?? apiError.details ?? ""),
    ).toUpperCase();

    if (raw.includes("PERMISSION DENIED FOR FUNCTION")) {
      return ERROR_CODE_MAP.RPC_PERMISSION_DENIED;
    }
    if (raw.includes("COULD NOT FIND THE FUNCTION")) {
      return ERROR_CODE_MAP.RPC_NOT_FOUND;
    }
    if (raw.includes("FUNCTION GEN_RANDOM_BYTES") && raw.includes("DOES NOT EXIST")) {
      return ERROR_CODE_MAP.DB_PATCH_REQUIRED;
    }

    // raw message 中的 known code 匹配
    for (const code of ["PER_USER_LIMIT_EXCEEDED", "SOLD_OUT", "SALE_NOT_STARTED", "SALE_ENDED", "EVENT_NOT_PUBLISHED", "TICKET_TYPE_INACTIVE"] as const) {
      if (raw.includes(code) && ERROR_CODE_MAP[code]) {
        return ERROR_CODE_MAP[code];
      }
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
  const status = (error as { response?: { status?: number } })?.response?.status;
  if (status === 429) return "操作過於頻繁，請稍後再試。";
  const apiError = extractApiErrorPayload(error);
  if (apiError?.code === "AUTH_FAILED") return "登入失敗：帳號或密碼不正確。";
  if (mode === "signin" && status === 401) return "登入失敗：帳號或密碼不正確。";

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
