-- MVP-1 one-click verification (Cloud SQL Editor / local SQL console)
-- Replace only these 2 UUID values before running:
--   OWNER_UUID: organizer owner who can create org/event and perform check-in
--   ATTENDEE_UUID: attendee who calls register_free
--
-- NOTE:
-- 1) OWNER_UUID and ATTENDEE_UUID must both exist in auth.users
-- 2) OWNER_UUID and ATTENDEE_UUID must be different users

DO $$
DECLARE
  owner_uuid uuid := '00000000-0000-0000-0000-000000000000'::uuid;
  attendee_uuid uuid := '11111111-1111-1111-1111-111111111111'::uuid;

  org_id uuid;
  event_id uuid;
  ticket_type_id uuid;
  issued_ticket public.tickets%ROWTYPE;

  verify_owner jsonb;
  verify_attendee jsonb;
  commit_once jsonb;
  commit_twice jsonb;
BEGIN
  IF owner_uuid = attendee_uuid THEN
    RAISE EXCEPTION 'OWNER_UUID and ATTENDEE_UUID must be different';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users u WHERE u.id = owner_uuid) THEN
    RAISE EXCEPTION 'OWNER_UUID not found in auth.users: %', owner_uuid;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users u WHERE u.id = attendee_uuid) THEN
    RAISE EXCEPTION 'ATTENDEE_UUID not found in auth.users: %', attendee_uuid;
  END IF;

  -- A) OWNER creates organization (trigger should auto-insert organizer_members owner row)
  PERFORM set_config('request.jwt.claim.sub', owner_uuid::text, true);
  PERFORM set_config('request.jwt.claim.role', 'authenticated', true);

  INSERT INTO public.organizations (name, owner_user_id)
  VALUES ('Verify Org ' || substr(gen_random_uuid()::text, 1, 8), owner_uuid)
  RETURNING id INTO org_id;

  IF NOT EXISTS (
    SELECT 1
    FROM public.organizer_members m
    WHERE m.org_id = org_id AND m.user_id = owner_uuid AND m.role = 'owner'
  ) THEN
    RAISE EXCEPTION 'owner membership trigger check failed for org_id=%', org_id;
  END IF;
  RAISE NOTICE 'A) org created, owner membership exists. org_id=%', org_id;

  -- B) OWNER creates published event and free ticket type
  INSERT INTO public.events (org_id, title, start_at, end_at, status, published_at, created_by)
  VALUES (
    org_id,
    'Verify Event ' || substr(gen_random_uuid()::text, 1, 8),
    now() + interval '7 days',
    now() + interval '7 days 2 hours',
    'published',
    now(),
    owner_uuid
  )
  RETURNING id INTO event_id;

  INSERT INTO public.ticket_types (event_id, name, capacity, per_user_limit, price_cents, is_active)
  VALUES (event_id, 'Verify Free Ticket', 2, 1, 0, true)
  RETURNING id INTO ticket_type_id;

  RAISE NOTICE 'B) event and ticket_type created. event_id=%, ticket_type_id=%', event_id, ticket_type_id;

  -- C) ATTENDEE registers one free ticket
  PERFORM set_config('request.jwt.claim.sub', attendee_uuid::text, true);
  PERFORM set_config('request.jwt.claim.role', 'authenticated', true);

  SELECT t.*
  INTO issued_ticket
  FROM public.register_free(ticket_type_id, 1) AS t
  LIMIT 1;

  IF issued_ticket.id IS NULL THEN
    RAISE EXCEPTION 'register_free did not return a ticket row';
  END IF;

  RAISE NOTICE 'C) register_free success. ticket_id=%, qr_secret=%', issued_ticket.id, issued_ticket.qr_secret;

  -- H) Optional forbidden check: attendee cannot verify ticket for event
  verify_attendee := public.verify_ticket_qr(event_id, issued_ticket.id, issued_ticket.qr_secret);
  RAISE NOTICE 'H) attendee verify result=%', verify_attendee;
  IF COALESCE(verify_attendee->>'reason', '') <> 'FORBIDDEN' THEN
    RAISE EXCEPTION 'Expected FORBIDDEN for attendee verify, got: %', verify_attendee;
  END IF;

  -- D) OWNER verifies QR
  PERFORM set_config('request.jwt.claim.sub', owner_uuid::text, true);
  PERFORM set_config('request.jwt.claim.role', 'authenticated', true);

  verify_owner := public.verify_ticket_qr(event_id, issued_ticket.id, issued_ticket.qr_secret);
  RAISE NOTICE 'D) owner verify result=%', verify_owner;

  IF (verify_owner->>'valid')::boolean IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'Expected verify valid=true, got: %', verify_owner;
  END IF;

  IF (verify_owner->>'can_checkin')::boolean IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'Expected can_checkin=true, got: %', verify_owner;
  END IF;

  -- E) First commit_checkin should succeed and not be marked as already checked in
  commit_once := public.commit_checkin(event_id, issued_ticket.id, issued_ticket.qr_secret);
  RAISE NOTICE 'E) first commit result=%', commit_once;

  IF (commit_once->>'ok')::boolean IS DISTINCT FROM true
     OR (commit_once->>'already_checked_in')::boolean IS DISTINCT FROM false THEN
    RAISE EXCEPTION 'Expected first commit ok=true and already_checked_in=false, got: %', commit_once;
  END IF;

  -- F) Second commit_checkin should be idempotent
  commit_twice := public.commit_checkin(event_id, issued_ticket.id, issued_ticket.qr_secret);
  RAISE NOTICE 'F) second commit result=%', commit_twice;

  IF (commit_twice->>'ok')::boolean IS DISTINCT FROM true
     OR (commit_twice->>'already_checked_in')::boolean IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'Expected second commit ok=true and already_checked_in=true, got: %', commit_twice;
  END IF;

  -- G) ATTENDEE tries to register again -> should fail with PER_USER_LIMIT_EXCEEDED
  PERFORM set_config('request.jwt.claim.sub', attendee_uuid::text, true);
  PERFORM set_config('request.jwt.claim.role', 'authenticated', true);

  BEGIN
    PERFORM 1
    FROM public.register_free(ticket_type_id, 1) AS t;
    RAISE EXCEPTION 'Expected PER_USER_LIMIT_EXCEEDED, but register_free succeeded';
  EXCEPTION
    WHEN OTHERS THEN
      IF POSITION('PER_USER_LIMIT_EXCEEDED' IN SQLERRM) > 0 THEN
        RAISE NOTICE 'G) per_user_limit test pass. caught error=%', SQLERRM;
      ELSE
        RAISE EXCEPTION 'Unexpected error in per_user_limit test: %', SQLERRM;
      END IF;
  END;

  RAISE NOTICE 'MVP-1 verify script completed successfully.';
END;
$$;
