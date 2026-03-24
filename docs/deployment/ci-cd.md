# CI/CD Pipeline

> 本文件說明 CypherHub 的 GitHub Actions CI/CD workflow：觸發條件、各 Job 內容、Branch 策略、Secrets 設定、手動部署與 Rollback 流程。
> 對應檔案：`.github/workflows/ci.yml`。

---

## 一、總覽

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions — CI Workflow                               │
│                                                             │
│  Trigger: push / PR → main, develop                        │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │  backend (parallel)  │  │  frontend (parallel) │          │
│  │  ├─ Checkout         │  │  ├─ Checkout          │          │
│  │  ├─ Python 3.12      │  │  ├─ Node 20           │          │
│  │  ├─ pip install      │  │  ├─ npm ci            │          │
│  │  ├─ ruff check       │  │  └─ npm run build     │          │
│  │  └─ pytest (unit)    │  │    (TypeScript +      │          │
│  └─────────────────────┘  │     Vite bundle)      │          │
│                            └─────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

| 項目 | 值 |
|------|-----|
| Workflow 檔案 | `.github/workflows/ci.yml` |
| 觸發事件 | `push`、`pull_request` |
| 觸發分支 | `main`、`develop` |
| Jobs 數量 | 2（`backend`、`frontend`，並行執行） |
| 自動部署 | 無（目前僅 CI，部署為手動） |

---

## 二、觸發條件

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

| 情境 | 是否觸發 |
|------|----------|
| Push 到 `main` | ✅ |
| Push 到 `develop` | ✅ |
| PR 目標為 `main` | ✅ |
| PR 目標為 `develop` | ✅ |
| Push 到 `feature/*` 分支 | ❌（除非有 PR 指向 main/develop） |
| 手動觸發 | ❌（未設定 `workflow_dispatch`） |

---

## 三、Job 詳解

### 3.1 `backend` Job

```yaml
backend:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - uses: actions/setup-python@v6
      with:
        python-version: "3.12"
        cache: "pip"
        cache-dependency-path: "backend/requirements.txt"
    - run: pip install -r backend/requirements.txt
    - run: cd backend && ruff check .
    - run: cd backend && pytest -q -m "not integration"
```

| Step | 說明 | 預期結果 |
|------|------|----------|
| `actions/checkout@v6` | 簽出程式碼 | — |
| `actions/setup-python@v6` | 安裝 Python 3.12，啟用 pip 快取 | 加速後續 `pip install` |
| `pip install` | 安裝 `backend/requirements.txt` 中所有依賴 | Flask、Supabase SDK、Pydantic、Ruff、Pytest 等 |
| `ruff check .` | Lint 檢查（規則見 `pyproject.toml`：E/F/I/UP/B） | 無 lint error |
| `pytest -q -m "not integration"` | 執行 unit tests（排除需 Supabase 連線的 integration tests） | 所有 unit tests 通過 |

**重點**：

- `cache: "pip"` + `cache-dependency-path`：CI 會快取 pip 套件，`requirements.txt` 不變時跳過下載
- `-m "not integration"`：標記為 `@pytest.mark.integration` 的測試會被排除（這些測試需要實際 Supabase 環境）
- 不需設定環境變數：unit tests 使用 `monkeypatch` mock Supabase 呼叫

### 3.2 `frontend` Job

```yaml
frontend:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - uses: actions/setup-node@v6
      with:
        node-version: "20"
        cache: "npm"
        cache-dependency-path: frontend/package-lock.json
    - run: cd frontend && npm ci
    - run: cd frontend && npm run build
```

| Step | 說明 | 預期結果 |
|------|------|----------|
| `actions/checkout@v6` | 簽出程式碼 | — |
| `actions/setup-node@v6` | 安裝 Node 20，啟用 npm 快取 | 加速 `npm ci` |
| `npm ci` | 乾淨安裝（依 `package-lock.json`，比 `npm install` 更嚴格） | 所有依賴安裝成功 |
| `npm run build` | 執行 `vue-tsc --noEmit && vite build` | TypeScript 型別檢查 + Vite 產生 bundle |

**重點**：

- `npm run build` 包含 TypeScript 編譯檢查（`vue-tsc --noEmit`），因此任何 type error 都會導致 CI 失敗
- `cache: "npm"` + `cache-dependency-path`：快取 `~/.npm`，`package-lock.json` 不變時跳過下載
- 不需環境變數：build 時 `VITE_*` 變數未設定，Vite 會使用程式碼中的 fallback 值

### 3.3 並行執行

`backend` 和 `frontend` 兩個 Job **無依賴關係**，GitHub Actions 會同時啟動兩個 runner 並行執行，加速 CI 流程。

```
              ┌─ backend  ─ ~60s ─ ✅/❌
Trigger ──┤
              └─ frontend ─ ~45s ─ ✅/❌
```

---

## 四、Branch 策略

### 4.1 目前策略

```
main ← 正式分支（production-ready）
  ↑
develop ← 開發整合分支
  ↑
feature/* ← 功能分支
```

| 分支 | 用途 | CI 觸發 | 部署 |
|------|------|---------|------|
| `main` | 正式版本 | Push + PR | 手動部署至 Production |
| `develop` | 開發整合 | Push + PR | 手動部署至 Staging（若有） |
| `feature/*` | 功能開發 | 僅 PR 觸發（目標為 main/develop） | 無 |

### 4.2 建議 PR 流程

```
1. 從 develop 建立 feature branch
   git checkout develop && git checkout -b feature/my-feature

2. 開發完成後發 PR → develop
   gh pr create --base develop

3. CI 通過 + Code Review → Merge

4. develop 穩定後發 PR → main
   gh pr create --base main --head develop

5. 合併至 main 後手動部署
```

---

## 五、Secrets 與環境變數

### 5.1 CI 需要的 Secrets

**目前不需要任何 Secrets**。原因：

- Backend unit tests 使用 `monkeypatch` mock，不需實際 Supabase 連線
- Frontend build 不需 `VITE_*` 變數（程式碼中有 fallback）
- CI 不執行部署

### 5.2 未來擴充（若加入 CD）

若需在 CI 中加入自動部署，需設定以下 GitHub Secrets：

| Secret | 用途 | 設定位置 |
|--------|------|----------|
| `GCP_SA_KEY` | Google Cloud Run 部署用的 Service Account JSON | Repo → Settings → Secrets |
| `VERCEL_TOKEN` | Vercel CLI 部署（若不用 Git 整合） | Repo → Settings → Secrets |
| `SUPABASE_ACCESS_TOKEN` | `supabase db push`（若需 CI 中推 migration） | Repo → Settings → Secrets |
| `SUPABASE_PROJECT_REF` | Supabase 專案 ID | Repo → Settings → Variables |

設定方式：GitHub → Repo → Settings → Secrets and variables → Actions → New repository secret

---

## 六、手動部署流程

目前 CI 僅負責測試，部署為手動操作。詳見 [deploy-guide.md](deploy-guide.md)。

### 6.1 Backend 部署

```bash
# 確認 CI 通過後
cd backend

# Google Cloud Run
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/cypherhub-backend
gcloud run deploy cypherhub-backend \
  --image gcr.io/YOUR_PROJECT_ID/cypherhub-backend \
  --region asia-east1

# 或 Fly.io
fly deploy
```

### 6.2 Frontend 部署

Vercel 預設在 push 到 `main` 時自動部署（透過 Git 整合，非 GitHub Actions）。

手動部署：

```bash
cd frontend
npx vercel --prod
```

### 6.3 Database Migration

```bash
supabase link --project-ref YOUR_REF
supabase db push --dry-run    # 預覽
supabase db push              # 正式推送
```

> ⚠️ 部署順序：**先推 migration → 再部署 Backend → 最後 Frontend**。

---

## 七、擴充：加入 CD（自動部署）

### 7.1 自動部署至 Cloud Run（範例）

```yaml
# .github/workflows/ci.yml — 在 jobs 下新增
  deploy-backend:
    needs: backend              # 等 backend job 通過
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - uses: google-github-actions/setup-gcloud@v2

      - run: |
          gcloud builds submit \
            --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/cypherhub-backend \
            backend/

      - run: |
          gcloud run deploy cypherhub-backend \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/cypherhub-backend \
            --region asia-east1 \
            --platform managed
```

### 7.2 自動推送 Migration（範例）

```yaml
  deploy-db:
    needs: backend
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - uses: supabase/setup-cli@v1
        with:
          version: latest

      - run: |
          supabase link --project-ref ${{ secrets.SUPABASE_PROJECT_REF }}
          supabase db push
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
```

### 7.3 加入 `workflow_dispatch` 手動觸發

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:          # 允許從 GitHub UI 手動觸發
    inputs:
      deploy:
        description: "Deploy after CI passes"
        type: boolean
        default: false
```

---

## 八、Rollback 流程

### 8.1 Backend Rollback

**Cloud Run**：

```bash
# 查看歷史版本
gcloud run revisions list --service cypherhub-backend

# 回退至指定版本（100% 流量切換）
gcloud run services update-traffic cypherhub-backend \
  --to-revisions REVISION_NAME=100
```

**Fly.io**：

```bash
fly releases
fly deploy --image registry.fly.io/cypherhub-backend:v<N>
```

### 8.2 Frontend Rollback

Vercel Dashboard → Deployments → 選擇先前版本 → **Promote to Production**。

或 CLI：

```bash
vercel rollback
```

### 8.3 Database Rollback

Supabase **不支援**自動 migration rollback。處理方式：

1. **非破壞性變更**（新增表/欄位）：無需 rollback，舊 code 不受影響
2. **破壞性變更**（修改欄位型別、刪除表）：需撰寫反向 migration SQL
3. **嚴重錯誤**：使用 Supabase Dashboard → Database → Backups → Point-in-Time Recovery

> 最佳實踐：破壞性 DB 變更應分階段進行 — 先部署相容新 code → 再執行 migration → 最後清理舊 code。

---

## 九、CI 失敗排查

### 9.1 Backend 常見失敗

| 錯誤 | 原因 | 修復 |
|------|------|------|
| `ruff check` 失敗 | Lint 不通過 | `cd backend && ruff check . --fix` 自動修復 |
| `ruff format` 差異 | 格式不一致 | `cd backend && ruff format .` |
| `pytest` 失敗 | Unit test 未通過 | 本地執行 `pytest -q -m "not integration"` 定位問題 |
| `ModuleNotFoundError` | 新依賴未加入 `requirements.txt` | 補上後 commit |

### 9.2 Frontend 常見失敗

| 錯誤 | 原因 | 修復 |
|------|------|------|
| `vue-tsc` 型別錯誤 | TypeScript type error | 本地 `npm run build` 定位，修復型別 |
| `npm ci` 失敗 | `package-lock.json` 與 `package.json` 不同步 | `npm install` 重新產生 lock file |
| Vite build 失敗 | Import 路徑錯誤、缺少模組 | 檢查 import 語句 |

### 9.3 本地重現 CI

```bash
# 模擬 backend CI
cd backend
pip install -r requirements.txt
ruff check .
pytest -q -m "not integration"

# 模擬 frontend CI
cd frontend
npm ci
npm run build
```

---

## 十、CI 效能

### 10.1 目前耗時

| Job | 預估耗時 | 瓶頸 |
|-----|----------|------|
| `backend` | ~60s | `pip install`（首次）/ `pytest`（後續） |
| `frontend` | ~45s | `npm ci`（首次）/ `npm run build`（後續） |
| **總計** | ~60s（並行） | 取兩者較慢者 |

### 10.2 快取效果

| 快取 | 機制 | 節省時間 |
|------|------|----------|
| pip packages | `cache: "pip"` + `cache-dependency-path` | ~15-20s |
| npm packages | `cache: "npm"` + `cache-dependency-path` | ~10-15s |

快取 key 由 dependency file hash 決定：`requirements.txt` 或 `package-lock.json` 變更時自動失效。

---

## 十一、未來改善方向

| 項目 | 說明 | 優先度 |
|------|------|--------|
| 加入 CD | push to main 自動部署（Cloud Run + Vercel） | 高 |
| Integration tests | 在 CI 中啟動 Supabase Container 執行整合測試 | 中 |
| `workflow_dispatch` | 允許手動觸發 CI + 部署 | 中 |
| PR status check | 設定 branch protection rule，CI 不通過禁止合併 | 高 |
| 安全掃描 | `npm audit` / `pip-audit` / Dependabot | 中 |
| Build cache | Vite build cache、Docker layer cache | 低 |
| E2E tests | Playwright / Cypress 前端 E2E（需 staging 環境） | 低 |
