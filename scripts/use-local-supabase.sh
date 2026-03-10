#!/usr/bin/env bash
# 切換到本地 Supabase
# 會覆蓋現有 .env，請先備份或確認

set -e
cd "$(dirname "$0")/.."

echo "==> 切換到本地 Supabase"

if [[ ! -f backend/.env.local.example ]]; then
  echo "錯誤：找不到 backend/.env.local.example"
  exit 1
fi

# 若已是本地且含 keys，略過
if [[ -f backend/.env ]] && grep -q "SUPABASE_URL=http://host.docker.internal" backend/.env 2>/dev/null && \
   grep -qE "SUPABASE_ANON_KEY=.+" backend/.env 2>/dev/null; then
  echo "  backend/.env 已是本地設定，略過"
else
  cp backend/.env.local.example backend/.env
  echo "  已複製 backend/.env.local.example → backend/.env"
  NEED_SETUP=1
fi

if [[ ! -f frontend/.env.local.example ]]; then
  echo "錯誤：找不到 frontend/.env.local.example"
  exit 1
fi

if [[ -f frontend/.env ]] && grep -q "VITE_SUPABASE_URL=http://127.0.0.1" frontend/.env 2>/dev/null && \
   grep -qE "VITE_SUPABASE_ANON_KEY=.+" frontend/.env 2>/dev/null; then
  echo "  frontend/.env 已是本地設定，略過"
else
  cp frontend/.env.local.example frontend/.env
  echo "  已複製 frontend/.env.local.example → frontend/.env"
  NEED_SETUP=1
fi

[[ -n "$NEED_SETUP" ]] && echo "" && echo "  請執行 ./scripts/setup-local-supabase.sh 取得並填入 keys"

echo ""
echo "==> 下一步："
echo "  1. supabase start（若未啟動）"
echo "  2. ./scripts/setup-local-supabase.sh  # 取得 keys 並寫入 .env"
echo "  3. supabase db reset  # 套用 migrations"
echo "  4. docker compose -f infra/docker-compose.yml up --build"
