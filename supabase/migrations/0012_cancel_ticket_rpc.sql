-- 使用者取消自己的報名（將票券設為 cancelled，並扣回 ticket_types.sold_count）
BEGIN;

CREATE OR REPLACE FUNCTION public.cancel_ticket(p_ticket_id uuid)
RETURNS SETOF public.tickets
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_uid uuid;
  v_tt_id uuid;
  v_ticket public.tickets%ROWTYPE;
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RAISE EXCEPTION USING errcode = '42501', message = 'AUTH_REQUIRED';
  END IF;

  SELECT ticket_type_id INTO v_tt_id
  FROM public.tickets
  WHERE id = p_ticket_id
    AND user_id = v_uid
    AND status IN ('issued', 'checked_in');

  IF NOT FOUND THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'TICKET_NOT_FOUND_OR_ALREADY_CANCELLED';
  END IF;

  UPDATE public.tickets
  SET status = 'cancelled'::public.ticket_status,
      cancelled_at = now()
  WHERE id = p_ticket_id
    AND user_id = v_uid
    AND status IN ('issued', 'checked_in')
  RETURNING * INTO v_ticket;

  UPDATE public.ticket_types
  SET sold_count = GREATEST(0, sold_count - 1)
  WHERE id = v_tt_id;

  RETURN NEXT v_ticket;
END;
$$;

GRANT EXECUTE ON FUNCTION public.cancel_ticket(uuid) TO authenticated;

COMMIT;
