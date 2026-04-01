-- ============================================================
-- 0028_live_progress.sql
-- 即時活動進度：event_stages / event_progress / event_progress_log
-- ============================================================

-- 1. event_stages: 活動階段定義
CREATE TABLE event_stages (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id    UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  description TEXT,
  sort_order  INT NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (event_id, sort_order)
);

-- 2. event_progress: 活動即時進度（每個活動一筆）
CREATE TABLE event_progress (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id         UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  current_stage_id UUID REFERENCES event_stages(id) ON DELETE SET NULL,
  status           TEXT NOT NULL DEFAULT 'not_started'
                   CHECK (status IN ('not_started', 'in_progress', 'paused', 'ended')),
  note             TEXT,
  updated_by       UUID NOT NULL,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (event_id)
);

-- 3. event_progress_log: 進度變更歷史
CREATE TABLE event_progress_log (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id    UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  stage_id    UUID REFERENCES event_stages(id) ON DELETE SET NULL,
  status      TEXT NOT NULL,
  note        TEXT,
  changed_by  UUID NOT NULL,
  changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_progress_log_event_changed
  ON event_progress_log (event_id, changed_at DESC);

-- ============================================================
-- RLS
-- ============================================================

ALTER TABLE event_stages ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_progress_log ENABLE ROW LEVEL SECURITY;

-- event_stages: 公開可讀（已發布活動）
CREATE POLICY "Anyone can read stages of published events"
  ON event_stages FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM events
    WHERE events.id = event_stages.event_id
      AND events.status = 'published'
  ));

-- event_stages: 主辦方 owner/admin 可管理
CREATE POLICY "Organizer admin can manage stages"
  ON event_stages FOR ALL
  USING (EXISTS (
    SELECT 1 FROM organizer_members om
    JOIN events e ON e.org_id = om.org_id
    WHERE e.id = event_stages.event_id
      AND om.user_id = auth.uid()
      AND om.role IN ('owner', 'admin')
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM organizer_members om
    JOIN events e ON e.org_id = om.org_id
    WHERE e.id = event_stages.event_id
      AND om.user_id = auth.uid()
      AND om.role IN ('owner', 'admin')
  ));

-- event_progress: 公開可讀（已發布活動）
CREATE POLICY "Anyone can read progress of published events"
  ON event_progress FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM events
    WHERE events.id = event_progress.event_id
      AND events.status = 'published'
  ));

-- event_progress: 主辦方 owner/admin 可管理
CREATE POLICY "Organizer admin can manage progress"
  ON event_progress FOR ALL
  USING (EXISTS (
    SELECT 1 FROM organizer_members om
    JOIN events e ON e.org_id = om.org_id
    WHERE e.id = event_progress.event_id
      AND om.user_id = auth.uid()
      AND om.role IN ('owner', 'admin')
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM organizer_members om
    JOIN events e ON e.org_id = om.org_id
    WHERE e.id = event_progress.event_id
      AND om.user_id = auth.uid()
      AND om.role IN ('owner', 'admin')
  ));

-- event_progress_log: 公開可讀（已發布活動）
CREATE POLICY "Anyone can read progress log of published events"
  ON event_progress_log FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM events
    WHERE events.id = event_progress_log.event_id
      AND events.status = 'published'
  ));

-- event_progress_log: 僅透過 trigger 寫入（SECURITY DEFINER function）
-- 不需要 INSERT policy for regular users

-- ============================================================
-- Trigger: 自動記錄進度變更歷史
-- ============================================================

CREATE OR REPLACE FUNCTION log_progress_change()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO event_progress_log (event_id, stage_id, status, note, changed_by)
  VALUES (NEW.event_id, NEW.current_stage_id, NEW.status, NEW.note, NEW.updated_by);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_log_progress_change
  AFTER INSERT OR UPDATE ON event_progress
  FOR EACH ROW EXECUTE FUNCTION log_progress_change();

-- ============================================================
-- Realtime: 啟用 event_progress 即時推送
-- ============================================================

ALTER PUBLICATION supabase_realtime ADD TABLE event_progress;
