# 本地 / 雲端 Supabase 切換指南

專案支援 **本地 Supabase**（開發測試）與 **雲端 Supabase**（正式/部署）兩種模式，透過 `.env` 切換。

---

## 工作流程

| 情境 | 使用 | 切換方式 |
|------|------|----------|
| 日常開發、測試 | 本地 Supabase | `./scripts/use-local-supabase.sh` |
| 部署、正式環境、雲端專案 | 雲端 Supabase | `./scripts/use-cloud-supabase.sh` |

---

## 使用本地 Supabase（開發測試）

1. **切換到本地模式**：
   ```bash
   ./scripts/use-local-supabase.sh
   ```

2. **取得 keys**（若 .env 中 keys 為空）：
   ```bash
   supabase start          # 若尚未啟動
   ./scripts/setup-local-supabase.sh
   ```

3. **套用 migrations**：
   ```bash
   supabase db reset
   ```

4. **啟動專案**：
   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

---

## 使用雲端 Supabase（正式/部署）

1. **喚醒 paused 專案**（若曾被暫停）：
   - 到 [Supabase Dashboard](https://supabase.com/dashboard)
   - 選擇專案 → 點 Resume / 恢復

2. **切換到雲端模式**：
   ```bash
   ./scripts/use-cloud-supabase.sh
   ```

3. **編輯 `.env`，填入雲端專案的值**：
   - `backend/.env`：SUPABASE_URL、SUPABASE_ANON_KEY、SUPABASE_SERVICE_ROLE_KEY
   - `frontend/.env`：VITE_SUPABASE_URL、VITE_SUPABASE_ANON_KEY
   - 取得位置：Dashboard → Project Settings → API

4. **套用 migrations 到雲端**：
   ```bash
   supabase login
   supabase link --project-ref YOUR_PROJECT_REF
   supabase db push
   ```

5. **啟動專案**（連到雲端）：
   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

---

## 注意事項

- **同時只用一種**：同一時間只會連到「本地」或「雲端」，不會混用。
- **Migrations 需分別套用**：本地用 `supabase db reset`，雲端用 `supabase db push`。
- **雲端若被 pause**：需先到 Dashboard 恢復專案，才能正常連線。
