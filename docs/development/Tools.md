# CypherHub 工具選單

| 工具 | 用途 |
|------|------|
| **Vercel** | 前端/全端部署：靜態站、Serverless Functions、Preview 分支、CDN。適合 Vue/Vite 或 Next.js 專案部署。 |
| **Namecheap** | 網域註冊與管理：購買、轉入、續約、WHOIS、DNS 設定。 |
| **Stripe** | 金流：信用卡、Apple Pay、訂閱、webhook、退 refund。MVP-2 付費票可優先整合。 |
| **UptimeRobot** | 監控：HTTP/ping 偵測、故障告警（Email/Slack）、uptime 報表。監控 API 與前端可用性。 |
| **Clerk** | 身份驗證（Auth）：登入/註冊、OAuth、2FA、session 管理。可與 Supabase Auth 並用或替代。 |
| **Cloudflare** | DNS + CDN：解析網域、快取、DDoS 防護、SSL、防火牆規則。 |
| **Sentry** | 錯誤追蹤：前端/後端 exception 收集、source map 對應、release 追蹤、告警通知。 |
| **Resend** | 交易型郵件：報名確認、重寄票券、驗證信、通知。API 簡潔，適合 MVP-1 email 串接。 |
| **PostHog** | 產品分析：事件追蹤、漏斗、Session 錄影、Feature flags、A/B 測試。開源、可自架。 |
| **Pinecone / FAISS** | 向量資料庫：Embedding 搜尋、相似推薦。適合做「相關活動推薦」「搜尋優化」等進階功能。 |

---

## 與 CypherHub 現況對照

| 工具 | MVP-1 | MVP-2+ |
|------|-------|--------|
| Supabase | ✓ Auth + DB + Storage | ✓ |
| Resend | 可串接（取代 email stub） | ✓ |
| Stripe | - | 付費票 |
| Sentry | 可選（上線前建議） | ✓ |
| Vercel | 可部署 frontend | ✓ |
| Cloudflare | 可做 DNS/CDN | ✓ |
