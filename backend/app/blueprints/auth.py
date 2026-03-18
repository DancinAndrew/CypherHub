from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from app.domain.errors import AppError
from app.extensions import rate_limiter
from app.services.supabase_client import supabase_client

from ._utils import parse_json

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _supabase_token(email: str, password: str) -> dict:
    """Sign in via Supabase client (sign_in_with_password). Returns session dict or raises AppError."""
    if not current_app.config.get("SUPABASE_URL") or not current_app.config.get("SUPABASE_ANON_KEY"):
        raise AppError(
            code="CONFIG_ERROR",
            message="Auth not configured",
            http_status=500,
        )
    try:
        client = supabase_client.public_client()
        resp = client.auth.sign_in_with_password(
            {"email": email.strip().lower(), "password": password.strip()}
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "invalid login credentials" in msg or "invalid_credentials" in msg or "invalid_grant" in msg:
            raise AppError(code="AUTH_FAILED", message="Invalid login credentials", http_status=400) from exc
        detail = f": {exc!s}" if (current_app.config.get("TESTING") or current_app.debug) else ""
        raise AppError(
            code="AUTH_SERVICE_ERROR",
            message=f"Unable to reach auth service{detail}",
            http_status=502,
        ) from exc

    session = getattr(resp, "session", None)
    if session is None:
        session = getattr(resp, "data", None) and (getattr(resp.data, "session", None) or (resp.data.get("session") if isinstance(getattr(resp, "data"), dict) else None))
    if not session:
        raise AppError(
            code="AUTH_FAILED",
            message="No session returned",
            http_status=400,
        )
    access_token = getattr(session, "access_token", None) or (session.get("access_token") if isinstance(session, dict) else None)
    refresh_token = getattr(session, "refresh_token", None) or (session.get("refresh_token") if isinstance(session, dict) else None)
    if not access_token or not refresh_token:
        raise AppError(
            code="AUTH_FAILED",
            message="Missing tokens in session",
            http_status=400,
        )
    user = getattr(session, "user", None) or (session.get("user") if isinstance(session, dict) else None) or getattr(resp, "user", None)
    if user is not None and not isinstance(user, dict):
        user = getattr(user, "model_dump", lambda: None)() or getattr(user, "__dict__", None) or {"id": getattr(user, "id", None), "email": getattr(user, "email", None)}

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": getattr(session, "expires_in", None) or (session.get("expires_in") if isinstance(session, dict) else None),
        "token_type": getattr(session, "token_type", "bearer") or (session.get("token_type") if isinstance(session, dict) else "bearer"),
        "user": user,
    }


@bp.post("/login")
@rate_limiter.limit("10 per minute")
def login() -> tuple[dict, int]:
    """Login proxy for Supabase Auth. Rate limited to prevent brute force."""
    from app.domain.schemas import LoginRequest

    body = parse_json(LoginRequest)
    session = _supabase_token(body.email, body.password)
    return jsonify(session), 200


@bp.post("/logout")
def logout() -> tuple[str, int]:
    return "", 204
