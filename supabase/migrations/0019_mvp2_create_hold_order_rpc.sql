-- MVP-2: create_hold_order RPC（原子扣 hold、建立 holding 訂單）
-- 選票種 → 建立 order status=holding，逾時由 release_expired_holds 釋放
-- develop.md 2.1.2

BEGIN;

-- p_items: [{"ticket_type_id": "uuid", "quantity": 1}, ...]
-- p_hold_minutes: 預設 15
-- 回傳: 新建 order 的 id（API 可再 GET 取得詳情）
CREATE OR REPLACE FUNCTION public.create_hold_order(
  p_items jsonb,
  p_hold_minutes int DEFAULT 15
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_uid uuid;
  v_order_id uuid;
  v_hold_expires timestamptz;
  v_item jsonb;
  v_tt_id uuid;
  v_qty int;
  v_price int;
  v_total_cents int := 0;
  v_existing_tickets int;
  v_existing_holds int;
  v_tt public.ticket_types%ROWTYPE;
  v_event_status public.event_status;
  v_items_processed int := 0;
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RAISE EXCEPTION USING errcode = '42501', message = 'AUTH_REQUIRED';
  END IF;

  IF p_items IS NULL OR jsonb_array_length(p_items) = 0 THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'HOLD_ITEMS_EMPTY';
  END IF;

  IF p_hold_minutes IS NULL OR p_hold_minutes < 1 OR p_hold_minutes > 60 THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'INVALID_HOLD_MINUTES';
  END IF;

  v_hold_expires := now() + (p_hold_minutes || ' minutes')::interval;

  -- 1) 鎖定並驗證所有 ticket_types，累積 total、更新 hold_count
  FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
  LOOP
    v_tt_id := (v_item->>'ticket_type_id')::uuid;
    v_qty := COALESCE((v_item->>'quantity')::int, 0);

    IF v_tt_id IS NULL OR v_qty < 1 THEN
      RAISE EXCEPTION USING errcode = '22023', message = 'INVALID_ITEM';
    END IF;

    SELECT * INTO v_tt
    FROM public.ticket_types
    WHERE id = v_tt_id
    FOR UPDATE;

    IF NOT FOUND THEN
      RAISE EXCEPTION USING errcode = '22023', message = 'TICKET_TYPE_NOT_FOUND';
    END IF;

    IF v_tt.is_active IS NOT TRUE THEN
      RAISE EXCEPTION USING errcode = '22023', message = 'TICKET_TYPE_INACTIVE';
    END IF;

    SELECT e.status INTO v_event_status
    FROM public.events e WHERE e.id = v_tt.event_id;
    IF v_event_status IS DISTINCT FROM 'published'::public.event_status THEN
      RAISE EXCEPTION USING errcode = '22023', message = 'EVENT_NOT_PUBLISHED';
    END IF;

    IF v_tt.sale_start_at IS NOT NULL AND now() < v_tt.sale_start_at THEN
      RAISE EXCEPTION USING errcode = '22023', message = 'SALE_NOT_STARTED';
    END IF;

    IF v_tt.sale_end_at IS NOT NULL AND now() > v_tt.sale_end_at THEN
      RAISE EXCEPTION USING errcode = '22023', message = 'SALE_ENDED';
    END IF;

    IF v_tt.sold_count + v_tt.hold_count + v_qty > v_tt.capacity THEN
      RAISE EXCEPTION USING errcode = '22023', message = 'SOLD_OUT';
    END IF;

    -- per_user_limit: tickets + 未逾時的 holding 訂單的 quantity（逾時 holding 不計入，免阻擋重試）
    SELECT COUNT(*)::int INTO v_existing_tickets
    FROM public.tickets t
    WHERE t.ticket_type_id = v_tt.id AND t.user_id = v_uid
      AND t.status IN ('issued', 'checked_in');

    SELECT COALESCE(SUM(oi.quantity), 0)::int INTO v_existing_holds
    FROM public.order_items oi
    JOIN public.orders o ON o.id = oi.order_id
    WHERE oi.ticket_type_id = v_tt.id
      AND o.user_id = v_uid
      AND o.status = 'holding'
      AND (o.hold_expires_at IS NULL OR o.hold_expires_at >= now());

    IF v_existing_tickets + v_existing_holds + v_qty > v_tt.per_user_limit THEN
      RAISE EXCEPTION USING errcode = '22023', message = 'PER_USER_LIMIT_EXCEEDED';
    END IF;

    v_price := v_tt.price_cents;
    v_total_cents := v_total_cents + (v_price * v_qty);

    UPDATE public.ticket_types
    SET hold_count = hold_count + v_qty, updated_at = now()
    WHERE id = v_tt_id;

    v_items_processed := v_items_processed + 1;
  END LOOP;

  -- 2) 建立 order
  INSERT INTO public.orders (user_id, status, total_cents, hold_expires_at, updated_at)
  VALUES (v_uid, 'holding'::public.order_status, v_total_cents, v_hold_expires, now())
  RETURNING id INTO v_order_id;

  -- 3) 建立 order_items
  FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
  LOOP
    v_tt_id := (v_item->>'ticket_type_id')::uuid;
    v_qty := (v_item->>'quantity')::int;

    SELECT price_cents INTO v_price FROM public.ticket_types WHERE id = v_tt_id;

    INSERT INTO public.order_items (order_id, ticket_type_id, quantity, price_cents)
    VALUES (v_order_id, v_tt_id, v_qty, v_price);
  END LOOP;

  RETURN v_order_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.create_hold_order(jsonb, int) TO authenticated;

COMMIT;
