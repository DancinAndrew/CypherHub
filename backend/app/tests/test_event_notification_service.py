"""MVP-3.5: 活動提醒與異動通知 service 測試。"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from app.services.event_notification_service import event_notification_service


def test_run_event_reminders_returns_counts(app) -> None:
    """run_event_reminders 回傳 {1_day, 1_hour}。Mock Supabase 避免連線。"""
    fake_response = type("R", (), {"data": []})()

    def _fake_table(*args, **kwargs):
        t = type("T", (), {})()
        t.select = lambda *a, **kw: t
        t.eq = t.gte = t.lte = lambda *a, **kw: t
        t.execute = lambda: fake_response
        return t

    fake_client = type("C", (), {"table": _fake_table})()

    with app.app_context():
        with patch("app.services.event_notification_service.supabase_client") as mock_sb:
            mock_sb.service_role_client.return_value = fake_client
            mock_sb.extract_data.side_effect = lambda r: getattr(r, "data", [])
            result = event_notification_service.run_event_reminders()

    assert "1_day" in result
    assert "1_hour" in result
    assert result["1_day"] == 0
    assert result["1_hour"] == 0


def test_notify_event_cancelled_calls_email(app) -> None:
    """notify_event_cancelled 對參加者發送取消信。"""
    ev_id = uuid4()
    with app.app_context():
        with (
            patch.object(
                event_notification_service,
                "get_event_participant_emails",
                return_value=[("u1", "a@x.com")],
            ),
            patch("app.services.event_notification_service.email_service") as mock_email,
        ):
            event_notification_service.notify_event_cancelled(ev_id, "Test Event")
        mock_email.send_event_cancelled_email.assert_called_once()
        call_args = mock_email.send_event_cancelled_email.call_args
        assert call_args[0][0] == "a@x.com"  # to_email (positional)
        assert call_args[0][1] == "Test Event"  # event_title (positional)
