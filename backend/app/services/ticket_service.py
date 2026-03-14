from __future__ import annotations

from uuid import UUID

from app.domain.errors import AppError, map_supabase_error

from .email_service import email_service
from .supabase_client import supabase_client


class TicketService:
    def list_my_tickets(self, jwt: str, user_id: str) -> list[dict]:
        client = supabase_client.authed_client(jwt)

        try:
            response = (
                client.table("tickets")
                .select("id,event_id,ticket_type_id,user_id,status,issued_at,checked_in_at,qr_secret,created_at")
                .eq("user_id", user_id)
                .in_("status", ["issued", "checked_in"])
                .order("created_at", desc=True)
                .execute()
            )
            return supabase_client.extract_data(response) or []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="LIST_TICKETS_FAILED") from exc

    def resend_ticket_email(self, jwt: str, ticket_id: UUID, user_id: str) -> None:
        client = supabase_client.authed_client(jwt)

        try:
            response = (
                client.table("tickets")
                .select("id,event_id,ticket_type_id,user_id,status,issued_at,checked_in_at,qr_secret")
                .eq("id", str(ticket_id))
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="TICKET_NOT_FOUND",
                    message="Ticket not found",
                    details={"ticket_id": str(ticket_id)},
                    http_status=404,
                )

            ticket = rows[0]
            email_service.send_ticket_email(str(ticket.get("user_id")), ticket)
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="RESEND_TICKET_FAILED") from exc

    def cancel_ticket(self, jwt: str, ticket_id: UUID, user_id: str) -> None:
        try:
            supabase_client.call_rpc(
                "cancel_ticket",
                {"p_ticket_id": str(ticket_id)},
                jwt=jwt,
            )
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="CANCEL_TICKET_FAILED") from exc


ticket_service = TicketService()
