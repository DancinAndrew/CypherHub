from __future__ import annotations

from typing import Any, Optional

from .schemas import ErrorContent, ErrorResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Any] = None,
        http_status: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.http_status = http_status

    def to_dict(self) -> dict[str, Any]:
        response = ErrorResponse(
            error=ErrorContent(
                code=self.code,
                message=self.message,
                details=self.details,
            )
        )
        return response.model_dump()


_RPC_ERROR_MAP: dict[str, tuple[int, str]] = {
    "AUTH_REQUIRED": (401, "Authentication is required"),
    "FORBIDDEN": (403, "You do not have permission to perform this action"),
    "INVALID_QUANTITY": (400, "Quantity must be greater than zero"),
    "INVALID_EVENT_ID": (400, "Invalid event id"),
    "TICKET_TYPE_NOT_FOUND": (404, "Ticket type not found"),
    "EVENT_NOT_FOUND": (404, "Event not found"),
    "TICKET_NOT_FOUND": (404, "Ticket not found"),
    "TICKET_NOT_FOUND_OR_ALREADY_CANCELLED": (404, "Ticket not found or already cancelled"),
    "EVENT_NOT_PUBLISHED": (409, "Event is not open for registration"),
    "TICKET_TYPE_INACTIVE": (409, "Ticket type is inactive"),
    "SALE_NOT_STARTED": (409, "Sale has not started"),
    "SALE_ENDED": (409, "Sale has ended"),
    "SOLD_OUT": (409, "Tickets are sold out"),
    "PER_USER_LIMIT_EXCEEDED": (409, "Per-user limit exceeded"),
    "PAID_TICKET_NOT_ALLOWED_IN_MVP1": (400, "Paid tickets are not available in MVP-1"),
    "QR_MISMATCH": (400, "QR payload does not match ticket"),
    "INVALID_STATUS": (409, "Ticket status does not allow this operation"),
}


def map_supabase_error(error: Exception, fallback_code: str = "SUPABASE_ERROR") -> AppError:
    raw = str(error)
    normalized = raw.upper()

    if "PERMISSION DENIED FOR FUNCTION" in normalized:
        return AppError(
            code="RPC_PERMISSION_DENIED",
            message="Current user token cannot execute this RPC",
            details={"raw": raw},
            http_status=403,
        )

    if "COULD NOT FIND THE FUNCTION" in normalized:
        return AppError(
            code="RPC_NOT_FOUND",
            message="Required RPC function is missing or signature mismatch",
            details={"raw": raw},
            http_status=500,
        )

    if "INVALID INPUT SYNTAX FOR TYPE UUID" in normalized:
        return AppError(
            code="VALIDATION_ERROR",
            message="Invalid UUID format in request",
            details={"raw": raw},
            http_status=400,
        )

    if "FUNCTION GEN_RANDOM_BYTES" in normalized and "DOES NOT EXIST" in normalized:
        return AppError(
            code="DB_PATCH_REQUIRED",
            message="Database patch required: apply migration 0005 for register_free",
            details={"raw": raw},
            http_status=500,
        )

    if "VIOLATES CHECK CONSTRAINT" in normalized and "TICKET_TYPES_SOLD_CHECK" in normalized:
        return AppError(
            code="SOLD_OUT",
            message="Tickets are sold out",
            details={"raw": raw},
            http_status=409,
        )

    if "AUTH.UID" in normalized and "NULL" in normalized:
        return AppError(
            code="AUTH_REQUIRED",
            message="Authentication is required",
            details={"raw": raw},
            http_status=401,
        )

    for key, (http_status, message) in _RPC_ERROR_MAP.items():
        if key in normalized:
            return AppError(
                code=key,
                message=message,
                details={"raw": raw},
                http_status=http_status,
            )

    if "ROW-LEVEL SECURITY" in normalized or "FORBIDDEN" in normalized:
        return AppError(
            code="FORBIDDEN",
            message="Operation blocked by RLS policy",
            details={"raw": raw},
            http_status=403,
        )

    return AppError(
        code=fallback_code,
        message="Supabase operation failed",
        details={"raw": raw},
        http_status=400,
    )
