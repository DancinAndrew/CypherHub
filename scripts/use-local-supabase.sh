#!/usr/bin/env bash
# 切換到本地 Supabase
# 若有 .env.local 則複製到 .env（保留本地 key）；否則從 .env.local.example 建立 .env.local 並提示執行 setup-local-supabase.sh

set -e
cd "$(dirname "$0")/.."

echo "==> 切換到本地 Supabase"

NEED_SETUP=

# Backend
if [[ -f backend/.env.local ]]; then
  cp backend/.env.local backend/.env
  echo "  已複製 backend/.env.local → backend/.env"
else
  if [[ ! -f backend/.env.local.example ]]; then
    echo "錯誤：找不到 backend/.env.local.example"
    exit 1
  fi
  cp backend/.env.local.example backend/.env.local
  cp backend/.env.local backend/.env
  echo "  已建立 backend/.env.local（從 example）"
  NEED_SETUP=1
fi

# Frontend
if [[ -f frontend/.env.local ]]; then
  cp frontend/.env.local frontend/.env
  echo "  已複製 frontend/.env.local → frontend/.env"
else
  if [[ ! -f frontend/.env.local.example ]]; then
    echo "錯誤：找不到 frontend/.env.local.example"
    exit 1
  fi
  cp frontend/.env.local.example frontend/.env.local
  cp frontend/.env.local frontend/.env
  echo "  已建立 frontend/.env.local（從 example）"
  NEED_SETUP=1
fi

echo ""
if [[ -n "$NEED_SETUP" ]]; then
  echo "  請執行：./scripts/setup-local-supabase.sh  取得本地 keys 並寫入 .env / .env.local"
  echo "  之後再切換本地時，直接跑此腳本即可，無需重填。"
fi
echo "==> 下一步："
echo "  1. supabase start（若未啟動）"
echo "  2. ./scripts/setup-local-supabase.sh  # 首次或 keys 遺失時"
echo "  3. supabase db reset  # 套用 migrations"
echo "  4. docker compose -f infra/docker-compose.yml up --build"
echo ""
