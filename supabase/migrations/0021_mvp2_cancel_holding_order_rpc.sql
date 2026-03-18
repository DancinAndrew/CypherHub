-- MVP-2: 使用者可取消自己的 holding 訂單，釋放 hold_count

BEGIN;

CREATE OR REPLACE FUNCTION public.cancel_holding_order(p_order_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid uuid;
  v_status public.order_status;
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RAISE EXCEPTION USING errcode = '42501', message = 'AUTH_REQUIRED';
  END IF;

  SELECT status INTO v_status FROM public.orders WHERE id = p_order_id AND user_id = v_uid;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'ORDER_NOT_FOUND';
  END IF;

  IF v_status IS DISTINCT FROM 'holding'::public.order_status THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'ORDER_NOT_HOLDING';
  END IF;

  UPDATE public.orders SET status = 'cancelled', updated_at = now() WHERE id = p_order_id;

  UPDATE public.ticket_types tt
  SET hold_count = tt.hold_count - sub.qty
  FROM (
    SELECT ticket_type_id, SUM(quantity)::int AS qty
    FROM public.order_items
    WHERE order_id = p_order_id
    GROUP BY ticket_type_id
  ) sub
  WHERE tt.id = sub.ticket_type_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.cancel_holding_order(uuid) TO authenticated;

COMMIT;
