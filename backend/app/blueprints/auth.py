from __future__ import annotations

from flask import Blueprint, jsonify

from app.extensions import rate_limiter
from app.services.auth_service import auth_service

from ._utils import parse_json

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.post("/login")
@rate_limiter.limit("10 per minute")
def login() -> tuple[dict, int]:
    """Login proxy for Supabase Auth. Rate limited to prevent brute force."""
    from app.domain.schemas import LoginRequest

    body = parse_json(LoginRequest)
    session = auth_service.login_with_password(body.email, body.password)
    return jsonify(session), 200


@bp.post("/logout")
def logout() -> tuple[str, int]:
    return "", 204
