-- MVP-2.3: 修正 hold_count 為 v_to_create，確保冪等（多次補償不重複扣減）
-- issue_tickets_for_order、compensate_paid_orders 在部分出票時應只釋放實際建立數量

BEGIN;

-- 1) issue_tickets_for_order: hold_count -= v_to_create（非 v_item.quantity）
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
        hold_count = hold_count - v_to_create
    WHERE id = v_item.ticket_type_id;

    v_tickets_created := v_tickets_created + v_to_create;
  END LOOP;

  UPDATE public.orders SET status = 'issued', updated_at = now() WHERE id = p_order_id;

  RETURN v_tickets_created;
END;
$$;

-- 2) compensate_paid_orders: 補上 hold_count 更新，與 issue_tickets 一致
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
      SET sold_count = sold_count + v_to_create,
          hold_count = hold_count - v_to_create
      WHERE id = v_item.ticket_type_id;

    END LOOP;

    UPDATE public.orders SET status = 'issued', updated_at = now() WHERE id = v_order.id;
    v_orders_compensated := v_orders_compensated + 1;
  END LOOP;

  RETURN v_orders_compensated;
END;
$$;

COMMIT;
