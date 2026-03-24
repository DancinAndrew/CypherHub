"""Event time change notification 測試。驗證 notify_event_time_changed 對參加者發送異動通知。"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from app.services.event_notification_service import event_notification_service


def test_notify_time_changed_calls_email(app) -> None:
    """notify_event_time_changed 對每位參加者呼叫 send_event_change_email。"""
    ev_id = uuid4()
    with app.app_context():
        with (
            patch.object(
                event_notification_service,
                "get_event_participant_emails",
                return_value=[("u1", "a@x.com"), ("u2", "b@x.com")],
            ),
            patch("app.services.event_notification_service.email_service") as mock_email,
        ):
            event_notification_service.notify_event_time_changed(
                ev_id, "Battle Night", "2026-04-01 19:00", "2026-04-02 20:00"
            )

        assert mock_email.send_event_change_email.call_count == 2
        first_call = mock_email.send_event_change_email.call_args_list[0]
        assert first_call[0][0] == "a@x.com"
        assert first_call[0][1] == "Battle Night"
        assert first_call[0][2] == "2026-04-01 19:00"
        assert first_call[0][3] == "2026-04-02 20:00"


def test_notify_time_changed_no_participants(app) -> None:
    """無參加者時不呼叫 email service。"""
    ev_id = uuid4()
    with app.app_context():
        with (
            patch.object(
                event_notification_service,
                "get_event_participant_emails",
                return_value=[],
            ),
            patch("app.services.event_notification_service.email_service") as mock_email,
        ):
            event_notification_service.notify_event_time_changed(
                ev_id, "Battle Night", "2026-04-01 19:00", "2026-04-02 20:00"
            )

        mock_email.send_event_change_email.assert_not_called()


def test_notify_time_changed_email_failure_does_not_raise(app) -> None:
    """單一 email 發送失敗不應中斷其他通知。"""
    ev_id = uuid4()
    with app.app_context():
        with (
            patch.object(
                event_notification_service,
                "get_event_participant_emails",
                return_value=[("u1", "fail@x.com"), ("u2", "ok@x.com")],
            ),
            patch("app.services.event_notification_service.email_service") as mock_email,
        ):
            mock_email.send_event_change_email.side_effect = [
                Exception("SMTP error"),
                None,
            ]
            # Should not raise
            event_notification_service.notify_event_time_changed(
                ev_id, "Battle Night", "old", "new"
            )

        assert mock_email.send_event_change_email.call_count == 2
