-- 允許在「該主辦方有已上架活動」時，公開讀取主辦方基本資訊（活動詳情頁主辦方區塊用）
BEGIN;

DROP POLICY IF EXISTS "org_select_public_via_published_event" ON public.organizations;
CREATE POLICY "org_select_public_via_published_event"
ON public.organizations
FOR SELECT
TO anon, authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.events e
    WHERE e.org_id = organizations.id AND e.status = 'published'
  )
);

COMMIT;
