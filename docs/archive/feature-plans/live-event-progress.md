# 即時活動進度（Live Event Progress）開發計畫

> **功能目標**：主辦方可即時更新活動進度（海選 → 晉級公布 → 決賽…），參加者在活動頁面即時看到目前比到哪裡，減少「不知道進度」的困擾。

---

## 1. 功能範圍（Scope）

### In-Scope

| 面向 | 功能 |
|------|------|
| 主辦方 | 預設活動階段模板（可自訂）、一鍵切換當前階段、新增/編輯/刪除階段 |
| 主辦方 | 發送階段備註（如「16 強名單已公布」、「休息 15 分鐘」） |
| 參加者 | 活動頁即時顯示當前階段 + 進度條 |
| 參加者 | 階段變更時收到頁面內即時通知（toast） |
| 系統 | Supabase Realtime 推送（基於 PostgreSQL LISTEN/NOTIFY） |

### Out-of-Scope（本次不做）

- 計分/評分系統（獨立功能，見 note.md）
- 選手晉級名單管理（未來可擴展）
- Push notification / Email 通知進度變更
- 歷史回放（進度時間軸回顧）

---

## 2. 技術方案

### 2.1 即時推送技術選型

| 方案 | 優點 | 缺點 | 結論 |
|------|------|------|------|
| **Supabase Realtime** | 零額外基礎建設、前端 SDK 已引入、支援 RLS | 依賴 Supabase 基礎建設 | **採用** |
| SSE (Server-Sent Events) | 單向推送、簡單 | 需 Flask 額外設定、長連線管理 | 不採用 |
| WebSocket (自建) | 雙向、彈性大 | 複雜度高、需額外伺服器 | 不採用 |
| Short Polling | 最簡單 | 延遲高、浪費頻寬 | 備援方案 |

**決策**：使用 **Supabase Realtime** 訂閱 `event_progress` 表變更，前端透過 `supabase.channel()` 監聽。

**備援**：若 Realtime 連線失敗，前端自動降級為 30 秒短輪詢。

### 2.2 資料庫設計

#### 新增表：`event_stages`（活動階段定義）

```sql
CREATE TABLE event_stages (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id    UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,           -- 階段名稱，如「海選」「16 強」「決賽」
  description TEXT,                    -- 階段說明（可選）
  sort_order  INT NOT NULL DEFAULT 0,  -- 排序
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (event_id, sort_order)
);
```

#### 新增表：`event_progress`（活動即時進度）

```sql
CREATE TABLE event_progress (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id         UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  current_stage_id UUID REFERENCES event_stages(id) ON DELETE SET NULL,
  status           TEXT NOT NULL DEFAULT 'not_started'
                   CHECK (status IN ('not_started', 'in_progress', 'paused', 'ended')),
  note             TEXT,               -- 主辦方即時備註，如「休息 15 分鐘」
  updated_by       UUID NOT NULL REFERENCES auth.users(id),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (event_id)  -- 每個活動只有一筆進度記錄
);
```

#### 新增表：`event_progress_log`（進度變更歷史）

```sql
CREATE TABLE event_progress_log (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id    UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  stage_id    UUID REFERENCES event_stages(id) ON DELETE SET NULL,
  status      TEXT NOT NULL,
  note        TEXT,
  changed_by  UUID NOT NULL REFERENCES auth.users(id),
  changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### RLS 政策

```sql
-- event_stages: 公開可讀（已發布活動），主辦方可寫
ALTER TABLE event_stages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read stages of published events"
  ON event_stages FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM events WHERE events.id = event_stages.event_id
    AND events.status = 'published'
  ));

CREATE POLICY "Organizer can manage stages"
  ON event_stages FOR ALL
  USING (EXISTS (
    SELECT 1 FROM organizer_members om
    JOIN events e ON e.org_id = om.org_id
    WHERE e.id = event_stages.event_id
    AND om.user_id = auth.uid()
    AND om.role IN ('owner', 'admin')
  ));

-- event_progress: 公開可讀，主辦方可寫
ALTER TABLE event_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read progress of published events"
  ON event_progress FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM events WHERE events.id = event_progress.event_id
    AND events.status = 'published'
  ));

CREATE POLICY "Organizer can update progress"
  ON event_progress FOR ALL
  USING (EXISTS (
    SELECT 1 FROM organizer_members om
    JOIN events e ON e.org_id = om.org_id
    WHERE e.id = event_progress.event_id
    AND om.user_id = auth.uid()
    AND om.role IN ('owner', 'admin')
  ));

-- event_progress_log: 公開可讀（透明度），僅系統可寫（透過 trigger）
ALTER TABLE event_progress_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read progress log of published events"
  ON event_progress_log FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM events WHERE events.id = event_progress_log.event_id
    AND events.status = 'published'
  ));
```

#### Realtime 啟用

```sql
-- 啟用 event_progress 的 Realtime 廣播
ALTER PUBLICATION supabase_realtime ADD TABLE event_progress;
```

#### 自動記錄歷史 Trigger

```sql
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
```

### 2.3 階段模板（預設）

針對街舞活動常見流程，提供預設模板：

```typescript
const BATTLE_STAGES_TEMPLATE = [
  { title: '報到', description: '選手報到與確認' },
  { title: '海選', description: 'Preliminary rounds' },
  { title: '海選結果公布', description: '晉級名單公布' },
  { title: 'Top 16', description: '16 強淘汰賽' },
  { title: 'Top 8', description: '8 強淘汰賽' },
  { title: 'Top 4 / 準決賽', description: '4 強準決賽' },
  { title: '決賽', description: 'Final battle' },
  { title: '頒獎', description: '頒獎典禮' },
  { title: '活動結束', description: '' },
]
```

主辦方可在此基礎上自訂（新增、刪除、改名、調整順序）。

---

## 3. API 設計

### 3.1 主辦方端 API

#### 階段管理

```
# 取得活動階段列表
GET /api/v1/organizer/events/:event_id/stages
Response: { stages: EventStage[] }

# 批量設定階段（建立/更新/刪除一次完成）
PUT /api/v1/organizer/events/:event_id/stages
Body: { stages: [{ id?, title, description?, sort_order }] }
Response: { stages: EventStage[] }
```

#### 進度控制

```
# 取得當前進度
GET /api/v1/organizer/events/:event_id/progress
Response: { progress: EventProgress, stages: EventStage[] }

# 更新進度（切換階段 / 更新狀態 / 發送備註）
PATCH /api/v1/organizer/events/:event_id/progress
Body: { current_stage_id?, status?, note? }
Response: { progress: EventProgress }

# 取得進度歷史
GET /api/v1/organizer/events/:event_id/progress/log
Response: { log: EventProgressLog[] }
```

### 3.2 參加者端 API

```
# 取得活動進度（含階段列表）— 已包含在 event detail 回傳
GET /api/v1/events/:event_id/progress
Response: { progress: EventProgress | null, stages: EventStage[] }
```

> **即時更新不走 API**：前端直接透過 Supabase Realtime 訂閱 `event_progress` 表變更。

### 3.3 Pydantic Schemas

```python
class EventStageItem(BaseModel):
    id: UUID | None = None
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    sort_order: int = Field(ge=0)

class EventStagesRequest(BaseModel):
    stages: list[EventStageItem] = Field(min_length=1, max_length=30)

class EventProgressUpdate(BaseModel):
    current_stage_id: UUID | None = None
    status: Literal['not_started', 'in_progress', 'paused', 'ended'] | None = None
    note: str | None = Field(default=None, max_length=500)

class EventProgressResponse(BaseModel):
    id: UUID
    event_id: UUID
    current_stage_id: UUID | None
    current_stage_title: str | None  # JOIN 回傳
    status: str
    note: str | None
    updated_at: datetime
    total_stages: int
    current_stage_order: int | None  # 用於前端計算進度百分比
```

---

## 4. 前端設計

### 4.1 參加者視角 — EventDetailView 擴充

在 [EventDetailView.vue](../../frontend/src/views/EventDetailView.vue) 新增即時進度區塊：

```
┌─────────────────────────────────────────┐
│  🔴 LIVE  即時進度                        │
│                                         │
│  ●───●───●───◎───○───○───○              │
│  報到  海選  結果  Top16 Top8 決賽  頒獎    │
│                    ↑ 目前                │
│                                         │
│  📌 目前階段：Top 16                      │
│  💬 主辦方備註：第三輪進行中，預計 15:30 結束 │
│  🕐 更新於 14:52                         │
└─────────────────────────────────────────┘
```

**元件設計**：

```
frontend/src/components/
  └── LiveProgressBar.vue    -- 即時進度條元件（可複用）
```

**功能**：
- 進度條以圓點 + 連線呈現各階段，已完成階段填色，當前階段高亮動畫
- 顯示主辦方即時備註
- 活動狀態為 `in_progress` 時顯示 LIVE 標籤（紅色脈動動畫）
- 活動狀態為 `paused` 時顯示「暫停中」
- `not_started` 時顯示「活動尚未開始」
- `ended` 時顯示「活動已結束」，進度條全部填滿
- Supabase Realtime 訂閱，收到更新時自動刷新 + toast 提示

**Realtime 訂閱邏輯**：

```typescript
// composables/useEventProgress.ts
import { supabase } from '@/api/supabase'

export function useEventProgress(eventId: string) {
  const progress = ref<EventProgress | null>(null)
  const stages = ref<EventStage[]>([])

  // 初始載入
  async function fetchProgress() {
    const res = await api.fetchEventProgress(eventId)
    progress.value = res.progress
    stages.value = res.stages
  }

  // Realtime 訂閱
  const channel = supabase
    .channel(`event-progress-${eventId}`)
    .on(
      'postgres_changes',
      {
        event: 'UPDATE',
        schema: 'public',
        table: 'event_progress',
        filter: `event_id=eq.${eventId}`,
      },
      (payload) => {
        progress.value = mapPayload(payload.new)
        showToast(`活動進度更新：${payload.new.note || '階段已切換'}`)
      }
    )
    .subscribe()

  // 備援：Realtime 失敗時降級為短輪詢
  let pollTimer: ReturnType<typeof setInterval> | null = null

  function startFallbackPolling() {
    pollTimer = setInterval(fetchProgress, 30_000)
  }

  function stopFallbackPolling() {
    if (pollTimer) clearInterval(pollTimer)
  }

  onMounted(() => {
    fetchProgress()
    // 監控 Realtime 連線狀態
    channel.on('system', { event: 'disconnect' }, () => {
      startFallbackPolling()
    })
    channel.on('system', { event: 'reconnect' }, () => {
      stopFallbackPolling()
      fetchProgress() // 重連後立即同步
    })
  })

  onUnmounted(() => {
    supabase.removeChannel(channel)
    stopFallbackPolling()
  })

  return { progress, stages }
}
```

### 4.2 主辦方視角 — 進度控制面板

新增頁面或在現有 OrganizerEventView 加入 tab：

```
frontend/src/views/organizer/
  └── OrganizerProgressView.vue   -- 進度控制面板
```

**UI 設計**：

```
┌──────────────────────────────────────────────┐
│  活動進度控制台                                │
│                                              │
│  狀態：[未開始] [進行中✓] [暫停] [已結束]       │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ ✅ 報到          [已完成]             │    │
│  │ ✅ 海選          [已完成]             │    │
│  │ ✅ 海選結果公布    [已完成]             │    │
│  │ 🔵 Top 16        [← 目前] [切換到此]  │    │
│  │ ○ Top 8                              │    │
│  │ ○ 決賽                               │    │
│  │ ○ 頒獎                               │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  備註（會即時顯示給參加者）：                    │
│  ┌──────────────────────────────────────┐    │
│  │ 第三輪進行中，預計 15:30 結束          │    │
│  └──────────────────────────────────────┘    │
│  [更新備註]                                   │
│                                              │
│  ── 變更歷史 ──                               │
│  14:52  切換至 Top 16                        │
│  14:50  備註：16 強名單已公布                  │
│  13:00  切換至 海選結果公布                    │
│  ...                                         │
└──────────────────────────────────────────────┘
```

**功能**：
- 一鍵切換當前階段（點擊「切換到此」）
- 狀態切換（未開始/進行中/暫停/結束）
- 輸入即時備註，送出後參加者立即看到
- 變更歷史（從 `event_progress_log` 載入）
- 階段管理（新增/編輯/刪除/拖曳排序），在活動編輯頁設定

---

## 5. 實作計畫

### Phase 1：資料庫與後端基礎（Day 1-2）

| 步驟 | 任務 | 檔案 |
|------|------|------|
| 1.1 | 撰寫 migration：建立 `event_stages`、`event_progress`、`event_progress_log` 表 + RLS + Trigger + Realtime | `supabase/migrations/0028_live_progress.sql` |
| 1.2 | 新增 Pydantic schemas | `backend/app/domain/schemas.py` |
| 1.3 | 新增 `progress_service.py`：階段 CRUD、進度更新、歷史查詢 | `backend/app/services/progress_service.py` |
| 1.4 | 新增 Blueprint 路由（主辦方 + 公開） | `backend/app/blueprints/progress.py` |
| 1.5 | 註冊 Blueprint 到 Flask app | `backend/app/__init__.py` |
| 1.6 | 更新 `get_public_event_detail` 回傳加入 progress + stages | `backend/app/services/events_service.py` |

### Phase 2：前端參加者視角（Day 3-4）

| 步驟 | 任務 | 檔案 |
|------|------|------|
| 2.1 | 新增 API client 方法 | `frontend/src/api/client.ts` |
| 2.2 | 實作 `useEventProgress` composable（Realtime + fallback） | `frontend/src/composables/useEventProgress.ts` |
| 2.3 | 實作 `LiveProgressBar.vue` 元件 | `frontend/src/components/LiveProgressBar.vue` |
| 2.4 | 整合到 `EventDetailView.vue` | `frontend/src/views/EventDetailView.vue` |
| 2.5 | TailwindCSS 動畫：LIVE 脈動、階段高亮 | 同上 |

### Phase 3：前端主辦方控制台（Day 5-6）

| 步驟 | 任務 | 檔案 |
|------|------|------|
| 3.1 | 實作 `OrganizerProgressView.vue`（進度控制面板） | `frontend/src/views/organizer/OrganizerProgressView.vue` |
| 3.2 | 階段管理 UI（在活動編輯頁加入階段設定區塊） | `frontend/src/views/organizer/OrganizerEventView.vue` |
| 3.3 | 新增路由 | `frontend/src/router/index.ts` |
| 3.4 | 階段模板選擇器（Battle / Workshop / Jam 預設模板） | 同 3.1 |

### Phase 4：測試與驗證（Day 7-8）

（詳見下方第 6、7 節）

---

## 6. 測試計畫

### 6.1 Backend Unit Tests

| 測試檔案 | 測試項目 |
|----------|----------|
| `test_progress_service.py` | 建立/更新/刪除階段 |
| | 更新進度（切換階段、更新狀態、發送備註） |
| | 進度自動記錄歷史 |
| | 權限驗證：非主辦方不可更新進度 |
| | 邊界：活動不存在、階段不屬於該活動 |
| | 狀態機：不合法狀態轉換（如 ended → in_progress） |
| `test_progress_blueprint.py` | API endpoint 回傳格式正確 |
| | 認證與授權（無 JWT / 非主辦方 / 主辦方） |
| | 輸入驗證（Pydantic 錯誤處理） |
| | 公開 API 回傳進度 |

### 6.2 Backend Integration Tests

| 測試項目 | 說明 |
|----------|------|
| 完整流程 | 建立階段 → 開始活動 → 逐步切換 → 結束，驗證歷史記錄 |
| RLS 驗證 | 匿名使用者可讀、非主辦方不可寫 |
| Realtime 觸發 | 更新 `event_progress` 後確認 trigger 寫入 log |
| 與現有功能整合 | `get_public_event_detail` 正確回傳 progress |

### 6.3 Frontend Tests

| 測試項目 | 說明 |
|----------|------|
| `LiveProgressBar` 渲染 | 各狀態下正確渲染（未開始/進行中/暫停/結束） |
| 進度百分比計算 | 確認 current_stage_order / total_stages 計算正確 |
| Realtime 模擬 | mock Supabase channel，驗證 payload → UI 更新 |
| Fallback polling | 模擬 Realtime 斷線 → 啟動輪詢 → 重連後停止 |
| 主辦方控制台 | 切換階段、更新備註、狀態切換互動測試 |

### 6.4 E2E / 手動驗證場景

| # | 場景 | 預期結果 |
|---|------|----------|
| 1 | 主辦方建立活動並設定 5 個階段 | 階段列表正確顯示，排序正確 |
| 2 | 主辦方將狀態改為「進行中」並設定第一階段 | 參加者頁面即時出現 LIVE 標籤 + 進度條 |
| 3 | 主辦方切換到下一階段 | 參加者頁面進度條自動更新 + toast 通知 |
| 4 | 主辦方發送備註「休息 15 分鐘」 | 參加者頁面即時顯示備註 |
| 5 | 主辦方暫停活動 | 參加者看到「暫停中」狀態 |
| 6 | 主辦方結束活動 | 進度條全滿，顯示「活動已結束」 |
| 7 | 參加者斷網後重連 | 自動同步最新進度 |
| 8 | 活動尚未設定進度 | 活動頁不顯示進度區塊（graceful fallback） |
| 9 | 多個參加者同時觀看 | 所有人同步收到更新 |

---

## 7. 驗證清單（Definition of Done）

### 7.1 程式碼品質

- [ ] `cd backend && ruff check . && ruff format --check .` 通過
- [ ] `cd backend && pytest -q` 全部通過（含新增測試）
- [ ] `cd frontend && npm run build` 通過
- [ ] Migration 可乾淨套用（`supabase db reset` 無錯誤）
- [ ] 無 secrets 被 commit

### 7.2 功能驗收

- [ ] 主辦方可建立/編輯/刪除活動階段
- [ ] 主辦方可使用預設模板快速建立階段
- [ ] 主辦方可切換當前階段（一鍵操作）
- [ ] 主辦方可更新活動狀態（未開始/進行中/暫停/結束）
- [ ] 主辦方可發送即時備註
- [ ] 主辦方可查看進度變更歷史
- [ ] 參加者在活動頁看到即時進度條
- [ ] 參加者在進度更新時收到 toast 通知（無需手動重整）
- [ ] Realtime 斷線時自動降級為短輪詢
- [ ] Realtime 重連後自動同步最新狀態
- [ ] 未設定進度的活動不顯示進度區塊
- [ ] 手機版（RWD）進度條正常顯示

### 7.3 安全性

- [ ] RLS 政策正確：公開可讀、僅主辦方可寫
- [ ] API 認證：需 `@require_auth` + 主辦方身份驗證
- [ ] `user_id` 從 JWT 解析，不信任 client
- [ ] 輸入驗證：Pydantic schema 驗證所有輸入
- [ ] 備註欄位 XSS 防護（前端 escape、限制長度）

### 7.4 效能

- [ ] Realtime 訂閱正確清理（`onUnmounted` 取消訂閱）
- [ ] 避免不必要的 re-render（`computed` / `watch` 最佳化）
- [ ] Progress log 查詢有索引（`event_id` + `changed_at`）

---

## 8. 檔案變更總覽

### 新增檔案

| 檔案 | 說明 |
|------|------|
| `supabase/migrations/0028_live_progress.sql` | DB schema + RLS + Trigger + Realtime |
| `backend/app/services/progress_service.py` | 進度業務邏輯 |
| `backend/app/blueprints/progress.py` | 進度 API 路由 |
| `backend/app/tests/test_progress_service.py` | Service 層測試 |
| `backend/app/tests/test_progress_blueprint.py` | API 層測試 |
| `frontend/src/composables/useEventProgress.ts` | Realtime + fallback composable |
| `frontend/src/components/LiveProgressBar.vue` | 即時進度條元件 |
| `frontend/src/views/organizer/OrganizerProgressView.vue` | 主辦方控制面板 |

### 修改檔案

| 檔案 | 變更 |
|------|------|
| `backend/app/__init__.py` | 註冊 progress Blueprint |
| `backend/app/domain/schemas.py` | 新增 Progress 相關 schemas |
| `backend/app/services/events_service.py` | event detail 回傳加入 progress |
| `frontend/src/api/client.ts` | 新增 progress API 方法 + types |
| `frontend/src/views/EventDetailView.vue` | 整合 LiveProgressBar |
| `frontend/src/views/organizer/OrganizerEventView.vue` | 階段設定 UI |
| `frontend/src/router/index.ts` | 新增主辦方進度控制路由 |

---

## 9. 風險與注意事項

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| Supabase Realtime 免費方案限制 | 同時連線數有上限（200 concurrent） | 大型活動需評估升級方案；備援短輪詢 |
| 主辦方誤操作切換階段 | 參加者收到錯誤進度 | 切換前加確認 dialog；歷史記錄可追溯 |
| 備註欄位被濫用 | XSS 或不當內容 | 前端 escape + 長度限制 500 字 |
| 離線參加者錯過更新 | 重新上線後進度不同步 | 重連後自動 fetch 最新狀態 |
| Migration 與現有 schema 衝突 | 部署失敗 | 本地 `supabase db reset` 先驗證 |

---

## 10. 未來擴展（不在本次範圍）

- **選手晉級名單管理**：與進度系統整合，公布晉級名單
- **計分系統**：評審打分 → 自動排名 → 公布結果
- **Push notification**：進度變更時推送通知到手機
- **進度時間軸回放**：活動結束後回顧各階段時間線
- **觀眾互動**：投票、留言、即時反應
