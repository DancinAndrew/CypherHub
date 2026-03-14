#!/usr/bin/env bash
# 切換到雲端 Supabase
# 若有 .env.cloud 則複製到 .env（保留你的 key）；否則從 .env.cloud.example 建立 .env.cloud 並提示填寫

set -e
cd "$(dirname "$0")/.."

echo "==> 切換到雲端 Supabase"

# Backend
if [[ -f backend/.env.cloud ]]; then
  cp backend/.env.cloud backend/.env
  echo "  已複製 backend/.env.cloud → backend/.env"
else
  if [[ ! -f backend/.env.cloud.example ]]; then
    echo "錯誤：找不到 backend/.env.cloud.example"
    exit 1
  fi
  cp backend/.env.cloud.example backend/.env.cloud
  cp backend/.env.cloud backend/.env
  echo "  已建立 backend/.env.cloud（從 example），請填入雲端 key 後再執行此腳本"
fi

# Frontend
if [[ -f frontend/.env.cloud ]]; then
  cp frontend/.env.cloud frontend/.env
  echo "  已複製 frontend/.env.cloud → frontend/.env"
else
  if [[ ! -f frontend/.env.cloud.example ]]; then
    echo "錯誤：找不到 frontend/.env.cloud.example"
    exit 1
  fi
  cp frontend/.env.cloud.example frontend/.env.cloud
  cp frontend/.env.cloud frontend/.env
  echo "  已建立 frontend/.env.cloud（從 example），請填入雲端 key 後再執行此腳本"
fi

echo ""
if [[ -f backend/.env.cloud ]] && [[ -f frontend/.env.cloud ]]; then
  echo "==> 已切換為雲端 Supabase。若專案曾 Pause，請到 Dashboard 喚醒（Resume）。"
else
  echo "==> 請編輯 backend/.env.cloud 與 frontend/.env.cloud 填入雲端 key，再執行此腳本一次。"
  echo "    取得位置：Supabase Dashboard → Project Settings → API"
fi
echo ""
