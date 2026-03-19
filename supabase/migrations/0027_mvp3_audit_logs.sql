-- MVP-3.4: audit_logs 表，平台治理與關鍵操作追蹤
-- mvp3-master-plan 五.2

BEGIN;

CREATE TABLE IF NOT EXISTS public.audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_type text NOT NULL CHECK (actor_type IN ('admin', 'organizer', 'system')),
  actor_id uuid NULL,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id uuid NULL,
  details jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON public.audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON public.audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON public.audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action);

-- 僅後端 service_role 寫入，不開放 authenticated；無 RLS policy 則 deny
-- service_role bypass RLS

COMMIT;
