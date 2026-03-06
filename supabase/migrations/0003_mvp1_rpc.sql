BEGIN;

-- 1) register_free (atomic + row lock + per-user limit)
-- Returns newly created tickets (includes qr_secret for QR generation)
CREATE OR REPLACE FUNCTION public.register_free(
  p_ticket_type_id uuid,
  p_quantity int DEFAULT 1
)
RETURNS SETOF public.tickets
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid uuid;
  v_tt public.ticket_types%ROWTYPE;
  v_existing int;
  v_event_status public.event_status;
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RAISE EXCEPTION USING errcode = '42501', message = 'AUTH_REQUIRED';
  END IF;

  IF p_quantity IS NULL OR p_quantity <= 0 THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'INVALID_QUANTITY';
  END IF;

  -- lock ticket type
  SELECT * INTO v_tt
  FROM public.ticket_types
  WHERE id = p_ticket_type_id
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'TICKET_TYPE_NOT_FOUND';
  END IF;

  -- MVP-1: free only
  IF v_tt.price_cents <> 0 THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'PAID_TICKET_NOT_ALLOWED_IN_MVP1';
  END IF;

  IF v_tt.is_active IS NOT TRUE THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'TICKET_TYPE_INACTIVE';
  END IF;

  SELECT e.status INTO v_event_status
  FROM public.events e
  WHERE e.id = v_tt.event_id;

  IF v_event_status IS DISTINCT FROM 'published'::public.event_status THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'EVENT_NOT_PUBLISHED';
  END IF;

  -- sale window checks (if provided)
  IF v_tt.sale_start_at IS NOT NULL AND now() < v_tt.sale_start_at THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'SALE_NOT_STARTED';
  END IF;

  IF v_tt.sale_end_at IS NOT NULL AND now() > v_tt.sale_end_at THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'SALE_ENDED';
  END IF;

  -- per-user limit
  SELECT COUNT(*) INTO v_existing
  FROM public.tickets t
  WHERE t.ticket_type_id = v_tt.id
    AND t.user_id = v_uid
    AND t.status IN ('issued','checked_in');

  IF v_existing + p_quantity > v_tt.per_user_limit THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'PER_USER_LIMIT_EXCEEDED';
  END IF;

  -- capacity check
  IF v_tt.sold_count + p_quantity > v_tt.capacity THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'SOLD_OUT';
  END IF;

  -- update sold_count atomically (we already hold FOR UPDATE lock)
  UPDATE public.ticket_types
  SET sold_count = sold_count + p_quantity
  WHERE id = v_tt.id;

  -- insert tickets (one row per ticket)
  RETURN QUERY
  INSERT INTO public.tickets (event_id, ticket_type_id, user_id, qr_secret, status)
  SELECT v_tt.event_id,
         v_tt.id,
         v_uid,
         encode(gen_random_bytes(16), 'hex'),
         'issued'::public.ticket_status
  FROM generate_series(1, p_quantity)
  RETURNING *;

END;
$$;

-- 2) verify_ticket_qr (no state change)
CREATE OR REPLACE FUNCTION public.verify_ticket_qr(
  p_event_id uuid,
  p_ticket_id uuid,
  p_qr_secret text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid uuid;
  v_ticket public.tickets%ROWTYPE;
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RETURN jsonb_build_object('valid', false, 'reason', 'AUTH_REQUIRED');
  END IF;

  -- organizer member check
  IF NOT public.is_event_member(p_event_id) THEN
    RETURN jsonb_build_object('valid', false, 'reason', 'FORBIDDEN');
  END IF;

  SELECT * INTO v_ticket
  FROM public.tickets
  WHERE id = p_ticket_id AND event_id = p_event_id;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('valid', false, 'reason', 'TICKET_NOT_FOUND');
  END IF;

  IF v_ticket.qr_secret <> p_qr_secret THEN
    RETURN jsonb_build_object('valid', false, 'reason', 'QR_MISMATCH');
  END IF;

  RETURN jsonb_build_object(
    'valid', true,
    'ticket_id', v_ticket.id,
    'ticket_type_id', v_ticket.ticket_type_id,
    'user_id', v_ticket.user_id,
    'status', v_ticket.status,
    'can_checkin', (v_ticket.status = 'issued')
  );
END;
$$;

-- 3) commit_checkin (atomic + idempotent)
CREATE OR REPLACE FUNCTION public.commit_checkin(
  p_event_id uuid,
  p_ticket_id uuid,
  p_qr_secret text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid uuid;
  v_updated int;
  v_ticket public.tickets%ROWTYPE;
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RETURN jsonb_build_object('ok', false, 'reason', 'AUTH_REQUIRED');
  END IF;

  IF NOT public.is_event_member(p_event_id) THEN
    RETURN jsonb_build_object('ok', false, 'reason', 'FORBIDDEN');
  END IF;

  -- atomic one-time update
  UPDATE public.tickets
  SET status = 'checked_in',
      checked_in_at = now(),
      checker_id = v_uid
  WHERE id = p_ticket_id
    AND event_id = p_event_id
    AND qr_secret = p_qr_secret
    AND status = 'issued';

  GET DIAGNOSTICS v_updated = ROW_COUNT;

  IF v_updated = 1 THEN
    RETURN jsonb_build_object('ok', true, 'checked_in', true, 'already_checked_in', false);
  END IF;

  -- idempotent: fetch current status to explain why not updated
  SELECT * INTO v_ticket
  FROM public.tickets
  WHERE id = p_ticket_id AND event_id = p_event_id;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'reason', 'TICKET_NOT_FOUND');
  END IF;

  IF v_ticket.qr_secret <> p_qr_secret THEN
    RETURN jsonb_build_object('ok', false, 'reason', 'QR_MISMATCH');
  END IF;

  IF v_ticket.status = 'checked_in' THEN
    RETURN jsonb_build_object('ok', true, 'checked_in', true, 'already_checked_in', true);
  END IF;

  RETURN jsonb_build_object('ok', false, 'reason', 'INVALID_STATUS', 'status', v_ticket.status);
END;
$$;

-- Restrict RPC execution surface and grant only authenticated calls.
REVOKE ALL ON FUNCTION public.register_free(uuid, int) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.verify_ticket_qr(uuid, uuid, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.commit_checkin(uuid, uuid, text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.register_free(uuid, int) TO authenticated;
GRANT EXECUTE ON FUNCTION public.verify_ticket_qr(uuid, uuid, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.commit_checkin(uuid, uuid, text) TO authenticated;

COMMIT;
