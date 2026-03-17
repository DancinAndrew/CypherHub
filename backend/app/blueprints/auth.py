from __future__ import annotations

import json
import urllib.error
import urllib.request
from flask import Blueprint, current_app, jsonify, request

from app.domain.errors import AppError
from app.extensions import rate_limiter

from ._utils import parse_json

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _supabase_token(email: str, password: str) -> dict:
    """Call Supabase Auth token endpoint. Returns session dict or raises AppError."""
    url = (current_app.config.get("SUPABASE_URL", "") or "").rstrip("/")
    anon = (current_app.config.get("SUPABASE_ANON_KEY", "") or "").strip()
    if not url or not anon:
        raise AppError(
            code="CONFIG_ERROR",
            message="Auth not configured",
            http_status=500,
        )
    payload = json.dumps({
        "grant_type": "password",
        "email": email.strip().lower(),
        "password": password,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/auth/v1/token",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "apikey": anon,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else "{}"
        try:
            err_data = json.loads(body)
            msg = err_data.get("error_description") or err_data.get("message") or body[:200]
        except json.JSONDecodeError:
            msg = body[:200] or str(e)
        raise AppError(
            code="AUTH_FAILED",
            message=msg,
            http_status=e.code,
        ) from e
    except OSError as exc:
        raise AppError(
            code="AUTH_SERVICE_ERROR",
            message="Unable to reach auth service",
            http_status=502,
        ) from exc
    return data


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
