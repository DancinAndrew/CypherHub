#!/usr/bin/env bash
# 本地 Supabase 設定腳本
# 執行後會：1) 啟動 Supabase 2) 取得 keys 3) 寫入根目錄的 .env

set -e
cd "$(dirname "$0")/.."

echo "==> 檢查 Supabase 狀態..."
if ! supabase status -o env &>/dev/null; then
  echo "==> 啟動 Supabase（首次約 1–2 分鐘）..."
  supabase start
fi

echo "==> 取得 Supabase 連線資訊..."
STATUS=$(supabase status -o env)

# 解析 ANON_KEY, SERVICE_ROLE_KEY, API_URL
ANON_KEY=$(echo "$STATUS" | grep '^ANON_KEY=' | cut -d'=' -f2- | tr -d '"')
SERVICE_ROLE_KEY=$(echo "$STATUS" | grep '^SERVICE_ROLE_KEY=' | cut -d'=' -f2- | tr -d '"')
API_URL=$(echo "$STATUS" | grep '^API_URL=' | cut -d'=' -f2- | tr -d '"')

if [[ -z "$ANON_KEY" ]]; then
  echo "錯誤：無法取得 ANON_KEY，請手動執行 supabase status 檢查"
  exit 1
fi

echo "==> 更新 .env ..."
BACKEND_URL="http://host.docker.internal:54321"
FRONTEND_URL="${API_URL:-http://127.0.0.1:54321}"

if [[ -f .env ]]; then
  # 如果系統是 macOS，sed -i 需要空字串備份後綴，但 GNU sed 不需要
  # 為了相容，使用臨時檔案
  tmp_env=$(mktemp)
  sed -e "s|^SUPABASE_URL=.*|SUPABASE_URL=$BACKEND_URL|" \
      -e "s|^SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$ANON_KEY|" \
      -e "s|^SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY|" \
      -e "s|^VITE_SUPABASE_URL=.*|VITE_SUPABASE_URL=$FRONTEND_URL|" \
      -e "s|^VITE_SUPABASE_ANON_KEY=.*|VITE_SUPABASE_ANON_KEY=$ANON_KEY|" .env > "$tmp_env"
  mv "$tmp_env" .env
else
  cp .env.example .env
  tmp_env=$(mktemp)
  sed -e "s|^SUPABASE_URL=.*|SUPABASE_URL=$BACKEND_URL|" \
      -e "s|^SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$ANON_KEY|" \
      -e "s|^SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY|" \
      -e "s|^VITE_SUPABASE_URL=.*|VITE_SUPABASE_URL=$FRONTEND_URL|" \
      -e "s|^VITE_SUPABASE_ANON_KEY=.*|VITE_SUPABASE_ANON_KEY=$ANON_KEY|" .env > "$tmp_env"
  mv "$tmp_env" .env
fi

cp .env .env.local
echo "  已同步 .env → .env.local"

echo ""
echo "==> 完成！下一步："
echo "  1. 套用 migrations: supabase db reset"
echo "  2. 啟動專案: docker compose -f infra/docker-compose.yml up --build"
echo ""
echo "  Supabase Studio: http://127.0.0.1:54323"
echo "  API: $FRONTEND_URL"
