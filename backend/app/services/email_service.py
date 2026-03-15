from __future__ import annotations

import os
from typing import Any

from flask import current_app

try:
    import resend
except ImportError:
    resend = None


class EmailService:
    """Email provider: Resend 若已設定 API key，否則僅 log（stub）。"""

    def __init__(self) -> None:
        self._api_key = os.environ.get("RESEND_API_KEY", "").strip()
        self._from_email = os.environ.get("RESEND_FROM_EMAIL", "CypherHub <onboarding@resend.dev>").strip()
        if self._api_key and resend:
            resend.api_key = self._api_key

    def _is_resend_available(self) -> bool:
        return bool(self._api_key and resend is not None)

    def send_ticket_email(
        self,
        to_email: str | None,
        event_title: str,
        ticket: dict[str, Any],
        frontend_base_url: str = "http://localhost:5173",
    ) -> None:
        """單張票券重寄：活動名稱、連結到「我的票券」。由 Resend 寄送（若已設定 API key）。"""
        if not to_email or not to_email.strip():
            current_app.logger.info(
                "[email] send_ticket_email skipped: no to_email (user_id=%s)",
                ticket.get("user_id"),
            )
            return
        tickets_url = f"{frontend_base_url.rstrip('/')}/tickets"
        subject = f"票券資訊：{event_title}"
        html = f"""
        <p>您有一張活動「{event_title}」的票券。</p>
        <p>請至「我的票券」頁面查看 QR Code 與詳情。</p>
        <p><a href="{tickets_url}">前往我的票券</a></p>
        <p>— CypherHub</p>
        """
        if self._is_resend_available():
            try:
                resend.Emails.send(
                    {
                        "from": self._from_email,
                        "to": [to_email.strip()],
                        "subject": subject,
                        "html": html,
                    }
                )
                current_app.logger.info(
                    "[email] ticket email sent to %s ticket_id=%s event=%s",
                    to_email,
                    ticket.get("id"),
                    event_title,
                )
            except Exception as exc:
                current_app.logger.warning("[email] Resend send_ticket_email failed: %s", exc)
                raise
        else:
            current_app.logger.info(
                "[email_stub] send_ticket_email would send to %s event=%s ticket_id=%s",
                to_email,
                event_title,
                ticket.get("id"),
            )

    def send_registration_success_email(
        self,
        to_email: str,
        event_title: str,
        tickets: list[dict[str, Any]],
        frontend_base_url: str = "http://localhost:5173",
    ) -> None:
        """報名成功後寄一封信：活動名稱、票券數量、連結到「我的票券」。"""
        tickets_url = f"{frontend_base_url.rstrip('/')}/tickets"
        count = len(tickets)
        subject = f"報名成功：{event_title}"
        html = f"""
        <p>您已成功報名活動「{event_title}」。</p>
        <p>共 {count} 張票券。請至「我的票券」頁面查看 QR Code 與詳情。</p>
        <p><a href="{tickets_url}">前往我的票券</a></p>
        <p>— CypherHub</p>
        """

        if self._is_resend_available():
            try:
                resend.Emails.send(
                    {
                        "from": self._from_email,
                        "to": [to_email],
                        "subject": subject,
                        "html": html,
                    }
                )
                current_app.logger.info("[email] registration success sent to %s for event %s", to_email, event_title)
            except Exception as exc:
                current_app.logger.warning("[email] Resend send failed: %s", exc)
        else:
            current_app.logger.info(
                "[email_stub] registration success would send to %s event=%s tickets=%s",
                to_email,
                event_title,
                count,
            )


email_service = EmailService()
