-- MVP-3.2: 主辦方入駐審核。organizations 新增 approval_status 等欄位。
-- 對應 docs/development/mvp3/mvp3-2-org-approval-plan.md

BEGIN;

-- 1) 新增審核相關欄位
ALTER TABLE public.organizations
  ADD COLUMN IF NOT EXISTS approval_status text
    DEFAULT 'approved'
    CHECK (approval_status IN ('pending', 'approved', 'rejected'));

ALTER TABLE public.organizations
  ADD COLUMN IF NOT EXISTS approved_at timestamptz;

ALTER TABLE public.organizations
  ADD COLUMN IF NOT EXISTS approved_by uuid;

ALTER TABLE public.organizations
  ADD COLUMN IF NOT EXISTS rejection_reason text;

ALTER TABLE public.organizations
  ADD COLUMN IF NOT EXISTS payout_bank_info jsonb;

-- 2) 既有 org 一律設為 approved（向下相容）
UPDATE public.organizations
SET approval_status = 'approved'
WHERE approval_status IS NULL OR approval_status = '';

COMMIT;
