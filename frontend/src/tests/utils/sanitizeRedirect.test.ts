import { describe, it, expect } from "vitest";
import { sanitizeRedirect } from "../../utils/sanitizeRedirect";

describe("sanitizeRedirect", () => {
  it("正常相對路徑原樣回傳", () => {
    expect(sanitizeRedirect("/dashboard")).toBe("/dashboard");
  });

  it("根路徑原樣回傳", () => {
    expect(sanitizeRedirect("/")).toBe("/");
  });

  it("含 query string 的相對路徑原樣回傳", () => {
    expect(sanitizeRedirect("/events/123?q=abc")).toBe("/events/123?q=abc");
  });

  it("protocol-relative URL（//evil.com）回傳 /", () => {
    expect(sanitizeRedirect("//evil.com")).toBe("/");
  });

  it("absolute URL（https://evil.com）回傳 /", () => {
    expect(sanitizeRedirect("https://evil.com")).toBe("/");
  });

  it("空字串回傳 /", () => {
    expect(sanitizeRedirect("")).toBe("/");
  });

  it("undefined 回傳 /", () => {
    expect(sanitizeRedirect(undefined)).toBe("/");
  });
});
