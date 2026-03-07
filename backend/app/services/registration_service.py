from __future__ import annotations

from uuid import UUID

from app.domain.errors import AppError, map_supabase_error

from .forms_service import forms_service
from .supabase_client import supabase_client


class RegistrationService:
    def register_free(
        self,
        jwt: str,
        event_id: UUID,
        ticket_type_id: UUID,
        quantity: int,
        answers: dict,
    ) -> list[dict]:
        client = supabase_client.authed_client(jwt)

        try:
            tt_response = (
                client.table("ticket_types")
                .select("id,event_id,price_cents,is_active")
                .eq("id", str(ticket_type_id))
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(tt_response) or []
            if not rows:
                raise AppError(
                    code="TICKET_TYPE_NOT_FOUND",
                    message="Ticket type not found",
                    details={"ticket_type_id": str(ticket_type_id)},
                    http_status=404,
                )

            ticket_type = rows[0]
            if str(ticket_type.get("event_id")) != str(event_id):
                raise AppError(
                    code="TICKET_TYPE_EVENT_MISMATCH",
                    message="ticket_type_id does not belong to event_id",
                    details={"event_id": str(event_id), "ticket_type_id": str(ticket_type_id)},
                    http_status=400,
                )

            if int(ticket_type.get("price_cents") or 0) != 0:
                raise AppError(
                    code="PAID_TICKET_NOT_ALLOWED_IN_MVP1",
                    message="Paid tickets are not available in MVP-1",
                    http_status=400,
                )

            form = forms_service.get_public_form(event_id, ticket_type_id)
            normalized_answers = forms_service.validate_answers(form, answers)

            rpc_data = supabase_client.call_rpc(
                "register_free_v2",
                {
                    "p_ticket_type_id": str(ticket_type_id),
                    "p_quantity": quantity,
                    "p_answers": normalized_answers,
                },
                jwt=jwt,
            )
            return rpc_data or []
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="REGISTER_FAILED") from exc


registration_service = RegistrationService()
