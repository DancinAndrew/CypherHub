-- 1.5.3: Platform governance - disabled status, block checkin for ended/cancelled/disabled

BEGIN;

-- Add disabled to event_status (admin 下架用)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_enum e
    JOIN pg_type t ON e.enumtypid = t.oid
    WHERE t.typname = 'event_status' AND e.enumlabel = 'disabled'
  ) THEN
    ALTER TYPE public.event_status ADD VALUE 'disabled';
  END IF;
END$$;

-- Block checkin when event is ended/cancelled/disabled
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
  v_event_status public.event_status;
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RETURN jsonb_build_object('valid', false, 'reason', 'AUTH_REQUIRED');
  END IF;

  IF NOT public.is_event_member(p_event_id) THEN
    RETURN jsonb_build_object('valid', false, 'reason', 'FORBIDDEN');
  END IF;

  SELECT e.status INTO v_event_status
  FROM public.events e
  WHERE e.id = p_event_id;

  IF v_event_status IN ('ended', 'cancelled', 'disabled') THEN
    RETURN jsonb_build_object('valid', false, 'reason', 'EVENT_ENDED_OR_CANCELLED', 'can_checkin', false);
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
  v_event_status public.event_status;
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RETURN jsonb_build_object('ok', false, 'reason', 'AUTH_REQUIRED');
  END IF;

  IF NOT public.is_event_member(p_event_id) THEN
    RETURN jsonb_build_object('ok', false, 'reason', 'FORBIDDEN');
  END IF;

  SELECT e.status INTO v_event_status
  FROM public.events e
  WHERE e.id = p_event_id;

  IF v_event_status IN ('ended', 'cancelled', 'disabled') THEN
    RETURN jsonb_build_object('ok', false, 'reason', 'EVENT_ENDED_OR_CANCELLED');
  END IF;

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

-- register_free_v2: ensure disabled also blocks (already checks IS DISTINCT FROM 'published')
-- No change needed - disabled/cancelled/ended all fail that check.

COMMIT;
