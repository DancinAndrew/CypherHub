"""MVP-3.5: 活動提醒與異動通知。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from flask import current_app

from .email_service import email_service
from .supabase_client import supabase_client

UTC = getattr(datetime, "UTC", timezone(timedelta(0)))


class EventNotificationService:
    """活動提醒 job、異動/取消通知。"""

    def get_event_participant_emails(self, event_id: UUID) -> list[tuple[str, str]]:
        """取得活動參加者 (user_id, email) 列表。含 issued/checked_in 票券。
        Email 優先從 auth.users，fallback 從 ticket_form_responses.answers。
        """
        client = supabase_client.service_role_client()
        try:
            resp = (
                client.table("tickets")
                .select("user_id")
                .eq("event_id", str(event_id))
                .in_("status", ["issued", "checked_in"])
                .execute()
            )
            rows = supabase_client.extract_data(resp) or []
            user_ids = list({str(r.get("user_id", "")) for r in rows if r.get("user_id")})

            result: list[tuple[str, str]] = []
            seen_emails: set[str] = set()
            for uid in user_ids:
                email = supabase_client.get_user_email_by_id(uid)
                if email and email.strip().lower() not in seen_emails:
                    seen_emails.add(email.strip().lower())
                    result.append((uid, email.strip()))
            return result
        except Exception as exc:
            current_app.logger.warning(
                "[event_notification] get_event_participant_emails failed event=%s: %s",
                event_id,
                exc,
            )
            return []

    def run_event_reminders(self) -> dict[str, int]:
        """MVP-3.5: 發送活動提醒（前一天、前一小時）。回傳 {1_day: N, 1_hour: M}。"""
        client = supabase_client.service_role_client()
        now = datetime.now(UTC)
        frontend_base = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:5173")

        # 前一天：start_at 在 [now+23h, now+25h]
        day_lo = (now + timedelta(hours=23)).isoformat()
        day_hi = (now + timedelta(hours=25)).isoformat()
        # 前一小時：start_at 在 [now+55m, now+65m]
        hour_lo = (now + timedelta(minutes=55)).isoformat()
        hour_hi = (now + timedelta(minutes=65)).isoformat()

        count_1day = 0
        count_1hour = 0

        def process_events(lo: str, hi: str, reminder_type: str, counter: list[int]) -> None:
            nonlocal count_1day, count_1hour
            resp = (
                client.table("events")
                .select("id,title,start_at")
                .eq("status", "published")
                .gte("start_at", lo)
                .lte("start_at", hi)
                .execute()
            )
            events = supabase_client.extract_data(resp) or []
            for ev in events:
                ev_id = str(ev.get("id", ""))
                title = ev.get("title", "活動")
                start_at = ev.get("start_at", "")
                if isinstance(start_at, str) and "T" in start_at:
                    try:
                        dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
                        start_display = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        start_display = start_at
                else:
                    start_display = str(start_at)
                participants = self.get_event_participant_emails(UUID(ev_id))
                for _uid, email in participants:
                    try:
                        email_service.send_event_reminder_email(
                            email, title, start_display, reminder_type,
                            event_id=ev_id, frontend_base_url=frontend_base,
                        )
                        counter[0] += 1
                    except Exception as exc:
                        current_app.logger.warning(
                            "[event_notification] reminder send failed to %s: %s", email, exc
                        )

        c1: list[int] = [0]
        c2: list[int] = [0]
        process_events(day_lo, day_hi, "1_day", c1)
        count_1day = c1[0]
        process_events(hour_lo, hour_hi, "1_hour", c2)
        count_1hour = c2[0]

        return {"1_day": count_1day, "1_hour": count_1hour}

    def notify_event_cancelled(self, event_id: UUID, event_title: str) -> None:
        """MVP-3.5: 活動取消/下架時通知參加者。"""
        participants = self.get_event_participant_emails(event_id)
        frontend_base = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:5173")
        for _uid, email in participants:
            try:
                email_service.send_event_cancelled_email(
                    email, event_title, event_id=str(event_id), frontend_base_url=frontend_base
                )
            except Exception as exc:
                current_app.logger.warning(
                    "[event_notification] cancelled email failed to %s: %s", email, exc
                )

    def notify_event_time_changed(
        self, event_id: UUID, event_title: str, old_start: str, new_start: str
    ) -> None:
        """MVP-3.5: 活動時間異動時通知參加者。"""
        participants = self.get_event_participant_emails(event_id)
        frontend_base = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:5173")
        for _uid, email in participants:
            try:
                email_service.send_event_change_email(
                    email, event_title, old_start, new_start,
                    event_id=str(event_id), frontend_base_url=frontend_base,
                )
            except Exception as exc:
                current_app.logger.warning(
                    "[event_notification] change email failed to %s: %s", email, exc
                )


event_notification_service = EventNotificationService()
