#!/usr/bin/env bash
# 將 migrations 推到 Supabase Cloud，保持專案活躍
# 使用前：請在 backend/.env 與 frontend/.env 填入 Cloud 專案的 URL 和 keys
# 若尚未連結，執行：supabase link --project-ref mcqpgnavygeuylisjllr

set -e
cd "$(dirname "$0")/.."

echo "==> Supabase Cloud 推送"
echo ""

# 檢查是否已登入
if ! supabase projects list &>/dev/null; then
  echo "請先執行：supabase login"
  exit 1
fi

# 檢查是否已 link（若 .temp/project-ref 存在且與預期相符則視為已 link）
PROJECT_REF="mcqpgnavygeuylisjllr"
if [[ -f supabase/.temp/project-ref ]]; then
  LINKED_REF=$(cat supabase/.temp/project-ref)
  if [[ "$LINKED_REF" != "$PROJECT_REF" ]]; then
    echo "目前連結的專案：$LINKED_REF"
    echo "若要改為 $PROJECT_REF，請執行：supabase link --project-ref $PROJECT_REF"
  fi
else
  echo "尚未 link，執行：supabase link --project-ref $PROJECT_REF"
  supabase link --project-ref "$PROJECT_REF"
fi

echo ""
echo "==> 執行 db push（dry-run 檢查）"
supabase db push --dry-run

echo ""
echo "==> 正式推送 migrations"
supabase db push

echo ""
echo "==> 完成。可用以下指令檢查："
echo "  supabase migration list"
echo ""
echo "若需建立測試用戶與資料，請執行："
echo "  python scripts/seed-cloud-test-data.py"
echo "  （需先在 backend/.env 填入 SUPABASE_URL 與 SUPABASE_SERVICE_ROLE_KEY）"
