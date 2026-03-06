BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dance_style') THEN
    CREATE TYPE public.dance_style AS ENUM (
      'hiphop','popping','locking','house','waacking','breaking','krump','voguing','freestyle','choreo','allstyle'
    );
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_type') THEN
    CREATE TYPE public.event_type AS ENUM (
      'cypher','battle','group_battle','workshop','jam','showcase','audition','party'
    );
  END IF;
END$$;

ALTER TABLE public.events
  ADD COLUMN IF NOT EXISTS dance_styles public.dance_style[] NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS event_types  public.event_type[]  NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_events_dance_styles_gin
  ON public.events USING GIN (dance_styles);

CREATE INDEX IF NOT EXISTS idx_events_event_types_gin
  ON public.events USING GIN (event_types);

COMMIT;
