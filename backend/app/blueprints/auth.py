from __future__ import annotations

from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.post("/logout")
def logout() -> tuple[str, int]:
    return "", 204
