BEGIN;

ALTER TABLE public.events
  ADD COLUMN IF NOT EXISTS short_desc text,
  ADD COLUMN IF NOT EXISTS registration_start_at timestamptz,
  ADD COLUMN IF NOT EXISTS registration_end_at timestamptz,
  ADD COLUMN IF NOT EXISTS map_url text,
  ADD COLUMN IF NOT EXISTS contact_email text,
  ADD COLUMN IF NOT EXISTS contact_phone text,
  ADD COLUMN IF NOT EXISTS socials jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS eligibility text,
  ADD COLUMN IF NOT EXISTS event_language text,
  ADD COLUMN IF NOT EXISTS checkin_open_at timestamptz,
  ADD COLUMN IF NOT EXISTS checkin_note text,
  ADD COLUMN IF NOT EXISTS schedule jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_events_reg_end ON public.events(registration_end_at);
CREATE INDEX IF NOT EXISTS idx_events_reg_start ON public.events(registration_start_at);

COMMIT;
