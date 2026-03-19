-- MVP-2.6: refunds 表，記錄退款狀態 requested/refunded/failed
-- 對應 develop.md 604-613、mvp2-6-refund-plan.md

BEGIN;

CREATE TABLE IF NOT EXISTS public.refunds (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
  amount_cents int NOT NULL,
  status text NOT NULL DEFAULT 'requested'
    CHECK (status IN ('requested', 'refunded', 'failed')),
  provider_trade_no text,
  raw_response jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_refunds_order ON public.refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_refunds_status ON public.refunds(status);

ALTER TABLE public.refunds ENABLE ROW LEVEL SECURITY;

-- refunds 僅後端寫入，不建 authenticated 政策，service_role bypass
COMMIT;
