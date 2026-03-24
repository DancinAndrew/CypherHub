"""email_service 單元測試：_is_resend_available 分支、send 失敗時 log 行為。

依據 note.md：測試 _is_resend_available() 分支、send 失敗時 log 行為。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.email_service import EmailService, email_service

# --- _is_resend_available 分支 ---


def test_is_resend_available_true_when_api_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """RESEND_API_KEY 有值且 resend 可 import → True。"""
    monkeypatch.setenv("RESEND_API_KEY", "re_xxx")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("RESEND_API_KEY", "re_123")
    svc = EmailService()
    assert svc._is_resend_available() is True


def test_is_resend_available_false_when_api_key_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """RESEND_API_KEY 空 → False。"""
    monkeypatch.setenv("RESEND_API_KEY", "")
    svc = EmailService()
    assert svc._is_resend_available() is False


def test_is_resend_available_false_when_resend_not_imported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resend 為 None（未 import）→ False。"""
    monkeypatch.setattr("app.services.email_service.resend", None)
    monkeypatch.setenv("RESEND_API_KEY", "re_xxx")
    svc = EmailService()
    assert svc._api_key == "re_xxx"
    assert svc._is_resend_available() is False


# --- send_registration_success_email ---


def test_send_registration_stub_logs_when_not_available(
    app, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stub 分支：記錄 [email_stub] log。"""
    monkeypatch.setattr(email_service, "_is_resend_available", lambda: False)
    logger_mock = MagicMock()
    monkeypatch.setattr(app, "logger", logger_mock)
    with app.app_context():
        email_service.send_registration_success_email(
            to_email="user@example.com",
            event_title="測試活動",
            tickets=[{"id": "t1"}],
        )
    logger_mock.info.assert_called()
    call_str = str(logger_mock.info.call_args)
    assert "[email_stub]" in call_str and "registration success would send" in call_str


def test_send_registration_resend_success_logs_info(app, monkeypatch: pytest.MonkeyPatch) -> None:
    """Resend 分支成功：記錄 [email] info log。"""
    monkeypatch.setattr(email_service, "_is_resend_available", lambda: True)
    send_mock = MagicMock()
    monkeypatch.setattr("app.services.email_service.resend.Emails.send", send_mock)
    logger_mock = MagicMock()
    monkeypatch.setattr(app, "logger", logger_mock)

    with app.app_context():
        email_service.send_registration_success_email(
            to_email="user@example.com",
            event_title="測試活動",
            tickets=[{"id": "t1"}],
        )

    send_mock.assert_called_once()
    logger_mock.info.assert_called()
    assert "registration success sent" in str(logger_mock.info.call_args)


def test_send_registration_resend_failure_logs_warning_no_raise(
    app, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resend 分支失敗：記錄 warning、不 raise。"""
    monkeypatch.setattr(email_service, "_is_resend_available", lambda: True)
    monkeypatch.setattr(
        "app.services.email_service.resend.Emails.send",
        MagicMock(side_effect=Exception("Resend API error")),
    )
    logger_mock = MagicMock()
    monkeypatch.setattr(app, "logger", logger_mock)

    with app.app_context():
        email_service.send_registration_success_email(
            to_email="user@example.com",
            event_title="測試活動",
            tickets=[],
        )

    logger_mock.warning.assert_called_once()
    assert "Resend send failed" in str(logger_mock.warning.call_args)


# --- send_ticket_email ---


def test_send_ticket_stub_logs_when_not_available(app, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub 分支：記錄 [email_stub] log。"""
    monkeypatch.setattr(email_service, "_is_resend_available", lambda: False)
    logger_mock = MagicMock()
    monkeypatch.setattr(app, "logger", logger_mock)
    with app.app_context():
        email_service.send_ticket_email(
            to_email="user@example.com",
            event_title="測試活動",
            ticket={"id": "t1", "user_id": "u1"},
        )
    logger_mock.info.assert_called()
    call_str = str(logger_mock.info.call_args)
    assert "[email_stub]" in call_str and "send_ticket_email would send" in call_str


def test_send_ticket_resend_failure_logs_warning_and_raises(
    app, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resend 分支失敗：記錄 warning 並 re-raise。"""
    monkeypatch.setattr(email_service, "_is_resend_available", lambda: True)
    monkeypatch.setattr(
        "app.services.email_service.resend.Emails.send",
        MagicMock(side_effect=Exception("Resend API error")),
    )
    logger_mock = MagicMock()
    monkeypatch.setattr(app, "logger", logger_mock)

    with app.app_context():
        with pytest.raises(Exception, match="Resend API error"):
            email_service.send_ticket_email(
                to_email="user@example.com",
                event_title="測試活動",
                ticket={"id": "t1"},
            )

    logger_mock.warning.assert_called_once()
    assert "send_ticket_email failed" in str(logger_mock.warning.call_args)


def test_send_ticket_skipped_when_no_email(app, monkeypatch: pytest.MonkeyPatch) -> None:
    """to_email 空時跳過、記錄 skip log。"""
    monkeypatch.setattr(email_service, "_is_resend_available", lambda: True)
    logger_mock = MagicMock()
    monkeypatch.setattr(app, "logger", logger_mock)
    with app.app_context():
        email_service.send_ticket_email(
            to_email=None,
            event_title="測試",
            ticket={"id": "t1", "user_id": "u1"},
        )
    logger_mock.info.assert_called()
    call_str = str(logger_mock.info.call_args)
    assert "skipped" in call_str and "no to_email" in call_str
