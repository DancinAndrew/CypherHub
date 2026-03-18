-- MVP-2: issue_tickets_for_order RPC（Webhook 收到 paid 後即時出票）
-- 同 compensate_paid_orders 邏輯，但僅處理單一 order
-- develop.md 2.2.1

BEGIN;

CREATE OR REPLACE FUNCTION public.issue_tickets_for_order(p_order_id uuid)
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
  v_tickets_created int := 0;
BEGIN
  SELECT * INTO v_order FROM public.orders WHERE id = p_order_id AND status = 'paid' FOR UPDATE;
  IF NOT FOUND THEN
    RETURN 0;
  END IF;

  FOR v_item IN SELECT * FROM public.order_items WHERE order_id = p_order_id
  LOOP
    SELECT * INTO v_tt FROM public.ticket_types WHERE id = v_item.ticket_type_id FOR UPDATE;
    IF NOT FOUND THEN
      CONTINUE;
    END IF;

    SELECT COUNT(*)::int INTO v_existing
    FROM public.tickets t
    WHERE t.order_id = p_order_id AND t.ticket_type_id = v_item.ticket_type_id
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
    SET sold_count = sold_count + v_to_create,
        hold_count = hold_count - v_item.quantity
    WHERE id = v_item.ticket_type_id;

    v_tickets_created := v_tickets_created + v_to_create;
  END LOOP;

  UPDATE public.orders SET status = 'issued', updated_at = now() WHERE id = p_order_id;

  RETURN v_tickets_created;
END;
$$;

-- service_role 或 backend 呼叫，不開放 authenticated
-- GRANT EXECUTE 由 backend 以 service_role 執行即可

COMMIT;
