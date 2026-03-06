BEGIN;

CREATE OR REPLACE FUNCTION public.register_free_v2(
  p_ticket_type_id uuid,
  p_quantity int DEFAULT 1,
  p_answers jsonb DEFAULT '{}'::jsonb
)
RETURNS SETOF public.tickets
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_uid uuid;
  v_tt public.ticket_types%ROWTYPE;
  v_existing int;
  v_event_status public.event_status;
  v_form_id uuid;
  v_ticket public.tickets%ROWTYPE;
  v_answers jsonb := COALESCE(p_answers, '{}'::jsonb);
BEGIN
  v_uid := auth.uid();
  IF v_uid IS NULL THEN
    RAISE EXCEPTION USING errcode = '42501', message = 'AUTH_REQUIRED';
  END IF;

  IF p_quantity IS NULL OR p_quantity <= 0 THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'INVALID_QUANTITY';
  END IF;

  SELECT * INTO v_tt
  FROM public.ticket_types
  WHERE id = p_ticket_type_id
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'TICKET_TYPE_NOT_FOUND';
  END IF;

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

  IF v_tt.sale_start_at IS NOT NULL AND now() < v_tt.sale_start_at THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'SALE_NOT_STARTED';
  END IF;

  IF v_tt.sale_end_at IS NOT NULL AND now() > v_tt.sale_end_at THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'SALE_ENDED';
  END IF;

  SELECT COUNT(*) INTO v_existing
  FROM public.tickets t
  WHERE t.ticket_type_id = v_tt.id
    AND t.user_id = v_uid
    AND t.status IN ('issued','checked_in');

  IF v_existing + p_quantity > v_tt.per_user_limit THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'PER_USER_LIMIT_EXCEEDED';
  END IF;

  IF v_tt.sold_count + p_quantity > v_tt.capacity THEN
    RAISE EXCEPTION USING errcode = '22023', message = 'SOLD_OUT';
  END IF;

  SELECT ef.id INTO v_form_id
  FROM public.event_forms ef
  WHERE ef.ticket_type_id = v_tt.id
    AND ef.is_active = true
  LIMIT 1;

  IF v_form_id IS NULL THEN
    SELECT ef.id INTO v_form_id
    FROM public.event_forms ef
    WHERE ef.event_id = v_tt.event_id
      AND ef.ticket_type_id IS NULL
      AND ef.is_active = true
    LIMIT 1;
  END IF;

  UPDATE public.ticket_types
  SET sold_count = sold_count + p_quantity
  WHERE id = v_tt.id;

  FOR v_ticket IN
    INSERT INTO public.tickets (event_id, ticket_type_id, user_id, qr_secret, status)
    SELECT v_tt.event_id,
           v_tt.id,
           v_uid,
           encode(gen_random_bytes(16), 'hex'),
           'issued'::public.ticket_status
    FROM generate_series(1, p_quantity)
    RETURNING *
  LOOP
    IF v_form_id IS NOT NULL THEN
      INSERT INTO public.ticket_form_responses (
        ticket_id,
        event_id,
        ticket_type_id,
        user_id,
        form_id,
        answers
      )
      VALUES (
        v_ticket.id,
        v_ticket.event_id,
        v_ticket.ticket_type_id,
        v_uid,
        v_form_id,
        v_answers
      );
    END IF;

    RETURN NEXT v_ticket;
  END LOOP;
END;
$$;

GRANT EXECUTE ON FUNCTION public.register_free_v2(uuid, int, jsonb) TO authenticated;

COMMIT;
