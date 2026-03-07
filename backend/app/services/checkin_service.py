from __future__ import annotations

import json
from uuid import UUID

from app.domain.errors import AppError, map_supabase_error
from app.domain.schemas import CheckinRequest

from .supabase_client import supabase_client


class CheckinService:
    def parse_checkin_input(self, payload: CheckinRequest) -> tuple[UUID, str]:
        if payload.ticket_id and payload.qr_secret:
            return payload.ticket_id, payload.qr_secret

        if payload.qr_payload:
            try:
                parsed = json.loads(payload.qr_payload)
            except json.JSONDecodeError as exc:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="qr_payload must be valid JSON",
                    http_status=400,
                ) from exc

            ticket_id = parsed.get("ticket_id")
            qr_secret = parsed.get("qr_secret")
            if not ticket_id or not qr_secret:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="qr_payload must contain ticket_id and qr_secret",
                    details={"qr_payload": payload.qr_payload},
                    http_status=400,
                )

            try:
                return UUID(str(ticket_id)), str(qr_secret)
            except ValueError as exc:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="qr_payload.ticket_id must be a valid UUID",
                    http_status=400,
                ) from exc

        raise AppError(
            code="VALIDATION_ERROR",
            message="Provide either ticket_id+qr_secret or qr_payload",
            http_status=400,
        )

    def verify_ticket_qr(self, jwt: str, event_id: UUID, ticket_id: UUID, qr_secret: str) -> dict:
        try:
            result = supabase_client.call_rpc(
                "verify_ticket_qr",
                {
                    "p_event_id": str(event_id),
                    "p_ticket_id": str(ticket_id),
                    "p_qr_secret": qr_secret,
                },
                jwt=jwt,
            )
            return result or {}
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="CHECKIN_VERIFY_FAILED") from exc

    def commit_checkin(self, jwt: str, event_id: UUID, ticket_id: UUID, qr_secret: str) -> dict:
        try:
            result = supabase_client.call_rpc(
                "commit_checkin",
                {
                    "p_event_id": str(event_id),
                    "p_ticket_id": str(ticket_id),
                    "p_qr_secret": qr_secret,
                },
                jwt=jwt,
            )
            return result or {}
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="CHECKIN_COMMIT_FAILED") from exc


checkin_service = CheckinService()
