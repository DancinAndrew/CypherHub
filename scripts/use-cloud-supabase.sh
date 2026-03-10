#!/usr/bin/env bash
# 切換到雲端 Supabase
# 會從 .env.cloud.example 複製模板，需手動填入真實 keys

set -e
cd "$(dirname "$0")/.."

echo "==> 切換到雲端 Supabase"

if [[ ! -f backend/.env.cloud.example ]]; then
  echo "錯誤：找不到 backend/.env.cloud.example"
  exit 1
fi

cp backend/.env.cloud.example backend/.env
echo "  已複製 backend/.env.cloud.example → backend/.env"

if [[ ! -f frontend/.env.cloud.example ]]; then
  echo "錯誤：找不到 frontend/.env.cloud.example"
  exit 1
fi

cp frontend/.env.cloud.example frontend/.env
echo "  已複製 frontend/.env.cloud.example → frontend/.env"

echo ""
echo "==> 重要：請編輯 backend/.env 與 frontend/.env，填入雲端專案的真實值："
echo "  - SUPABASE_URL / VITE_SUPABASE_URL：https://YOUR_PROJECT_REF.supabase.co"
echo "  - SUPABASE_ANON_KEY / VITE_SUPABASE_ANON_KEY"
echo "  - SUPABASE_SERVICE_ROLE_KEY"
echo ""
echo "  取得位置：Supabase Dashboard → Project Settings → API"
echo ""
echo "  若 cloud 專案有 pause，請先到 Dashboard 喚醒（Resume）。"
echo ""
echo "  套用 migrations 到雲端："
echo "  supabase link --project-ref YOUR_PROJECT_REF"
echo "  supabase db push"
