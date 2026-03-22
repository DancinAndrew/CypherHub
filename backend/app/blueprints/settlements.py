"""MVP-3.3: 結算與提款。主辦方 settlements、payout-requests。"""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.domain.schemas import (
    CreatePayoutRequestRequest,
    PayoutRequestResponse,
)
from app.services.auth_service import require_auth
from app.services.settlement_service import settlement_service

from ._utils import parse_json, parse_uuid

bp = Blueprint("settlements", __name__, url_prefix="/api/v1/organizer")


@bp.get("/settlements")
@require_auth
def list_settlements() -> tuple[dict, int]:
    """主辦方看自己所有 org 的結算列表。"""
    rows = settlement_service.list_settlements_for_org(g.jwt, g.user_id)
    return jsonify({"items": rows}), 200


@bp.get("/settlements/<settlement_id>")
@require_auth
def get_settlement(settlement_id: str) -> tuple[dict, int]:
    """主辦方看單一結算明細。"""
    sid = parse_uuid(settlement_id, "settlement_id")
    row = settlement_service.get_settlement_detail(g.jwt, sid, g.user_id)
    return jsonify(row), 200


@bp.post("/payout-requests")
@require_auth
def create_payout_request() -> tuple[dict, int]:
    """主辦方申請提款。"""
    body = parse_json(CreatePayoutRequestRequest)
    row = settlement_service.create_payout_request(
        g.jwt,
        str(body.org_id),
        body.amount_cents,
        g.user_id,
    )
    payload = PayoutRequestResponse(**row)
    return jsonify({"payout_request": payload.model_dump(mode="json")}), 201
