-- MVP-2: orders, order_items, payments, webhook_events
-- 訂單與 hold 機制、金流記錄、Webhook 冪等
-- 參考：note.md、develop.md 2.1.1

BEGIN;

-- 1) order_status enum
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
    CREATE TYPE public.order_status AS ENUM (
      'created',
      'holding',
      'pending_payment',
      'paid',
      'issued',
      'cancelled',
      'refunded'
    );
  END IF;
END$$;

-- 2) payment_status enum
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
    CREATE TYPE public.payment_status AS ENUM (
      'pending',
      'completed',
      'failed',
      'refunded'
    );
  END IF;
END$$;

-- 3) orders 表
CREATE TABLE IF NOT EXISTS public.orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status public.order_status NOT NULL DEFAULT 'created',
  total_cents int NOT NULL DEFAULT 0,
  currency text NOT NULL DEFAULT 'TWD',
  hold_expires_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON public.orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_hold_expires ON public.orders(hold_expires_at) WHERE status = 'holding';

DROP TRIGGER IF EXISTS set_orders_updated_at ON public.orders;
CREATE TRIGGER set_orders_updated_at
BEFORE UPDATE ON public.orders
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 4) order_items 表
CREATE TABLE IF NOT EXISTS public.order_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
  ticket_type_id uuid NOT NULL REFERENCES public.ticket_types(id),
  quantity int NOT NULL CHECK (quantity >= 1),
  price_cents int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON public.order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_ticket_type ON public.order_items(ticket_type_id);

-- 5) payments 表（金流記錄，Webhook 寫入）
CREATE TABLE IF NOT EXISTS public.payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
  provider text NOT NULL,
  external_id text NOT NULL,
  amount_cents int NOT NULL,
  currency text NOT NULL DEFAULT 'TWD',
  status public.payment_status NOT NULL DEFAULT 'pending',
  raw_payload jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(provider, external_id)
);

CREATE INDEX IF NOT EXISTS idx_payments_order ON public.payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_provider_external ON public.payments(provider, external_id);

-- 6) webhook_events 表（冪等去重）
CREATE TABLE IF NOT EXISTS public.webhook_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  external_event_id text NOT NULL,
  event_type text NOT NULL,
  payload jsonb NULL,
  processed_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(provider, external_event_id)
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_provider_external ON public.webhook_events(provider, external_event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed ON public.webhook_events(processed_at) WHERE processed_at IS NULL;

-- 7) ticket_types 新增 hold_count
ALTER TABLE public.ticket_types ADD COLUMN IF NOT EXISTS hold_count int NOT NULL DEFAULT 0;

-- 8) 調整 inventory constraint：sold_count + hold_count <= capacity
ALTER TABLE public.ticket_types DROP CONSTRAINT IF EXISTS ticket_types_sold_check;
ALTER TABLE public.ticket_types ADD CONSTRAINT ticket_types_inventory_check
  CHECK (sold_count >= 0 AND hold_count >= 0 AND sold_count + hold_count <= capacity);

-- 9) RLS

ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_events ENABLE ROW LEVEL SECURITY;

-- orders: 使用者只能看自己的訂單
DROP POLICY IF EXISTS "orders_select_own" ON public.orders;
CREATE POLICY "orders_select_own"
ON public.orders FOR SELECT TO authenticated
USING (user_id = auth.uid());

DROP POLICY IF EXISTS "orders_insert_own" ON public.orders;
CREATE POLICY "orders_insert_own"
ON public.orders FOR INSERT TO authenticated
WITH CHECK (user_id = auth.uid());

-- orders UPDATE 僅限 backend（hold 逾時、狀態轉換）；RLS 預設 deny，service_role bypass
DROP POLICY IF EXISTS "orders_update_own" ON public.orders;
CREATE POLICY "orders_update_own"
ON public.orders FOR UPDATE TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- order_items: 透過 order 關聯，使用者只能看自己訂單的 items
DROP POLICY IF EXISTS "order_items_select_via_order" ON public.order_items;
CREATE POLICY "order_items_select_via_order"
ON public.order_items FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.orders o
    WHERE o.id = order_items.order_id AND o.user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "order_items_insert_via_order" ON public.order_items;
CREATE POLICY "order_items_insert_via_order"
ON public.order_items FOR INSERT TO authenticated
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.orders o
    WHERE o.id = order_items.order_id AND o.user_id = auth.uid()
  )
);

-- payments: 使用者只能看自己訂單的付款紀錄
DROP POLICY IF EXISTS "payments_select_via_order" ON public.payments;
CREATE POLICY "payments_select_via_order"
ON public.payments FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.orders o
    WHERE o.id = payments.order_id AND o.user_id = auth.uid()
  )
);

-- payments INSERT/UPDATE 僅 backend（Webhook 寫入）
-- 不建立 authenticated 的 INSERT/UPDATE policy，由 service_role 處理

-- webhook_events: 僅後端寫入，不對外暴露
-- 不建立任何 policy，authenticated/anon 無法存取；service_role bypass 可寫入

COMMIT;
