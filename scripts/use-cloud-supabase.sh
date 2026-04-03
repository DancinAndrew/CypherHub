#!/usr/bin/env bash
# 切換到雲端 Supabase
# 若有 .env.cloud 則複製到 .env；否則從 .env.cloud.example 建立 .env.cloud 並提示填寫

set -e
cd "$(dirname "$0")/.."

echo "==> 切換到雲端 Supabase"

if [[ -f .env.cloud ]]; then
  cp .env.cloud .env
  echo "  已複製 .env.cloud → .env"
else
  if [[ ! -f .env.cloud.example ]]; then
    echo "錯誤：找不到 .env.cloud.example"
    exit 1
  fi
  cp .env.cloud.example .env.cloud
  cp .env.cloud .env
  echo "  已建立 .env.cloud（從 example），請填寫雲端 key 後再執行此腳本。"
fi

echo ""
if [[ -f .env.cloud ]]; then
  echo "==> 已切換為雲端 Supabase。若專案曾 Pause，請到 Dashboard 喚醒（Resume）。"
  echo "==> 注意：如果你尚未在 .env 中填寫綠界金流 (ECPay) 參數，請記得填寫以免結帳失敗。"
else
  echo "==> 請編輯根目錄的 .env.cloud 填入雲端 key，再執行此腳本一次。"
  echo "    取得位置：Supabase Dashboard → Project Settings → API"
fi
echo ""
