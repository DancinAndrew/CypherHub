BEGIN;

CREATE TABLE IF NOT EXISTS public.event_forms (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
  ticket_type_id uuid NULL REFERENCES public.ticket_types(id) ON DELETE CASCADE,
  schema jsonb NOT NULL,
  version int NOT NULL DEFAULT 1,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_forms_event ON public.event_forms(event_id);
CREATE INDEX IF NOT EXISTS idx_event_forms_ticket_type ON public.event_forms(ticket_type_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_forms_active_event_level_unique
  ON public.event_forms(event_id)
  WHERE is_active = true AND ticket_type_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_forms_active_ticket_type_unique
  ON public.event_forms(ticket_type_id)
  WHERE is_active = true AND ticket_type_id IS NOT NULL;

DROP TRIGGER IF EXISTS set_event_forms_updated_at ON public.event_forms;
CREATE TRIGGER set_event_forms_updated_at
BEFORE UPDATE ON public.event_forms
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.ticket_form_responses (
  ticket_id uuid PRIMARY KEY REFERENCES public.tickets(id) ON DELETE CASCADE,
  event_id uuid NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
  ticket_type_id uuid NOT NULL REFERENCES public.ticket_types(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  form_id uuid NOT NULL REFERENCES public.event_forms(id) ON DELETE RESTRICT,
  answers jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_responses_event ON public.ticket_form_responses(event_id);
CREATE INDEX IF NOT EXISTS idx_responses_user ON public.ticket_form_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_responses_ticket_type ON public.ticket_form_responses(ticket_type_id);

COMMIT;
