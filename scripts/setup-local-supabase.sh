#!/usr/bin/env bash
# 本地 Supabase 設定腳本
# 執行後會：1) 啟動 Supabase 2) 取得 keys 3) 寫入 backend/.env 與 frontend/.env

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

echo "==> 更新 backend/.env ..."
# Backend 在 Docker 內需用 host.docker.internal
BACKEND_URL="http://host.docker.internal:54321"
if [[ -f backend/.env ]]; then
  # 保留既有設定，只更新 Supabase 相關
  sed -i.bak "s|^SUPABASE_URL=.*|SUPABASE_URL=$BACKEND_URL|" backend/.env
  sed -i.bak "s|^SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$ANON_KEY|" backend/.env
  sed -i.bak "s|^SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY|" backend/.env
  rm -f backend/.env.bak
else
  cat > backend/.env << EOF
APP_ENV=development
FLASK_DEBUG=1
SUPABASE_URL=$BACKEND_URL
SUPABASE_ANON_KEY=$ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY
CORS_ORIGINS=http://localhost:5173
ADMIN_ALLOWLIST=
EOF
fi
cp backend/.env backend/.env.local
echo "  已同步 backend/.env → backend/.env.local"

echo "==> 更新 frontend/.env ..."
FRONTEND_URL="${API_URL:-http://127.0.0.1:54321}"
if [[ -f frontend/.env ]]; then
  sed -i.bak "s|^VITE_SUPABASE_URL=.*|VITE_SUPABASE_URL=$FRONTEND_URL|" frontend/.env
  sed -i.bak "s|^VITE_SUPABASE_ANON_KEY=.*|VITE_SUPABASE_ANON_KEY=$ANON_KEY|" frontend/.env
  rm -f frontend/.env.bak
else
  cat > frontend/.env << EOF
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=$FRONTEND_URL
VITE_SUPABASE_ANON_KEY=$ANON_KEY
EOF
fi
cp frontend/.env frontend/.env.local
echo "  已同步 frontend/.env → frontend/.env.local"

echo ""
echo "==> 完成！下一步："
echo "  1. 套用 migrations: supabase db reset"
echo "  2. 啟動專案: docker compose -f infra/docker-compose.yml up --build"
echo ""
echo "  Supabase Studio: http://127.0.0.1:54323"
echo "  API: $FRONTEND_URL"
