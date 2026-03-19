"""MVP-3.5: 內部 jobs endpoint 測試。"""
from __future__ import annotations

from unittest.mock import patch


def test_event_reminders_unauthorized_without_secret(client) -> None:
    """無 X-Cron-Secret 回 401。"""
    resp = client.post("/internal/jobs/event-reminders")
    assert resp.status_code == 401


def test_event_reminders_unauthorized_wrong_secret(client) -> None:
    """錯誤的 X-Cron-Secret 回 401。"""
    resp = client.post(
        "/internal/jobs/event-reminders",
        headers={"X-Cron-Secret": "wrong"},
    )
    assert resp.status_code == 401


def test_event_reminders_ok_with_valid_secret(client, monkeypatch) -> None:
    """正確 X-Cron-Secret 且 CRON_SECRET 有值時回 200。"""
    monkeypatch.setenv("CRON_SECRET", "test-secret-123")
    # app 已載入，需在 test config 設定
    client.application.config["CRON_SECRET"] = "test-secret-123"

    with patch(
        "app.services.event_notification_service.event_notification_service.run_event_reminders",
        return_value={"1_day": 0, "1_hour": 0},
    ):
        resp = client.post(
            "/internal/jobs/event-reminders",
            headers={"X-Cron-Secret": "test-secret-123"},
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["1_day"] == 0
    assert data["1_hour"] == 0
