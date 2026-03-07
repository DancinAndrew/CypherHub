from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from flask import request
from pydantic import BaseModel, ValidationError

from app.domain.errors import AppError

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def parse_json(model: type[SchemaT]) -> SchemaT:
    payload = request.get_json(silent=True) or {}
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise AppError(
            code="VALIDATION_ERROR",
            message="Invalid request payload",
            details=exc.errors(),
            http_status=400,
        ) from exc


def parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise AppError(
            code="VALIDATION_ERROR",
            message=f"Invalid {field_name}",
            details={field_name: value},
            http_status=400,
        ) from exc
