-- MVP-3.3: 結算與提款。settlements、ledger_entries、payout_requests。
-- 對應 docs/development/mvp3/mvp3-master-plan.md 四

BEGIN;

-- 1) settlements 表
CREATE TABLE IF NOT EXISTS public.settlements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  period_start timestamptz NOT NULL,
  period_end timestamptz NOT NULL,
  gross_cents int NOT NULL DEFAULT 0,
  platform_fee_cents int NOT NULL DEFAULT 0,
  net_cents int NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'finalized')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_settlements_org ON public.settlements(org_id);
CREATE INDEX IF NOT EXISTS idx_settlements_period ON public.settlements(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_settlements_status ON public.settlements(status);

-- 2) ledger_entries 表
CREATE TABLE IF NOT EXISTS public.ledger_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  event_id uuid REFERENCES public.events(id) ON DELETE SET NULL,
  order_id uuid REFERENCES public.orders(id) ON DELETE SET NULL,
  type text NOT NULL CHECK (type IN ('sale', 'refund', 'platform_fee', 'payout')),
  amount_cents int NOT NULL,
  settlement_id uuid REFERENCES public.settlements(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_org ON public.ledger_entries(org_id);
CREATE INDEX IF NOT EXISTS idx_ledger_settlement ON public.ledger_entries(settlement_id);
CREATE INDEX IF NOT EXISTS idx_ledger_order ON public.ledger_entries(order_id);
CREATE INDEX IF NOT EXISTS idx_ledger_created ON public.ledger_entries(created_at);

-- 3) payout_requests 表
CREATE TABLE IF NOT EXISTS public.payout_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  settlement_id uuid REFERENCES public.settlements(id) ON DELETE SET NULL,
  amount_cents int NOT NULL CHECK (amount_cents > 0),
  status text NOT NULL DEFAULT 'requested' CHECK (status IN ('requested', 'approved', 'paid', 'failed')),
  requested_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz NULL,
  failure_reason text NULL
);

CREATE INDEX IF NOT EXISTS idx_payout_requests_org ON public.payout_requests(org_id);
CREATE INDEX IF NOT EXISTS idx_payout_requests_status ON public.payout_requests(status);

-- 4) RLS（主辦方僅能看自己的 settlements/ledger；Admin 用 service_role）
ALTER TABLE public.settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payout_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "settlements_select_org_member" ON public.settlements;
CREATE POLICY "settlements_select_org_member"
ON public.settlements FOR SELECT TO authenticated
USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS "ledger_select_org_member" ON public.ledger_entries;
CREATE POLICY "ledger_select_org_member"
ON public.ledger_entries FOR SELECT TO authenticated
USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS "payout_select_org_member" ON public.payout_requests;
CREATE POLICY "payout_select_org_member"
ON public.payout_requests FOR SELECT TO authenticated
USING (public.is_org_member(org_id));

-- 主辦方可新增 payout_request（僅 requested）
DROP POLICY IF EXISTS "payout_insert_org_admin" ON public.payout_requests;
CREATE POLICY "payout_insert_org_admin"
ON public.payout_requests FOR INSERT TO authenticated
WITH CHECK (public.is_org_admin(org_id) AND status = 'requested');

COMMIT;
