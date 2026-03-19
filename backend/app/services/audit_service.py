"""MVP-3.4: 平台治理 Audit。關鍵操作寫入 audit_logs。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.supabase_client import supabase_client


class AuditService:
    """關鍵操作寫入 audit_logs（僅 service_role 可寫）。"""

    ACTOR_ADMIN = "admin"
    ACTOR_ORGANIZER = "organizer"
    ACTOR_SYSTEM = "system"

    def log(
        self,
        *,
        actor_type: str,
        actor_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """寫入 audit_logs。失敗不拋錯，避免影響主流程。"""
        try:
            sr = supabase_client.service_role_client()
            row = {
                "actor_type": actor_type,
                "actor_id": str(actor_id) if actor_id else None,
                "action": action,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                "details": details or {},
            }
            sr.table("audit_logs").insert(row).execute()
        except Exception as exc:
            from flask import current_app

            current_app.logger.warning(
                "[audit] log failed: action=%s resource=%s err=%s",
                action,
                resource_type,
                exc,
            )

    def log_refund(self, order_id: UUID, admin_user_id: str, amount_cents: int) -> None:
        self.log(
            actor_type=self.ACTOR_ADMIN,
            actor_id=admin_user_id,
            action="refund",
            resource_type="order",
            resource_id=str(order_id),
            details={"amount_cents": amount_cents},
        )

    def log_comp_ticket(
        self,
        ticket_id: UUID,
        event_id: UUID,
        ticket_type_id: UUID,
        recipient_user_id: str,
        actor_type: str,
        actor_id: str,
        note: str | None = None,
    ) -> None:
        self.log(
            actor_type=actor_type,
            actor_id=actor_id,
            action="comp_ticket",
            resource_type="ticket",
            resource_id=str(ticket_id),
            details={
                "event_id": str(event_id),
                "ticket_type_id": str(ticket_type_id),
                "recipient_user_id": recipient_user_id,
                "note": note,
            },
        )

    def log_unpublish(self, event_id: UUID, admin_user_id: str, status: str) -> None:
        self.log(
            actor_type=self.ACTOR_ADMIN,
            actor_id=admin_user_id,
            action="unpublish",
            resource_type="event",
            resource_id=str(event_id),
            details={"status": status},
        )

    def log_payout_approve(
        self, payout_id: UUID, admin_user_id: str, org_id: str, amount_cents: int
    ) -> None:
        self.log(
            actor_type=self.ACTOR_ADMIN,
            actor_id=admin_user_id,
            action="payout_approve",
            resource_type="payout_request",
            resource_id=str(payout_id),
            details={"org_id": org_id, "amount_cents": amount_cents},
        )

    def log_payout_reject(
        self, payout_id: UUID, admin_user_id: str, failure_reason: str | None = None
    ) -> None:
        self.log(
            actor_type=self.ACTOR_ADMIN,
            actor_id=admin_user_id,
            action="payout_reject",
            resource_type="payout_request",
            resource_id=str(payout_id),
            details={"failure_reason": failure_reason},
        )

    def log_settlement_generate(
        self, admin_user_id: str, period_start: str, period_end: str, count: int
    ) -> None:
        self.log(
            actor_type=self.ACTOR_ADMIN,
            actor_id=admin_user_id,
            action="settlement_generate",
            resource_type="settlement",
            resource_id=None,
            details={"period_start": period_start, "period_end": period_end, "count": count},
        )


audit_service = AuditService()
