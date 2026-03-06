BEGIN;

-- Helper functions for policies (use SECURITY DEFINER, stable)
CREATE OR REPLACE FUNCTION public.is_org_member(p_org_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.organizer_members m
    WHERE m.org_id = p_org_id
      AND m.user_id = auth.uid()
  );
$$;

CREATE OR REPLACE FUNCTION public.is_org_admin(p_org_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.organizer_members m
    WHERE m.org_id = p_org_id
      AND m.user_id = auth.uid()
      AND m.role IN ('owner','admin')
  );
$$;

CREATE OR REPLACE FUNCTION public.is_event_member(p_event_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.events e
    JOIN public.organizer_members m ON m.org_id = e.org_id
    WHERE e.id = p_event_id
      AND m.user_id = auth.uid()
  );
$$;

CREATE OR REPLACE FUNCTION public.is_event_admin(p_event_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.events e
    JOIN public.organizer_members m ON m.org_id = e.org_id
    WHERE e.id = p_event_id
      AND m.user_id = auth.uid()
      AND m.role IN ('owner','admin')
  );
$$;

-- Enable RLS on all exposed tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizer_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_media ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ticket_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;

-- PROFILES
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own"
ON public.profiles
FOR SELECT
TO authenticated
USING (id = auth.uid());

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own"
ON public.profiles
FOR UPDATE
TO authenticated
USING (id = auth.uid())
WITH CHECK (id = auth.uid());

-- Optional: allow insert own profile (if you need)
-- (If you have auth trigger to create profile, you can omit this)
DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
CREATE POLICY "profiles_insert_own"
ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK (id = auth.uid());

-- ORGANIZATIONS
DROP POLICY IF EXISTS "org_select_member" ON public.organizations;
CREATE POLICY "org_select_member"
ON public.organizations
FOR SELECT
TO authenticated
USING (public.is_org_member(id) OR owner_user_id = auth.uid());

DROP POLICY IF EXISTS "org_insert_owner" ON public.organizations;
CREATE POLICY "org_insert_owner"
ON public.organizations
FOR INSERT
TO authenticated
WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "org_update_owner_admin" ON public.organizations;
CREATE POLICY "org_update_owner_admin"
ON public.organizations
FOR UPDATE
TO authenticated
USING (public.is_org_admin(id) OR owner_user_id = auth.uid())
WITH CHECK (public.is_org_admin(id) OR owner_user_id = auth.uid());

-- ORGANIZER_MEMBERS
DROP POLICY IF EXISTS "org_members_select_self_or_admin" ON public.organizer_members;
CREATE POLICY "org_members_select_self_or_admin"
ON public.organizer_members
FOR SELECT
TO authenticated
USING (user_id = auth.uid() OR public.is_org_admin(org_id));

-- MVP-1：成員管理可以先不開（避免越權）；若要開，僅 owner/admin 可 insert/delete
DROP POLICY IF EXISTS "org_members_insert_admin" ON public.organizer_members;
CREATE POLICY "org_members_insert_admin"
ON public.organizer_members
FOR INSERT
TO authenticated
WITH CHECK (public.is_org_admin(org_id));

DROP POLICY IF EXISTS "org_members_delete_admin" ON public.organizer_members;
CREATE POLICY "org_members_delete_admin"
ON public.organizer_members
FOR DELETE
TO authenticated
USING (public.is_org_admin(org_id));

-- EVENTS
DROP POLICY IF EXISTS "events_select_published_public" ON public.events;
CREATE POLICY "events_select_published_public"
ON public.events
FOR SELECT
TO anon, authenticated
USING (status = 'published');

DROP POLICY IF EXISTS "events_select_org_members" ON public.events;
CREATE POLICY "events_select_org_members"
ON public.events
FOR SELECT
TO authenticated
USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS "events_insert_org_admin" ON public.events;
CREATE POLICY "events_insert_org_admin"
ON public.events
FOR INSERT
TO authenticated
WITH CHECK (public.is_org_admin(org_id));

DROP POLICY IF EXISTS "events_update_org_admin" ON public.events;
CREATE POLICY "events_update_org_admin"
ON public.events
FOR UPDATE
TO authenticated
USING (public.is_org_admin(org_id))
WITH CHECK (public.is_org_admin(org_id));

-- EVENT_MEDIA
DROP POLICY IF EXISTS "event_media_select_public" ON public.event_media;
CREATE POLICY "event_media_select_public"
ON public.event_media
FOR SELECT
TO anon, authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.events e
    WHERE e.id = event_id AND e.status = 'published'
  )
);

DROP POLICY IF EXISTS "event_media_select_org" ON public.event_media;
CREATE POLICY "event_media_select_org"
ON public.event_media
FOR SELECT
TO authenticated
USING (public.is_event_member(event_id));

DROP POLICY IF EXISTS "event_media_mutate_admin" ON public.event_media;
CREATE POLICY "event_media_mutate_admin"
ON public.event_media
FOR ALL
TO authenticated
USING (public.is_event_admin(event_id))
WITH CHECK (public.is_event_admin(event_id));

-- TICKET_TYPES
DROP POLICY IF EXISTS "ticket_types_select_public" ON public.ticket_types;
CREATE POLICY "ticket_types_select_public"
ON public.ticket_types
FOR SELECT
TO anon, authenticated
USING (
  is_active = true AND EXISTS (
    SELECT 1 FROM public.events e
    WHERE e.id = event_id AND e.status = 'published'
  )
);

DROP POLICY IF EXISTS "ticket_types_select_org" ON public.ticket_types;
CREATE POLICY "ticket_types_select_org"
ON public.ticket_types
FOR SELECT
TO authenticated
USING (public.is_event_member(event_id));

DROP POLICY IF EXISTS "ticket_types_mutate_admin" ON public.ticket_types;
CREATE POLICY "ticket_types_mutate_admin"
ON public.ticket_types
FOR ALL
TO authenticated
USING (public.is_event_admin(event_id))
WITH CHECK (public.is_event_admin(event_id));

-- TICKETS
-- User can read own tickets
DROP POLICY IF EXISTS "tickets_select_own" ON public.tickets;
CREATE POLICY "tickets_select_own"
ON public.tickets
FOR SELECT
TO authenticated
USING (user_id = auth.uid());

-- Organizer members can read tickets for their event (attendees list)
DROP POLICY IF EXISTS "tickets_select_event_members" ON public.tickets;
CREATE POLICY "tickets_select_event_members"
ON public.tickets
FOR SELECT
TO authenticated
USING (public.is_event_member(event_id));

-- IMPORTANT:
-- Do NOT create UPDATE/INSERT policies for tickets in MVP-1.
-- Tickets are created/updated ONLY via RPC (SECURITY DEFINER).
-- This prevents clients from forging check-in or creating tickets directly.

COMMIT;
