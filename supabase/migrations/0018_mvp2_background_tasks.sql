-- MVP-2 背景任務：pg_cron + 純 SQL RPC
-- 1. Hold 逾時釋放（每 1 分鐘）
-- 2. 補償出票（每 5 分鐘）
-- 參考：background-tasks-analysis.md 方案 C

BEGIN;

-- 0) pg_cron 擴展（Cloud 若已啟用 Cron 整合則會跳過）
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;
GRANT USAGE ON SCHEMA cron TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres;

-- 1) tickets 新增 order_id（付費訂單出票用，補償時可檢查是否已出票）
ALTER TABLE public.tickets ADD COLUMN IF NOT EXISTS order_id uuid NULL REFERENCES public.orders(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_tickets_order ON public.tickets(order_id) WHERE order_id IS NOT NULL;

-- 2) release_expired_holds：逾時 holding → cancelled，扣回 hold_count
CREATE OR REPLACE FUNCTION public.release_expired_holds()
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_order_id uuid;
  v_count int := 0;
BEGIN
  FOR v_order_id IN
    SELECT id FROM public.orders
    WHERE status = 'holding' AND hold_expires_at IS NOT NULL AND hold_expires_at < now()
    FOR UPDATE SKIP LOCKED
  LOOP
    UPDATE public.orders SET status = 'cancelled', updated_at = now() WHERE id = v_order_id;
    UPDATE public.ticket_types tt
    SET hold_count = tt.hold_count - sub.qty
    FROM (
      SELECT ticket_type_id, SUM(quantity)::int AS qty
      FROM public.order_items
      WHERE order_id = v_order_id
      GROUP BY ticket_type_id
    ) sub
    WHERE tt.id = sub.ticket_type_id;
    v_count := v_count + 1;
  END LOOP;
  RETURN v_count;
END;
$$;

-- 3) compensate_paid_orders：paid 但無對應 tickets → 建立 tickets，status→issued
CREATE OR REPLACE FUNCTION public.compensate_paid_orders()
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_order public.orders%ROWTYPE;
  v_item public.order_items%ROWTYPE;
  v_tt public.ticket_types%ROWTYPE;
  v_existing int;
  v_to_create int;
  v_orders_compensated int := 0;
BEGIN
  FOR v_order IN
    SELECT o.* FROM public.orders o
    WHERE o.status = 'paid'
    FOR UPDATE SKIP LOCKED
  LOOP
    FOR v_item IN
      SELECT * FROM public.order_items WHERE order_id = v_order.id
    LOOP
      SELECT * INTO v_tt FROM public.ticket_types WHERE id = v_item.ticket_type_id FOR UPDATE;
      IF NOT FOUND THEN
        CONTINUE;
      END IF;

      SELECT COUNT(*)::int INTO v_existing
      FROM public.tickets t
      WHERE t.order_id = v_order.id AND t.ticket_type_id = v_item.ticket_type_id
        AND t.status IN ('issued', 'checked_in');

      v_to_create := v_item.quantity - v_existing;
      IF v_to_create <= 0 THEN
        CONTINUE;
      END IF;

      INSERT INTO public.tickets (event_id, ticket_type_id, user_id, order_id, qr_secret, status)
      SELECT v_tt.event_id, v_tt.id, v_order.user_id, v_order.id,
             encode(gen_random_bytes(16), 'hex'), 'issued'::public.ticket_status
      FROM generate_series(1, v_to_create);

      UPDATE public.ticket_types
      SET sold_count = sold_count + v_to_create
      WHERE id = v_item.ticket_type_id;

    END LOOP;

    UPDATE public.orders SET status = 'issued', updated_at = now() WHERE id = v_order.id;
    v_orders_compensated := v_orders_compensated + 1;
  END LOOP;

  RETURN v_orders_compensated;
END;
$$;

-- 4) pg_cron 排程（先移除避免 migration 重跑時重複）
DO $$
BEGIN
  PERFORM cron.unschedule('release-expired-holds');
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;
DO $$
BEGIN
  PERFORM cron.unschedule('compensate-paid-orders');
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

SELECT cron.schedule(
  'release-expired-holds',
  '* * * * *',  -- 每分鐘
  $$SELECT public.release_expired_holds()$$
);
SELECT cron.schedule(
  'compensate-paid-orders',
  '*/5 * * * *',  -- 每 5 分鐘
  $$SELECT public.compensate_paid_orders()$$
);

COMMIT;
