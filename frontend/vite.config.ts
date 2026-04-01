import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// SEC-1: 生產建置時檢查 API URL 是否使用 HTTPS
if (process.env.NODE_ENV === "production") {
  const apiUrl = process.env.VITE_API_BASE_URL || "";
  if (apiUrl && !apiUrl.startsWith("https://")) {
    console.warn(
      "⚠️  SEC-1: VITE_API_BASE_URL should use HTTPS in production:",
      apiUrl,
    );
  }
}

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
  },
});
