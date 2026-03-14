1.5.2 視覺與主辦方	活動圖片、主辦方區塊、代寄票券、核銷統計	核銷頁「已入場 N / 未入場 M」統計（資料已有）；主辦方在名單代參加者重寄票券
1.5.3 平台治理	Admin 前端、下架活動、Rate limiting	依你需不需要先營運再決定

---

**待研究**

- **架構與併發**
  - 分散式系統（distributed systems）
  - 系統設計（system design）
  - 高併發處理（搶票、hold 逾時、冪等、鎖與佇列）

- **部署與上雲（個人 side project 最小化）**
  - 前端：Vercel（Vue/Vite 靜態站，Preview 分支）
  - 後端：選一即可 — Railway / Render / Fly.io（容器或直接跑 Flask）
  - DB/Auth：Supabase Cloud 已算上雲，不需自建
  - 網域與 DNS：Namecheap 買網域 + Cloudflare 或 Vercel 綁定

- **DevOps / 運維（簡單版）**
  - CI：GitHub Actions — 跑 pytest、ruff、前端 build，PR 時自動跑
  - 環境變數：各平台後台填（Vercel / Railway 等），勿 commit secrets
  - 日誌：先 stdout → 用平台內建 log 查；要集中再考慮 Logtail / Axiom（可選）

- **監控與儀表板**
  - 可用性：UptimeRobot — 對 API + 前端 URL 做 HTTP 偵測、故障告警
  - 錯誤：Sentry — 前/後端 exception、source map、release 對應
  - 產品分析（可選）：PostHog — 事件、漏斗、Session 錄影
  - 儀表板：個人專案用 UptimeRobot + Sentry 內建頁面即可；要自建再考慮 Grafana

工具細節與對照見 [docs/Tools.md](docs/Tools.md)、[docs/develop.md](docs/develop.md) 推薦套件章節。