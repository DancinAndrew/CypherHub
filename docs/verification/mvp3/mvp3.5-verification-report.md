# MVP-3.5 使用者端擴充驗證報告

> 對應 mvp3-master-plan.md 第六節。熱門活動、活動提醒、異動/取消通知。

---

## 一、熱門活動

| 項目 | 驗證 | 備註 |
|------|------|------|
| GET /events?sort=hot | ✅ | 依 ticket_types.sold_count 總和排序，同 sold 則依 start_at |
| total_sold_count 回傳 | ✅ | sort=hot 時每筆 event 含 total_sold_count |
| 前端「依時間」/「熱門」tab | ✅ | HomeView sortMode、setSortMode |
| 熱門 badge | ✅ | sortMode=hot 且 total_sold_count>0 時顯示「熱門 · N 人報名」 |

---

## 二、活動提醒 Email

| 項目 | 驗證 | 備註 |
|------|------|------|
| POST /internal/jobs/event-reminders | ✅ | 需 X-Cron-Secret header |
| 無 secret → 401 | ✅ | test_jobs_blueprint |
| 前一天窗口 23–25h | ✅ | process_events(day_lo, day_hi, "1_day") |
| 前一小時窗口 55–65min | ✅ | process_events(hour_lo, hour_hi, "1_hour") |
| 回傳 {1_day, 1_hour} | ✅ | 各窗口寄送數量 |
| Cron 設定 | 文件 | 由 Render Cron、cron-job.org 等每 15 分鐘呼叫 |

---

## 三、活動異動/取消通知

| 項目 | 驗證 | 備註 |
|------|------|------|
| Admin 下架 (status=disabled/cancelled) | ✅ | admin_update_event_status → notify_event_cancelled |
| 主辦方改 status 為 cancelled | ✅ | update_event 偵測 → notify_event_cancelled |
| 主辦方修改 start_at/end_at | ✅ | update_event 偵測 → notify_event_time_changed |
| 參加者 Email 來源 | ✅ | auth.users 優先，fallback ticket_form_responses |

---

## 四、測試覆蓋

| 檔案 | 說明 |
|------|------|
| test_events_filters.py | sort=hot 傳遞、sort 無效值忽略 |
| test_event_notification_service.py | run_event_reminders 回傳格式、notify_event_cancelled 寄信 |
| test_jobs_blueprint.py | 401 無 secret、200 有 secret |

---

## 五、檔案清單

| 類型 | 檔案 |
|------|------|
| Backend service | events_service (sort, notify 鈎子), event_notification_service, email_service |
| Backend blueprint | events (sort param), jobs (event-reminders) |
| Backend config | config.CRON_SECRET |
| Frontend | HomeView (sort tabs, badge), client.fetchEvents(sort) |
| Schema | EventResponse.total_sold_count |
| Docs | mvp3-master-plan §6, develop.md MVP-3.5 |
