from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import g, request

from app.domain.errors import AppError

from .supabase_client import supabase_client

F = TypeVar("F", bound=Callable[..., Any])


def require_auth(func: F) -> F:
    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AppError(
                code="AUTH_REQUIRED",
                message="Missing Authorization Bearer token",
                http_status=401,
            )

        jwt = auth_header.replace("Bearer ", "", 1).strip()
        if not jwt:
            raise AppError(
                code="AUTH_REQUIRED",
                message="Missing Authorization Bearer token",
                http_status=401,
            )

        try:
            user = supabase_client.get_user(jwt)
        except Exception as exc:
            raise AppError(
                code="AUTH_INVALID",
                message="Invalid or expired access token",
                details={"reason": str(exc)},
                http_status=401,
            ) from exc

        user_id = user.get("id") or user.get("sub")
        if not user_id:
            raise AppError(
                code="AUTH_INVALID",
                message="Unable to resolve user id from token",
                http_status=401,
            )

        g.jwt = jwt
        g.user = user
        g.user_id = str(user_id)

        return func(*args, **kwargs)

    return wrapped  # type: ignore[return-value]
