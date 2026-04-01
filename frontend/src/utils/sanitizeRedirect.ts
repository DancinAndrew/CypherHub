/**
 * SEC-2: 驗證 redirect 參數，防止 open redirect 攻擊。
 * 僅允許以 "/" 開頭的相對路徑，拒絕絕對 URL 和 protocol-relative URL。
 */
export function sanitizeRedirect(value: unknown): string {
  if (typeof value !== "string" || !value) return "/";
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  return "/";
}
