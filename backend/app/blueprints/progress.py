from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.domain.schemas import (
    EventProgressUpdate,
    EventStagesRequest,
)
from app.extensions import rate_limiter
from app.services.auth_service import require_auth
from app.services.progress_service import progress_service

from ._utils import parse_json, parse_uuid

# --- 主辦方端：階段管理 + 進度控制 ---

organizer_bp = Blueprint(
    "organizer_progress",
    __name__,
    url_prefix="/api/v1/organizer/events",
)


@organizer_bp.get("/<event_id>/stages")
@rate_limiter.limit("30 per minute")
@require_auth
def list_stages(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    stages = progress_service.list_stages(event_uuid, jwt=g.jwt)
    return jsonify({"stages": stages}), 200


@organizer_bp.put("/<event_id>/stages")
@rate_limiter.limit("10 per minute")
@require_auth
def replace_stages(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    body = parse_json(EventStagesRequest)
    stages = progress_service.replace_stages(
        jwt=g.jwt,
        event_id=event_uuid,
        user_id=g.user_id,
        stages=body.stages,
    )
    return jsonify({"stages": stages}), 200


@organizer_bp.get("/<event_id>/progress")
@rate_limiter.limit("30 per minute")
@require_auth
def get_progress(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    progress = progress_service.get_progress(event_uuid, jwt=g.jwt)
    stages = progress_service.list_stages(event_uuid, jwt=g.jwt)
    return jsonify({"progress": progress, "stages": stages}), 200


@organizer_bp.patch("/<event_id>/progress")
@rate_limiter.limit("20 per minute")
@require_auth
def update_progress(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    body = parse_json(EventProgressUpdate)
    progress = progress_service.update_progress(
        jwt=g.jwt,
        event_id=event_uuid,
        user_id=g.user_id,
        current_stage_id=body.current_stage_id,
        status=body.status,
        note=body.note,
    )
    return jsonify({"progress": progress}), 200


@organizer_bp.get("/<event_id>/progress/log")
@rate_limiter.limit("30 per minute")
@require_auth
def get_progress_log(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    log = progress_service.get_progress_log(event_uuid, jwt=g.jwt)
    return jsonify({"log": log}), 200


# --- 參加者端：公開讀取進度 ---

public_bp = Blueprint(
    "public_progress",
    __name__,
    url_prefix="/api/v1/events",
)


@public_bp.get("/<event_id>/progress")
@rate_limiter.limit("60 per minute")
def get_public_progress(event_id: str) -> tuple[dict, int]:
    event_uuid = parse_uuid(event_id, "event_id")
    result = progress_service.get_public_progress(event_uuid)
    return jsonify(result), 200
