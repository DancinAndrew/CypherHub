from __future__ import annotations

from typing import Any

from flask import current_app


class EmailService:
    """Email provider abstraction for MVP-1."""

    def send_ticket_email(self, user_id: str, ticket: dict[str, Any]) -> None:
        current_app.logger.info(
            "[email_stub] send ticket email user_id=%s ticket_id=%s event_id=%s",
            user_id,
            ticket.get("id"),
            ticket.get("event_id"),
        )


email_service = EmailService()
