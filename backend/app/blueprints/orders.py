from __future__ import annotations

from flask import Blueprint

bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")
