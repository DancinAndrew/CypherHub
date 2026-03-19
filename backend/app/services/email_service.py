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
        self._from_email = os.environ.get(
            "RESEND_FROM_EMAIL", "CypherHub <onboarding@resend.dev>"
        ).strip()
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
                current_app.logger.info(
                    "[email] registration success sent to %s for event %s", to_email, event_title
                )
            except Exception as exc:
                current_app.logger.warning("[email] Resend send failed: %s", exc)
        else:
            current_app.logger.info(
                "[email_stub] registration success would send to %s event=%s tickets=%s",
                to_email,
                event_title,
                count,
            )

    def send_refund_complete_email(
        self,
        to_email: str | None,
        order_id: str,
        amount_display: str,
        frontend_base_url: str = "http://localhost:5173",
    ) -> None:
        """退款完成後寄信給使用者。"""
        if not to_email or not to_email.strip():
            current_app.logger.info(
                "[email] send_refund_complete_email skipped: no to_email (order_id=%s)",
                order_id,
            )
            return
        orders_url = f"{frontend_base_url.rstrip('/')}/orders"
        subject = "退款完成通知"
        html = f"""
        <p>您的訂單 {order_id[:8]}... 已成功退款。</p>
        <p>退款金額：{amount_display}</p>
        <p><a href="{orders_url}">查看訂單</a></p>
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
                    "[email] refund complete sent to %s order_id=%s", to_email, order_id
                )
            except Exception as exc:
                current_app.logger.warning(
                    "[email] Resend send_refund_complete_email failed: %s", exc
                )
                raise
        else:
            current_app.logger.info(
                "[email_stub] refund complete would send to %s order_id=%s", to_email, order_id
            )

    def send_event_reminder_email(
        self,
        to_email: str | None,
        event_title: str,
        event_start_at: str,
        reminder_type: str,
        event_id: str | None = None,
        frontend_base_url: str = "http://localhost:5173",
    ) -> None:
        """MVP-3.5: 活動提醒（前一天或前一小時）。reminder_type='1_day'|'1_hour'。"""
        if not to_email or not to_email.strip():
            return
        base = frontend_base_url.rstrip("/")
        event_url = f"{base}/events/{event_id}" if event_id else f"{base}/events"
        if reminder_type == "1_day":
            subject = f"明天就是「{event_title}」！"
            html = f"""
        <p>提醒您：您報名的活動「{event_title}」將於明天開始。</p>
        <p>活動時間：{event_start_at}</p>
        <p><a href="{event_url}">查看活動</a></p>
        <p>— CypherHub</p>
        """
        else:
            subject = f"一小時後：「{event_title}」即將開始"
            html = f"""
        <p>提醒您：您報名的活動「{event_title}」將在一小時後開始。</p>
        <p>活動時間：{event_start_at}</p>
        <p><a href="{event_url}">查看活動</a></p>
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
                    "[email] event reminder sent to %s %s %s",
                    to_email,
                    reminder_type,
                    event_title,
                )
            except Exception as exc:
                current_app.logger.warning(
                    "[email] Resend send_event_reminder_email failed: %s", exc
                )
                raise
        else:
            current_app.logger.info(
                "[email_stub] event reminder would send to %s %s %s",
                to_email,
                reminder_type,
                event_title,
            )

    def send_event_change_email(
        self,
        to_email: str | None,
        event_title: str,
        old_start: str,
        new_start: str,
        event_id: str | None = None,
        frontend_base_url: str = "http://localhost:5173",
    ) -> None:
        """MVP-3.5: 活動時間異動通知。"""
        if not to_email or not to_email.strip():
            return
        base = frontend_base_url.rstrip("/")
        event_url = f"{base}/events/{event_id}" if event_id else f"{base}/events"
        subject = f"「{event_title}」活動時間異動通知"
        html = f"""
        <p>您報名的活動「{event_title}」時間已更新。</p>
        <p>原時間：{old_start}</p>
        <p>新時間：{new_start}</p>
        <p><a href="{event_url}">查看活動詳情</a></p>
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
                    "[email] event change sent to %s %s", to_email, event_title
                )
            except Exception as exc:
                current_app.logger.warning("[email] Resend send_event_change_email failed: %s", exc)
                raise
        else:
            current_app.logger.info("[email_stub] event change would send to %s %s", to_email, event_title)

    def send_event_cancelled_email(
        self,
        to_email: str | None,
        event_title: str,
        event_id: str | None = None,
        frontend_base_url: str = "http://localhost:5173",
    ) -> None:
        """MVP-3.5: 活動取消/下架通知。"""
        if not to_email or not to_email.strip():
            return
        base = frontend_base_url.rstrip("/")
        event_url = f"{base}/events/{event_id}" if event_id else f"{base}/events"
        subject = f"「{event_title}」活動已取消"
        html = f"""
        <p>很遺憾通知您：您報名的活動「{event_title}」已取消或下架。</p>
        <p>若有疑問請與主辦方聯繫。</p>
        <p><a href="{event_url}">探索其他活動</a></p>
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
                    "[email] event cancelled sent to %s %s", to_email, event_title
                )
            except Exception as exc:
                current_app.logger.warning("[email] Resend send_event_cancelled_email failed: %s", exc)
                raise
        else:
            current_app.logger.info("[email_stub] event cancelled would send to %s %s", to_email, event_title)


email_service = EmailService()
