BEGIN;

ALTER TABLE public.event_forms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ticket_form_responses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "event_forms_select_public_active" ON public.event_forms;
CREATE POLICY "event_forms_select_public_active"
ON public.event_forms
FOR SELECT
TO anon, authenticated
USING (
  is_active = true
  AND EXISTS (
    SELECT 1
    FROM public.events e
    WHERE e.id = event_id
      AND e.status = 'published'
  )
  AND (
    ticket_type_id IS NULL
    OR EXISTS (
      SELECT 1
      FROM public.ticket_types tt
      WHERE tt.id = ticket_type_id
        AND tt.is_active = true
    )
  )
);

DROP POLICY IF EXISTS "event_forms_select_org_member" ON public.event_forms;
CREATE POLICY "event_forms_select_org_member"
ON public.event_forms
FOR SELECT
TO authenticated
USING (public.is_event_member(event_id));

DROP POLICY IF EXISTS "event_forms_insert_admin" ON public.event_forms;
CREATE POLICY "event_forms_insert_admin"
ON public.event_forms
FOR INSERT
TO authenticated
WITH CHECK (public.is_event_admin(event_id));

DROP POLICY IF EXISTS "event_forms_update_admin" ON public.event_forms;
CREATE POLICY "event_forms_update_admin"
ON public.event_forms
FOR UPDATE
TO authenticated
USING (public.is_event_admin(event_id))
WITH CHECK (public.is_event_admin(event_id));

DROP POLICY IF EXISTS "ticket_form_responses_select_own" ON public.ticket_form_responses;
CREATE POLICY "ticket_form_responses_select_own"
ON public.ticket_form_responses
FOR SELECT
TO authenticated
USING (user_id = auth.uid());

DROP POLICY IF EXISTS "ticket_form_responses_select_org_member" ON public.ticket_form_responses;
CREATE POLICY "ticket_form_responses_select_org_member"
ON public.ticket_form_responses
FOR SELECT
TO authenticated
USING (public.is_event_member(event_id));

COMMIT;
