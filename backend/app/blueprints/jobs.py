"""MVP-3.5: 內部 Cron jobs（活動提醒等）。需 X-Cron-Secret header 驗證。"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.services.event_notification_service import event_notification_service

bp = Blueprint("jobs", __name__, url_prefix="/internal/jobs")


def _verify_cron_secret() -> bool:
    secret = request.headers.get("X-Cron-Secret", "")
    expected = current_app.config.get("CRON_SECRET", "")
    return bool(expected and secret == expected)


@bp.post("/event-reminders")
def event_reminders() -> tuple[dict, int]:
    """前一天、前一小時活動提醒。由外部 cron（如 Render Cron、cron-job.org）定期呼叫。"""
    if not _verify_cron_secret():
        return jsonify({"error": "Unauthorized"}), 401
    result = event_notification_service.run_event_reminders()
    return jsonify(result), 200
