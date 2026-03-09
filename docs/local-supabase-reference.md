# 本地 Supabase 連線參考

本地執行 `supabase start` 後的服務端點（每次啟動相同）。

## 開發工具

| 服務   | URL                    | 說明           |
|--------|------------------------|----------------|
| Studio | http://127.0.0.1:54323 | 後台管理、建立用戶 |
| Mailpit| http://127.0.0.1:54324 | 測試 Email 收信 |
| MCP    | http://127.0.0.1:54321/mcp | MCP 端點     |

## API

| 類型         | URL                                  |
|--------------|--------------------------------------|
| Project URL  | http://127.0.0.1:54321               |
| REST         | http://127.0.0.1:54321/rest/v1       |
| GraphQL      | http://127.0.0.1:54321/graphql/v1    |
| Edge Functions | http://127.0.0.1:54321/functions/v1 |

## Database

```
postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

## Authentication Keys

- **Publishable**：前端與 backend 的 `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY`
- **Secret**：僅 backend 的 `SUPABASE_SERVICE_ROLE_KEY`，禁止放前端

取得方式：執行 `supabase status`，或 `supabase status -o env` 取得完整 env 格式。

## Storage (S3)

- URL: http://127.0.0.1:54321/storage/v1/s3
- Region: `local`
- Access Key / Secret Key：由 `supabase status` 輸出
