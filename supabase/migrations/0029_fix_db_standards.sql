-- ============================================================
-- 0029_fix_db_standards.sql
-- 修正違反 DATABASE_SUPABASE.md 標準的問題
-- 1. 確保 audit_logs 啟用 RLS
-- 2. 補上 live_progress 相關資料表的 updated_at trigger
-- 3. 補上 mvp3_settlements 相關資料表的 updated_at 欄位與 trigger
-- ============================================================

BEGIN;

-- 1. 確保 audit_logs 啟用 RLS (預設拒絕，僅 server-side 可以透過 service_role 寫入)
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- 2. 補上 live_progress 相關資料表 (event_stages, event_progress) 的 updated_at trigger
DROP TRIGGER IF EXISTS set_event_stages_updated_at ON public.event_stages;
CREATE TRIGGER set_event_stages_updated_at
BEFORE UPDATE ON public.event_stages
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS set_event_progress_updated_at ON public.event_progress;
CREATE TRIGGER set_event_progress_updated_at
BEFORE UPDATE ON public.event_progress
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 3. 補上 mvp3_settlements 相關資料表的 updated_at 欄位與 trigger
-- 3.a 針對 public.settlements 補上 updated_at 欄位
ALTER TABLE public.settlements ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

DROP TRIGGER IF EXISTS set_settlements_updated_at ON public.settlements;
CREATE TRIGGER set_settlements_updated_at
BEFORE UPDATE ON public.settlements
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 3.b 針對 public.payout_requests 補上 updated_at 欄位
ALTER TABLE public.payout_requests ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

DROP TRIGGER IF EXISTS set_payout_requests_updated_at ON public.payout_requests;
CREATE TRIGGER set_payout_requests_updated_at
BEFORE UPDATE ON public.payout_requests
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- (ledger_entries 通常為 append-only，不需 updated_at，且原有定義已符合標準)

COMMIT;
