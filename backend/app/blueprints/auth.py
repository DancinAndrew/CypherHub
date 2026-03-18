from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from app.domain.errors import AppError
from app.extensions import rate_limiter
from app.services.supabase_client import supabase_client

from ._utils import parse_json

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _session_from_resp(resp: object) -> object | None:
    """Extract session from Supabase sign_in response (object or dict)."""
    session = getattr(resp, "session", None)
    if session is not None:
        return session
    data = getattr(resp, "data", None)
    if data is None:
        return None
    if hasattr(data, "session"):
        return data.session
    if isinstance(data, dict):
        return data.get("session")
    return None


def _get_attr_or_key(obj: object, key: str, default: object = None) -> object:
    """Get attribute or dict key from session-like object."""
    val = getattr(obj, key, None)
    if val is not None:
        return val
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _user_to_dict(user: object) -> dict:
    """Convert Supabase User object to JSON-serializable dict."""
    if hasattr(user, "model_dump"):
        return user.model_dump()
    if hasattr(user, "__dict__"):
        return dict(user.__dict__)
    return {"id": getattr(user, "id", None), "email": getattr(user, "email", None)}


def _supabase_token(email: str, password: str) -> dict:
    """Sign in via Supabase client; returns session dict or raises AppError."""
    url = current_app.config.get("SUPABASE_URL") or ""
    anon = current_app.config.get("SUPABASE_ANON_KEY") or ""
    if not url or not anon:
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
        invalid = (
            "invalid login credentials" in msg
            or "invalid_credentials" in msg
            or "invalid_grant" in msg
        )
        if invalid:
            raise AppError(
                code="AUTH_FAILED",
                message="Invalid login credentials",
                http_status=400,
            ) from exc
        detail = f": {exc!s}" if (current_app.config.get("TESTING") or current_app.debug) else ""
        raise AppError(
            code="AUTH_SERVICE_ERROR",
            message=f"Unable to reach auth service{detail}",
            http_status=502,
        ) from exc

    session = _session_from_resp(resp)
    if not session:
        raise AppError(
            code="AUTH_FAILED",
            message="No session returned",
            http_status=400,
        )
    access_token = _get_attr_or_key(session, "access_token")
    refresh_token = _get_attr_or_key(session, "refresh_token")
    if not access_token or not refresh_token:
        raise AppError(
            code="AUTH_FAILED",
            message="Missing tokens in session",
            http_status=400,
        )
    user = _get_attr_or_key(session, "user") or getattr(resp, "user", None)
    if user is not None and not isinstance(user, dict):
        user = _user_to_dict(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": _get_attr_or_key(session, "expires_in"),
        "token_type": _get_attr_or_key(session, "token_type") or "bearer",
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
