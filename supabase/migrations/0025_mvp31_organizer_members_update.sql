-- MVP-3.1: organizer_members 需 UPDATE policy，供 PATCH /organizer/organizations/:orgId/members/:userId 改 role 使用。

BEGIN;

DROP POLICY IF EXISTS "org_members_update_admin" ON public.organizer_members;
CREATE POLICY "org_members_update_admin"
ON public.organizer_members
FOR UPDATE
TO authenticated
USING (public.is_org_admin(org_id))
WITH CHECK (public.is_org_admin(org_id));

COMMIT;
