BEGIN;

-- 1) extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2) enums (或用 text + check constraint 也可；建議 enum)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'organizer_role') THEN
    CREATE TYPE public.organizer_role AS ENUM ('owner', 'admin', 'staff');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_status') THEN
    CREATE TYPE public.event_status AS ENUM ('draft', 'published', 'cancelled', 'ended');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ticket_status') THEN
    CREATE TYPE public.ticket_status AS ENUM ('issued', 'checked_in', 'cancelled');
  END IF;
END$$;

-- 3) helper trigger function for updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- 4) tables

-- profiles (linked to auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY,
  display_name text NOT NULL,
  avatar_url text NULL,
  phone text NULL,
  social_links jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Optional FK to auth.users (keep if you want strict link)
-- 注意：若你用 FK，verify 腳本請用真實 auth user id
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'profiles_id_fkey'
      AND table_name = 'profiles'
  ) THEN
    ALTER TABLE public.profiles
      ADD CONSTRAINT profiles_id_fkey
      FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;
END$$;

DROP TRIGGER IF EXISTS set_profiles_updated_at ON public.profiles;
CREATE TRIGGER set_profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- organizations
CREATE TABLE IF NOT EXISTS public.organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text NULL,
  logo_url text NULL,
  contact_email text NULL,
  owner_user_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_org_owner ON public.organizations(owner_user_id);

DROP TRIGGER IF EXISTS set_organizations_updated_at ON public.organizations;
CREATE TRIGGER set_organizations_updated_at
BEFORE UPDATE ON public.organizations
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- organizer_members
CREATE TABLE IF NOT EXISTS public.organizer_members (
  org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  role public.organizer_role NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_user ON public.organizer_members(user_id);

-- Optional FK to auth.users for organizer_members.user_id
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'organizer_members_user_id_fkey'
      AND table_name = 'organizer_members'
  ) THEN
    ALTER TABLE public.organizer_members
      ADD CONSTRAINT organizer_members_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;
END$$;

-- events
CREATE TABLE IF NOT EXISTS public.events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  title text NOT NULL,
  description text NULL,
  start_at timestamptz NOT NULL,
  end_at timestamptz NOT NULL,
  timezone text NULL,
  location_name text NULL,
  location_address text NULL,
  rules text NULL,
  refund_policy text NULL,
  status public.event_status NOT NULL DEFAULT 'draft',
  published_at timestamptz NULL,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT events_time_check CHECK (end_at > start_at)
);

CREATE INDEX IF NOT EXISTS idx_events_status_start ON public.events(status, start_at);
CREATE INDEX IF NOT EXISTS idx_events_org ON public.events(org_id);

DROP TRIGGER IF EXISTS set_events_updated_at ON public.events;
CREATE TRIGGER set_events_updated_at
BEFORE UPDATE ON public.events
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- event_media (for carousel images)
CREATE TABLE IF NOT EXISTS public.event_media (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
  path text NOT NULL,
  sort_order int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_media_event ON public.event_media(event_id);

-- ticket_types
CREATE TABLE IF NOT EXISTS public.ticket_types (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text NULL,
  price_cents int NOT NULL DEFAULT 0,
  currency text NOT NULL DEFAULT 'TWD',
  capacity int NOT NULL,
  sold_count int NOT NULL DEFAULT 0,
  per_user_limit int NOT NULL DEFAULT 1,
  sale_start_at timestamptz NULL,
  sale_end_at timestamptz NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ticket_types_capacity_check CHECK (capacity >= 0),
  CONSTRAINT ticket_types_sold_check CHECK (sold_count >= 0 AND sold_count <= capacity),
  CONSTRAINT ticket_types_limit_check CHECK (per_user_limit >= 1)
);

CREATE INDEX IF NOT EXISTS idx_ticket_types_event ON public.ticket_types(event_id);
CREATE INDEX IF NOT EXISTS idx_ticket_types_active ON public.ticket_types(is_active);

DROP TRIGGER IF EXISTS set_ticket_types_updated_at ON public.ticket_types;
CREATE TRIGGER set_ticket_types_updated_at
BEFORE UPDATE ON public.ticket_types
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- tickets
CREATE TABLE IF NOT EXISTS public.tickets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
  ticket_type_id uuid NOT NULL REFERENCES public.ticket_types(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  qr_secret text NOT NULL,
  status public.ticket_status NOT NULL DEFAULT 'issued',
  issued_at timestamptz NOT NULL DEFAULT now(),
  checked_in_at timestamptz NULL,
  checker_id uuid NULL,
  cancelled_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tickets_user ON public.tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_event ON public.tickets(event_id);
CREATE INDEX IF NOT EXISTS idx_tickets_type ON public.tickets(ticket_type_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON public.tickets(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_qr_secret_unique ON public.tickets(qr_secret);

-- Optional FK to auth.users for tickets.user_id / checker_id
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'tickets_user_id_fkey'
      AND table_name = 'tickets'
  ) THEN
    ALTER TABLE public.tickets
      ADD CONSTRAINT tickets_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'tickets_checker_id_fkey'
      AND table_name = 'tickets'
  ) THEN
    ALTER TABLE public.tickets
      ADD CONSTRAINT tickets_checker_id_fkey
      FOREIGN KEY (checker_id) REFERENCES auth.users(id) ON DELETE SET NULL;
  END IF;
END$$;

-- 5) Optional: auto-create organizer_members row for org owner
CREATE OR REPLACE FUNCTION public.handle_new_organization()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.organizer_members(org_id, user_id, role)
  VALUES (NEW.id, NEW.owner_user_id, 'owner')
  ON CONFLICT DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_org_insert_member ON public.organizations;
CREATE TRIGGER trg_org_insert_member
AFTER INSERT ON public.organizations
FOR EACH ROW EXECUTE FUNCTION public.handle_new_organization();

COMMIT;
