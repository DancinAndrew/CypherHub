BEGIN;

CREATE TABLE IF NOT EXISTS public.event_internal_notes (
  event_id uuid PRIMARY KEY REFERENCES public.events(id) ON DELETE CASCADE,
  note text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by uuid NULL
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'event_internal_notes_updated_by_fkey'
      AND table_name = 'event_internal_notes'
  ) THEN
    ALTER TABLE public.event_internal_notes
      ADD CONSTRAINT event_internal_notes_updated_by_fkey
      FOREIGN KEY (updated_by) REFERENCES auth.users(id) ON DELETE SET NULL;
  END IF;
END$$;

DROP TRIGGER IF EXISTS set_event_internal_notes_updated_at ON public.event_internal_notes;
CREATE TRIGGER set_event_internal_notes_updated_at
BEFORE UPDATE ON public.event_internal_notes
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.event_internal_notes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "event_internal_notes_select_member" ON public.event_internal_notes;
CREATE POLICY "event_internal_notes_select_member"
ON public.event_internal_notes
FOR SELECT
TO authenticated
USING (public.is_event_member(event_id));

DROP POLICY IF EXISTS "event_internal_notes_insert_admin" ON public.event_internal_notes;
CREATE POLICY "event_internal_notes_insert_admin"
ON public.event_internal_notes
FOR INSERT
TO authenticated
WITH CHECK (public.is_event_admin(event_id));

DROP POLICY IF EXISTS "event_internal_notes_update_admin" ON public.event_internal_notes;
CREATE POLICY "event_internal_notes_update_admin"
ON public.event_internal_notes
FOR UPDATE
TO authenticated
USING (public.is_event_admin(event_id))
WITH CHECK (public.is_event_admin(event_id));

COMMIT;
