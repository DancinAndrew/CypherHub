from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from pydantic import ValidationError

from app.domain.errors import AppError, map_supabase_error
from app.domain.schemas import FormFieldType, FormSchemaDefinition

from .supabase_client import supabase_client

_SNAKE_CASE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^[0-9+()\-\s]{6,20}$")


class FormsService:
    FORM_SELECT = "id,event_id,ticket_type_id,schema,version,is_active,created_at,updated_at"

    def get_public_form(self, event_id: UUID, ticket_type_id: UUID | None = None) -> dict | None:
        client = supabase_client.public_client()

        try:
            response = (
                client.table("event_forms")
                .select(self.FORM_SELECT)
                .eq("event_id", str(event_id))
                .eq("is_active", True)
                .order("updated_at", desc=True)
                .execute()
            )
            rows = supabase_client.extract_data(response) or []
            return self._resolve_active_form(rows, ticket_type_id)
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="FORMS_FETCH_FAILED") from exc

    def list_organizer_forms(self, jwt: str, event_id: UUID) -> list[dict]:
        client = supabase_client.authed_client(jwt)

        try:
            response = (
                client.table("event_forms")
                .select(self.FORM_SELECT)
                .eq("event_id", str(event_id))
                .order("updated_at", desc=True)
                .execute()
            )
            return supabase_client.extract_data(response) or []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="FORMS_LIST_FAILED") from exc

    def upsert_form(self, jwt: str, event_id: UUID, payload: dict[str, Any]) -> dict:
        client = supabase_client.authed_client(jwt)
        schema_payload = payload["schema"]
        self.validate_schema_definition(schema_payload)

        ticket_type_id = payload.get("ticket_type_id")
        ticket_type_value = str(ticket_type_id) if ticket_type_id else None

        try:
            if ticket_type_value:
                tt_response = (
                    client.table("ticket_types")
                    .select("id,event_id")
                    .eq("id", ticket_type_value)
                    .limit(1)
                    .execute()
                )
                tt_rows = supabase_client.extract_data(tt_response) or []
                if not tt_rows or str(tt_rows[0].get("event_id")) != str(event_id):
                    raise AppError(
                        code="VALIDATION_ERROR",
                        message="ticket_type_id does not belong to event_id",
                        details={"event_id": str(event_id), "ticket_type_id": ticket_type_value},
                        http_status=400,
                    )

            existing_forms = self.list_organizer_forms(jwt, event_id)
            scoped_forms = [
                form
                for form in existing_forms
                if str(form.get("ticket_type_id")) == ticket_type_value
            ]
            next_version = (
                max((int(form.get("version") or 0) for form in scoped_forms), default=0) + 1
            )

            if payload.get("is_active", True):
                active_forms = [form for form in scoped_forms if form.get("is_active") is True]
                if active_forms:
                    for active_form in active_forms:
                        (
                            client.table("event_forms")
                            .update({"is_active": False})
                            .eq("id", str(active_form["id"]))
                            .execute()
                        )

            insert_response = (
                client.table("event_forms")
                .insert(
                    {
                        "event_id": str(event_id),
                        "ticket_type_id": ticket_type_value,
                        "schema": schema_payload,
                        "version": next_version,
                        "is_active": payload.get("is_active", True),
                    }
                )
                .execute()
            )
            rows = supabase_client.extract_data(insert_response) or []
            if not rows:
                raise AppError(
                    code="FORBIDDEN",
                    message="Unable to save form schema",
                    details={"event_id": str(event_id)},
                    http_status=403,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="FORM_UPSERT_FAILED") from exc

    def validate_answers(
        self,
        form: dict | None,
        answers: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not form:
            return {}

        try:
            schema = FormSchemaDefinition.model_validate(form.get("schema") or {})
        except ValidationError as exc:
            raise AppError(
                code="FORM_SCHEMA_INVALID",
                message="Stored form schema is invalid",
                details=exc.errors(),
                http_status=500,
            ) from exc
        incoming = answers or {}
        normalized: dict[str, Any] = {}

        for field in schema.fields:
            raw_value = incoming.get(field.key)
            normalized[field.key] = self._normalize_field_value(field, raw_value)

        return {key: value for key, value in normalized.items() if value is not None}

    def validate_schema_definition(self, schema_payload: dict[str, Any]) -> None:
        try:
            schema = FormSchemaDefinition.model_validate(schema_payload)
        except ValidationError as exc:
            raise AppError(
                code="VALIDATION_ERROR",
                message="Invalid form schema payload",
                details=exc.errors(),
                http_status=400,
            ) from exc

        seen_keys: set[str] = set()
        for field in schema.fields:
            if field.key in seen_keys:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="Form field keys must be unique",
                    details={"key": field.key},
                    http_status=400,
                )
            seen_keys.add(field.key)

            if not _SNAKE_CASE_KEY_RE.match(field.key):
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="Form field key must be snake_case",
                    details={"key": field.key},
                    http_status=400,
                )

            if field.type in {
                FormFieldType.single_select,
                FormFieldType.multi_select,
                FormFieldType.dropdown,
            } and not field.options:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="Select fields require options",
                    details={"key": field.key},
                    http_status=400,
                )

    @staticmethod
    def _resolve_active_form(rows: list[dict], ticket_type_id: UUID | None) -> dict | None:
        ticket_type_value = str(ticket_type_id) if ticket_type_id else None

        if ticket_type_value:
            for row in rows:
                if str(row.get("ticket_type_id")) == ticket_type_value:
                    return row

        for row in rows:
            if row.get("ticket_type_id") is None:
                return row

        return None

    def _normalize_field_value(self, field, raw_value: Any) -> Any:
        missing = raw_value is None or raw_value == ""

        if field.type == FormFieldType.checkbox:
            if field.required and raw_value is not True:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="Required checkbox field must be checked",
                    details={"field": field.key},
                    http_status=400,
                )
            if raw_value in (None, ""):
                return False
            return bool(raw_value)

        if field.type == FormFieldType.multi_select:
            if missing:
                if field.required:
                    raise AppError(
                        code="VALIDATION_ERROR",
                        message="Missing required field",
                        details={"field": field.key},
                        http_status=400,
                    )
                return []

            if not isinstance(raw_value, list):
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="multi_select field must be an array",
                    details={"field": field.key},
                    http_status=400,
                )

            normalized_values = [str(value) for value in raw_value]
            invalid_values = [value for value in normalized_values if value not in field.options]
            if invalid_values:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="multi_select option is invalid",
                    details={"field": field.key, "invalid": invalid_values},
                    http_status=400,
                )

            if field.required and not normalized_values:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="Missing required field",
                    details={"field": field.key},
                    http_status=400,
                )

            return normalized_values

        if missing:
            if field.required:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="Missing required field",
                    details={"field": field.key},
                    http_status=400,
                )
            return None

        if field.type == FormFieldType.number:
            try:
                parsed = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="number field must be numeric",
                    details={"field": field.key},
                    http_status=400,
                ) from exc
            return int(parsed) if parsed.is_integer() else parsed

        if field.type in {
            FormFieldType.text,
            FormFieldType.phone,
            FormFieldType.email,
            FormFieldType.url,
            FormFieldType.date,
            FormFieldType.single_select,
            FormFieldType.dropdown,
        }:
            value = str(raw_value).strip()
        else:
            value = raw_value

        if field.type == FormFieldType.text:
            return value

        if field.type == FormFieldType.email:
            if not _EMAIL_RE.match(value):
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="email field format is invalid",
                    details={"field": field.key},
                    http_status=400,
                )
            return value

        if field.type == FormFieldType.phone:
            if not _PHONE_RE.match(value):
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="phone field format is invalid",
                    details={"field": field.key},
                    http_status=400,
                )
            return value

        if field.type == FormFieldType.url:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="url field format is invalid",
                    details={"field": field.key},
                    http_status=400,
                )
            return value

        if field.type == FormFieldType.date:
            try:
                date.fromisoformat(value[:10])
            except ValueError:
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError as inner_exc:
                    raise AppError(
                        code="VALIDATION_ERROR",
                        message="date field format is invalid",
                        details={"field": field.key},
                        http_status=400,
                    ) from inner_exc
            return value

        if field.type in {FormFieldType.single_select, FormFieldType.dropdown}:
            if value not in field.options:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="select option is invalid",
                    details={"field": field.key, "value": value},
                    http_status=400,
                )
            return value

        raise AppError(
            code="VALIDATION_ERROR",
            message="Unsupported form field type",
            details={"field": field.key, "type": str(field.type)},
            http_status=400,
        )


forms_service = FormsService()
