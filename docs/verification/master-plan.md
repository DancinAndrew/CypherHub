# MVP-1／MVP-2／MVP-3 主驗證計畫（可重複執行）

> **用途**：供人類或 AI 助理**重複開啟本檔**，依序執行自動化指令與手動勾選項，驗證 MVP-1～3 在**邏輯、程式可重現性、已定義之資安控制**上是否達標。  
> **非目標**：本檔不取代 `develop.md` 規格；**SEC-1～SEC-4 全站資安軌**見同檔「Phase 6」，須與 MVP 驗收**分開簽核**。  
> **狀態欄**：執行時請在 `執行紀錄` 填日期、commit SHA、環境（local Supabase／cloud staging／prod）。

---

## 給 AI 助理的執行協定（每次對話請先讀這段）

1. **讀取順序**：先讀本檔全文 → 再依 **Phase 編號** 由小到大執行；子步驟依 **步驟 ID**（如 `P1-AUTO-01`）。
2. **自動化優先**：每個 Phase 先跑「可自動化」區塊；失敗則**停止並記錄**，不要跳過。
3. **手動項**：標示為 `手動` 的步驟需使用者操作瀏覽器／綠界測試站／ngrok；AI 應產出**勾選表或摘要**供簽核，不可偽造為已通過。
4. **證據**：通過的 Phase 請在 `執行紀錄` 附上：指令、exit code、或「已依哪份子檔勾選」。
5. **外部文件**：細項流程以連結為準；本檔只給**入口與通過定義**。
6. **Supabase 僅 Cloud**：Phase 0 走 **P0-02-CLOUD**，不要求 Docker／`db reset`；若使用者未聲明，可詢問「本地 DB 或僅 Cloud」再選路徑。

**關鍵連結**

| 用途 | 路徑 |
|------|------|
| 規格主檔 | [docs/development/develop.md](../development/develop.md) |
| MVP-1/2/3 實作狀態總覽 | [implementation-status.md](./implementation-status.md) |
| MVP-1 手動驗收 | [mvp1-verification.md](./mvp1-verification.md) |
| MVP-2 驗證（含綠界 E2E） | [mvp2-verification.md](./mvp2-verification.md) |
| MVP-3 測試＋手動 | [mvp3-verification.md](./mvp3-verification.md) |
| 本地／雲端切換 | [docs/setup/local-cloud-switch.md](../setup/local-cloud-switch.md) |
| Migrations 推到雲端 | [scripts/push-to-cloud.sh](../../scripts/push-to-cloud.sh)（內容為 `supabase db push` 等） |

---

## 執行紀錄（每次跑驗證請更新）

> 下表為**某次歷史執行留存**；新跑驗證請覆寫。若只用 Cloud，P0-02 應記 **P0-02a-cloud** 結果，而非僅 `supabase db reset`。

| 欄位 | 內容 |
|------|------|
| 日期 | 2026-03-21 |
| Git commit | `9dd27c4587d0debbec414ce433a5814ddf3f7de0` |
| 環境 | local（Supabase CLI；Docker 未連線） |
| 執行者 | AI 助理 |
| Phase 0～5 結果 | **Phase 0：部分通過**（僅試 P0-02-local；Cloud 路徑未記）；**Phase 1：pytest 通過**；**P1 ruff：當時未通過**（見下表；若已修復請更新） |
| Phase 6（SEC） | 未執行 |
| 已知限制 | 工作區有未提交變更；`.env` 未設 ECPAY_*／CRON_SECRET 等；本地 DB 需 Docker 或改走 **P0-02-CLOUD**；`uv sync` 後跑測需 `uv pip install -r requirements.txt` |

### Phase 0 步驟證據（最近一次）

| 步驟 ID | 結果 | 說明 |
|---------|------|------|
| P0-01a | ⚠️ | `git status`：有修改 docs、刪除／新增若干檔；**建議驗收前 commit 或 stash** |
| P0-01b | ✅ | `git rev-parse HEAD` → 上表 commit |
| P0-02a-cloud | ✅ | cloud staging |
| P0-03a | ✅ | `cd backend && uv sync` → exit 0 |
| P0-04a/b | ✅ | `npm install` + `npm run build`（vue-tsc + vite）→ exit 0 |
| P0-05 | ⚠️ | `.env`：`SUPABASE_*`、`ADMIN_ALLOWLIST` 已設；`ECPAY_*`、`CRON_SECRET`、`ORG_APPROVAL_REQUIRED`、`PLATFORM_FEE_RATE` 為空（MVP-2 E2E／MVP-3 jobs 測前需補）；未驗證前端 `VITE_SUPABASE_*` |

### Phase 1 步驟證據（同一次執行；於 P0-02 失敗後仍跑自動化以取得回歸狀態）

| 步驟 ID | 結果 | 說明 |
|---------|------|------|
| P1-AUTO-01 | ✅ | `uv pip install -r requirements.txt` 後 `uv run python -m pytest -v -m "not integration"` → **89 passed**, 4 deselected, ~4.6s |
| P1-AUTO-05 | ❌→✅? | 當時 **exit 1**；若已 `ruff check .` 全綠請改為 ✅ |

> **備註**：僅執行 `uv sync` 時未安裝 `requirements.txt` 內套件，導致 `uv run pytest` 找不到 pytest；正式 SOP 建議在 Phase 0 加上 `uv pip install -r requirements.txt` 或將依賴納入 `pyproject.toml`。

---

## 範圍與簽核定義

### 納入 MVP-1～3 驗收

- 功能與 DB 行為與 `develop.md`、各階段 checklist **一致**。
- 後端／前端在乾淨環境可依本檔指令**重現**測試與 build。
- **資安（MVP 重疊範圍）**：JWT 僅由後端解析、`user_id` 不信任 client；RLS／API 不允許讀他人訂單／票；綠界 webhook **驗簽＋冪等**；Admin／Cron 等敏感端點有**允許清單或 secret**（依實作）。

### 不納入（除非另開專案）

- **MVP-2.7 PayPal**：規格為可選，未實作不視為 MVP-2 不完整。
- **SEC-1～SEC-4 全站強化**：見 Phase 6；與 MVP 功能驗收**分表**簽核。

---

## Phase 0 — 基線環境（P0）

**通過定義**：同一 commit 下 DB schema、依賴、環境變數**可重現**；無「僅某台電腦能跑」之未紀錄步驟。

**資料庫路徑（擇一即可）**

| 路徑 | 需要 Docker？ | Phase 0 DB 怎麼算「綠」 |
|------|----------------|------------------------|
| **A. 本地 Supabase** | 是（`supabase start` 依賴容器） | 專案根目錄 `supabase db reset` 成功，migrations 含 MVP-2／3 |
| **B. 僅 Cloud** | **否** | 已對目標專案（建議 **staging**）完成 `supabase db push`（或 `./scripts/push-to-cloud.sh`），且 `.env` 指向該專案；schema 與 repo 內 `supabase/migrations` 一致 |

若你**只用 Supabase Cloud、不跑本地 DB**：不必安裝／啟動 Docker 來通過 Phase 0；請走 **路徑 B**，並在執行紀錄註明 `環境：cloud staging`（或專案 ref）。**勿**在正式 production 上試錯 migration；應另有 staging 專案。推送前建議先 **dry-run**：[scripts/push-to-cloud.sh](../../scripts/push-to-cloud.sh) 已內建 `supabase db push --dry-run` 再正式 `db push`。

**Cloud 專案連結**：CLI 需已 `supabase login`，且專案根目錄已 `supabase link --project-ref <你的專案 ref>`（與 Dashboard 的 Project reference 一致）。`push-to-cloud.sh` 內含**預設** `PROJECT_REF`；若你的 staging 不同，請先 `supabase link` 到正確專案，或依團隊慣例修改腳本／改用純 `supabase db push`。

詳見：[local-cloud-switch.md](../setup/local-cloud-switch.md)（雲端：`supabase login` → `./scripts/push-to-cloud.sh`）。

### P0-01 工作目錄與版本

| 步驟 ID | 類型 | 動作 | 預期 |
|---------|------|------|------|
| P0-01a | 自動 | 專案根目錄執行 `git status` | 知悉是否有未提交變更（驗收建議在乾淨 tree） |
| P0-01b | 自動 | `git rev-parse HEAD` | 記入執行紀錄 |

### P0-02 資料庫 migrations（擇一：本地 **或** 雲端）

**P0-02-LOCAL（本地 Supabase）**

| 步驟 ID | 類型 | 動作 | 預期 |
|---------|------|------|------|
| P0-02a-local | 自動 | 依 [local-cloud-switch.md](../setup/local-cloud-switch.md) 啟動本地 Supabase（`supabase start`），專案根目錄執行 `supabase db reset` | 成功結束；含 MVP-2（約 0017～0023）、MVP-3（約 0024～0027） |

**P0-02-CLOUD（僅連雲端，不需 Docker）**

| 步驟 ID | 類型 | 動作 | 預期 |
|---------|------|------|------|
| P0-02a-cloud | 自動／手動 | `supabase login` 後，連結 **staging**（`supabase link`），再執行 `./scripts/push-to-cloud.sh` 或專案根目錄 `supabase db push`（見 [local-cloud-switch.md](../setup/local-cloud-switch.md)） | 成功套用 migrations；執行紀錄註明目標專案 ref（**勿**寫入 service role / key） |
| P0-02b-cloud | 手動（建議） | Dashboard → SQL 或 Table Editor 抽樣確認關鍵表／函式存在（或對 staging 跑 integration 測試） | 與本 repo migration 預期一致 |

**AI 執行注意**：若使用者聲明「只用 Cloud」，**不要**要求啟動 Docker 或 `supabase db reset`；改確認 **P0-02-CLOUD** 已完成或列為待使用者執行。

### P0-03 後端依賴

| 步驟 ID | 類型 | 動作 | 預期 |
|---------|------|------|------|
| P0-03a | 自動 | `cd backend && uv sync`；若要跑 Phase 1 pytest，**另補** `uv pip install -r requirements.txt`（與專案慣例一致） | 無錯誤 |

### P0-04 前端依賴與建置

| 步驟 ID | 類型 | 動作 | 預期 |
|---------|------|------|------|
| P0-04a | 自動 | `cd frontend && npm ci` 或 `npm install` | 無錯誤 |
| P0-04b | 自動 | `npm run build` | 成功 |

### P0-05 環境變數（檢查清單，不寫入密碼）

至少確認**鍵名存在**（值由執行者本地／CI 注入）：

- **後端** `.env`：`SUPABASE_URL`、`SUPABASE_ANON_KEY`、`SUPABASE_SERVICE_ROLE_KEY`
- **後端**：`ADMIN_ALLOWLIST`（Admin／審核／全站訂單等）
- **前端**（若手動／E2E 會開瀏覽器）：`.env`（或 Vite 對應檔）內 `VITE_SUPABASE_URL`、`VITE_SUPABASE_ANON_KEY` 與後端指向**同一** Supabase 專案（見 [local-cloud-switch.md](../setup/local-cloud-switch.md)）
- MVP-2 綠界測試：`ECPAY_MERCHANT_ID`、`ECPAY_HASH_KEY`、`ECPAY_HASH_IV`、`ECPAY_RETURN_URL`、`ECPAY_STAGE`
- MVP-3：`CRON_SECRET`（或專案實際命名）、`ORG_APPROVAL_REQUIRED`、`PLATFORM_FEE_RATE`（依 checklist）

### Phase 0 通過檢核（對照用）

完成下列即視為 Phase 0 **全綠**（DB 為 **P0-02-LOCAL 或 P0-02-CLOUD 擇一**，不可兩邊都略過）：

- [ ] P0-01：已記錄 commit SHA；知悉工作區是否乾淨
- [ ] P0-02：**本地** `db reset` 成功 **或** **Cloud** `link` + `db push`（或 `push-to-cloud.sh`）成功 + 可選 P0-02b-cloud
- [ ] P0-03：`uv sync`（+ 需要時 `uv pip install -r requirements.txt`）
- [ ] P0-04：前端 `npm` + `npm run build` 成功
- [ ] P0-05：後端／前端（若測 UI）Supabase 變數鍵名齊備，且前後端指向同一專案

---

## Phase 1 — 自動化測試與靜態檢查（P1）

**通過定義**：下列指令在 Phase 0 **非 DB 項**（P0-01、P0-03～P0-05）與 **P0-02 擇一路徑**完成後**全數成功**（integration 可獨立矩陣）。僅 Cloud 者無須完成 P0-02-LOCAL。

### P1-AUTO-01 後端單元／整合（不含 integration 標記）

在 `backend` 目錄（若尚未安裝 `requirements.txt`，先執行 `uv pip install -r requirements.txt`）：

```bash
cd backend
uv run python -m pytest -v -m "not integration"
```

**預期**：exit code 0；失敗則記錄檔名與錯誤摘要。

### P1-AUTO-02 MVP-2 核心測試（建議至少包含）

```bash
cd backend
uv run python -m pytest app/tests/test_order_state_machine.py app/tests/test_compensate_paid_orders.py -v -m "not integration"
```

**預期**：全數 passed。

### P1-AUTO-03 MVP-3 測試套件（與狀態報告對齊）

```bash
cd backend
uv run python -m pytest \
  app/tests/test_mvp31_staff_permissions.py \
  app/tests/test_mvp3_staff_permission.py \
  app/tests/test_mvp3_org_approval.py \
  app/tests/test_mvp33_settlements_payouts.py \
  app/tests/test_mvp34_audit_comp_admin_orders.py \
  app/tests/test_audit_service.py \
  app/tests/test_jobs_blueprint.py \
  app/tests/test_event_notification_service.py \
  -v -m "not integration"
```

**預期**：全數 passed（若專案另有合併指令，以 `mvp3-verification-checklist.md` 為準）。

### P1-AUTO-04 Integration（可選矩陣，需真實 Supabase）

```bash
cd backend
# 已設定 SUPABASE_* 時
uv run python -m pytest -m integration -v
```

**預期**：若執行，exit code 0；若環境未備妥，於執行紀錄標示「略過」。

### P1-AUTO-05 後端 linter（若專案有設定）

```bash
cd backend
uv run python -m ruff check .   # 或專案文件規定之指令
```

**預期**：無 error（warning 政策由團隊定義）。

---

## Phase 2 — MVP-1：手動驗收（P2）

**通過定義**：依 [mvp1-verification.md](./mvp1-verification.md) **逐項勾選**完成。

### P2 給 AI 的指令

- 開啟 checklist，依章節 **1.0 → 1.5** 引導使用者操作。
- 重點不得遺漏：**免費報名防超賣**、**QR／核銷**、**主辦方流程**、**Admin**、**Rate limit**（與 [reports/rate-limit-test-report.md](./reports/rate-limit-test-report.md) 行為一致）。

### P2 通過勾選

- [ ] Checklist 全部勾選或同等文件已簽名／日期

---

## Phase 3 — MVP-2：訂單、Hold、綠界、出票、退款（P3）

**通過定義**：  
- 自動化：Phase 1 已含訂單狀態機／補償等測試。  
- **手動**：依 [mvp2-verification.md](./mvp2-verification.md) 完成 **綠界 E2E、Hold 逾時、補償**（現況見 [implementation-status.md](./implementation-status.md)）。

### P3 子項核銷表

| 子項 | 驗證來源 | 通過 |
|------|----------|------|
| DB 表與 RLS | mvp2-verification-plan「DB 與模型」 | [ ] |
| Hold／逾時釋放 | 同檔 Hold 區 + `release-expired-holds` 等 | [ ] |
| 綠界結帳→Webhook→驗簽→冪等→出票 | 同檔 2.2（需 ngrok 與測試卡） | [ ] |
| 訂單狀態機 | 單測 + 手動抽樣 | [ ] |
| 退款 | 單測 + 手動或 staging | [ ] |
| 表單擴充／CSV | develop.md 對照 + UI | [ ] |

---

## Phase 4 — MVP-3：RBAC、審核、結算、Audit、Jobs（P4）

**通過定義**：  
- 自動化：Phase 1 MVP-3 測試通過。  
- 手動：依 [mvp3-verification.md](./mvp3-verification.md) 第二節起之 **手動驗證**。

### P4 子項核銷表

| 子項 | 通過 |
|------|------|
| MVP-3.1 staff／owner／admin 邊界 | [ ] |
| MVP-3.2 入駐審核 | [ ] |
| MVP-3.3 結算／提款／平台費 | [ ] |
| MVP-3.4 Audit／Admin 訂單／Comp 票 | [ ] |
| MVP-3.5 sort=hot、reminders、異動通知 | [ ] |

---

## Phase 5 — 跨階段加強（併發／越權／Webhook 濫測）（P5）

**通過定義**：抽樣結果符合預期；發現問題須開 issue 並**不通過**整體驗收。

建議至少執行：

| 步驟 ID | 類型 | 說明 | 通過 |
|---------|------|------|------|
| P5-01 | 手動／工具 | **併發**：最後名額同時報名或 Hold，僅一方成功，DB 無超賣、無負值 | [ ] |
| P5-02 | 手動 | **IDOR**：使用者 B 的 token 存取使用者 A 的 order／ticket 相關 API → 應 403/404 | [ ] |
| P5-03 | 手動／腳本 | **Webhook**：錯簽名、竄改金額、重放 → 不得錯誤出票或重複出票 | [ ] |

---

## Phase 6 — SEC-1～SEC-4（與 MVP 分開簽核）（P6）

**通過定義**：依 `develop.md`「階段一覽」中 SEC 項目逐項檢查；**未實作項目不得勾完成**。

參考：[develop.md 階段一覽（SEC）](../development/develop.md)

| 項目 | 說明 | 通過 |
|------|------|------|
| SEC-1 | HTTPS、CORS、安全標頭（staging/prod） | [ ] |
| SEC-2 | 身份與敏感資料保護 | [ ] |
| SEC-3 | 注入、XSS、CSRF 模型、Rate limit 覆蓋檢視 | [ ] |
| SEC-4 | Secrets、日誌、部署檢查 | [ ] |

---

## 簽核包（驗收交付物）

完成 Phase 0～5 後，建議存檔：

1. 本檔的 **執行紀錄**（含 commit、環境）。
2. Phase 1 指令之 **完整終端輸出** 或 CI artifact。
3. MVP-1/2/3 **checklist 勾選版**（或截圖／影片連結）。
4. **已知限制**（例：僅 local 綠界、未跑 cloud integration）。

---

## 文件版本

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0 | 2025-03-20 | 初版：主驗證計畫，供重複執行與 AI 依序驗證 |
