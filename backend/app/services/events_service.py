from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from flask import current_app

from app.domain.errors import AppError, map_supabase_error

from .email_service import email_service
from .supabase_client import supabase_client

UTC = getattr(datetime, "UTC", timezone(timedelta(0)))
EVENT_PUBLIC_SELECT = (
    "id,org_id,title,description,short_desc,start_at,end_at,timezone,location_name,"
    "location_address,map_url,contact_email,contact_phone,registration_start_at,"
    "registration_end_at,socials,eligibility,event_language,checkin_open_at,checkin_note,"
    "schedule,rules,refund_policy,status,published_at,dance_styles,event_types"
)


class EventsService:
    @staticmethod
    def _pg_array_literal(values: list[str]) -> str:
        # PostgREST overlap filter expects postgres array literal, e.g. "{hiphop,popping}".
        escaped = [value.replace('"', '\\"') for value in values]
        return "{" + ",".join(escaped) + "}"

    def list_events(
        self,
        q: str | None = None,
        from_at: str | None = None,
        to_at: str | None = None,
        org_id: str | None = None,
        styles: list[str] | None = None,
        types: list[str] | None = None,
    ) -> list[dict]:
        client = supabase_client.public_client()

        query = client.table("events").select(EVENT_PUBLIC_SELECT)
        query = query.eq("status", "published")

        if org_id:
            query = query.eq("org_id", org_id)

        if q:
            query = query.ilike("title", f"%{q}%")

        if from_at:
            query = query.gte("start_at", from_at)

        if to_at:
            query = query.lte("start_at", to_at)

        if styles:
            query = query.filter("dance_styles", "ov", self._pg_array_literal(styles))

        if types:
            query = query.filter("event_types", "ov", self._pg_array_literal(types))

        try:
            response = query.order("start_at", desc=False).execute()
            return supabase_client.extract_data(response) or []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="EVENTS_LIST_FAILED") from exc

    def list_public_events(
        self,
        q: str | None = None,
        from_at: str | None = None,
        to_at: str | None = None,
        org_id: str | None = None,
        styles: list[str] | None = None,
        types: list[str] | None = None,
    ) -> list[dict]:
        return self.list_events(
            q=q,
            from_at=from_at,
            to_at=to_at,
            org_id=org_id,
            styles=styles,
            types=types,
        )

    def get_event_title(self, event_id: UUID) -> str:
        """取得活動標題（供 email 等使用，不檢查 published）。"""
        client = supabase_client.public_client()
        try:
            response = (
                client.table("events")
                .select("title")
                .eq("id", str(event_id))
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(response) or []
            return rows[0].get("title", "活動") if rows else "活動"
        except Exception:
            return "活動"

    def get_public_event_detail(self, event_id: UUID) -> dict:
        client = supabase_client.public_client()

        try:
            event_response = (
                client.table("events")
                .select(EVENT_PUBLIC_SELECT)
                .eq("id", str(event_id))
                .eq("status", "published")
                .limit(1)
                .execute()
            )
            events = supabase_client.extract_data(event_response) or []
            if not events:
                raise AppError(
                    code="EVENT_NOT_FOUND",
                    message="Event not found",
                    details={"event_id": str(event_id)},
                    http_status=404,
                )

            media_response = (
                client.table("event_media")
                .select("id,event_id,path,sort_order,created_at")
                .eq("event_id", str(event_id))
                .order("sort_order", desc=False)
                .execute()
            )
            ticket_type_response = (
                client.table("ticket_types")
                .select(
                    "id,event_id,name,description,price_cents,currency,capacity,sold_count,per_user_limit,sale_start_at,sale_end_at,is_active"
                )
                .eq("event_id", str(event_id))
                .eq("is_active", True)
                .order("created_at", desc=False)
                .execute()
            )
            event = events[0]
            org_id = event.get("org_id")
            organizer = None
            other_events: list[dict] = []
            if org_id:
                org_response = (
                    client.table("organizations")
                    .select("id,name,description,contact_email,logo_url")
                    .eq("id", str(org_id))
                    .limit(1)
                    .execute()
                )
                org_rows = supabase_client.extract_data(org_response) or []
                if org_rows:
                    organizer = org_rows[0]
                other_response = (
                    client.table("events")
                    .select(EVENT_PUBLIC_SELECT)
                    .eq("org_id", str(org_id))
                    .eq("status", "published")
                    .neq("id", str(event_id))
                    .order("start_at", desc=False)
                    .limit(6)
                    .execute()
                )
                other_events = supabase_client.extract_data(other_response) or []

            return {
                "event": event,
                "event_media": supabase_client.extract_data(media_response) or [],
                "ticket_types": supabase_client.extract_data(ticket_type_response) or [],
                "organizer": organizer,
                "other_events": other_events,
            }
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="EVENT_DETAIL_FAILED") from exc

    def apply_organizer(self, jwt: str, user_id: str, payload: dict) -> dict:
        client = supabase_client.authed_client(jwt)
        values = {
            "name": payload["name"],
            "description": payload.get("description"),
            "contact_email": payload.get("contact_email"),
            "logo_url": payload.get("logo_url"),
            "owner_user_id": user_id,
        }

        try:
            response = client.table("organizations").insert(values).execute()
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="FORBIDDEN",
                    message="Unable to create organization",
                    http_status=403,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="ORGANIZER_APPLY_FAILED") from exc

    def create_event(self, jwt: str, user_id: str, payload: dict) -> dict:
        client = supabase_client.authed_client(jwt)

        values = {
            **payload,
            "org_id": str(payload["org_id"]),
            "created_by": user_id,
            "dance_styles": payload.get("dance_styles", []),
            "event_types": payload.get("event_types", []),
        }
        if values.get("status") == "published" and not values.get("published_at"):
            values["published_at"] = datetime.now(UTC).isoformat()

        try:
            response = client.table("events").insert(values).execute()
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="FORBIDDEN",
                    message="Unable to create event",
                    http_status=403,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="CREATE_EVENT_FAILED") from exc

    def update_event(self, jwt: str, event_id: UUID, payload: dict) -> dict:
        client = supabase_client.authed_client(jwt)

        update_values = {key: value for key, value in payload.items() if value is not None}
        if update_values.get("status") == "published" and "published_at" not in update_values:
            update_values["published_at"] = datetime.now(UTC).isoformat()

        if not update_values:
            raise AppError(
                code="VALIDATION_ERROR",
                message="No updatable fields provided",
                http_status=400,
            )

        try:
            response = (
                client.table("events")
                .update(update_values)
                .eq("id", str(event_id))
                .execute()
            )
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="EVENT_NOT_FOUND",
                    message="Event not found or no permission",
                    details={"event_id": str(event_id)},
                    http_status=404,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="UPDATE_EVENT_FAILED") from exc

    def get_organizer_event_detail(self, jwt: str, event_id: UUID, user_id: str) -> dict:
        client = supabase_client.authed_client(jwt)

        try:
            event_response = (
                client.table("events")
                .select(EVENT_PUBLIC_SELECT)
                .eq("id", str(event_id))
                .limit(1)
                .execute()
            )
            event_rows = supabase_client.extract_data(event_response) or []
            if not event_rows:
                raise AppError(
                    code="EVENT_NOT_FOUND",
                    message="Event not found or no permission",
                    details={"event_id": str(event_id)},
                    http_status=404,
                )

            member_response = (
                client.table("organizer_members")
                .select("org_id")
                .eq("org_id", str(event_rows[0]["org_id"]))
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            member_rows = supabase_client.extract_data(member_response) or []
            if not member_rows:
                raise AppError(
                    code="FORBIDDEN",
                    message="You do not have permission to access organizer event detail",
                    details={"event_id": str(event_id)},
                    http_status=403,
                )

            note_response = (
                client.table("event_internal_notes")
                .select("event_id,note,updated_at,updated_by")
                .eq("event_id", str(event_id))
                .limit(1)
                .execute()
            )
            note_rows = supabase_client.extract_data(note_response) or []
            note = note_rows[0].get("note", "") if note_rows else ""

            media_response = (
                client.table("event_media")
                .select("id,event_id,path,sort_order")
                .eq("event_id", str(event_id))
                .order("sort_order", desc=False)
                .execute()
            )
            event_media = supabase_client.extract_data(media_response) or []

            return {"event": event_rows[0], "internal_note": note, "event_media": event_media}
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="ORGANIZER_EVENT_DETAIL_FAILED") from exc

    def upsert_event_internal_note(
        self,
        jwt: str,
        event_id: UUID,
        user_id: str,
        note: str,
    ) -> dict:
        client = supabase_client.authed_client(jwt)
        values = {
            "event_id": str(event_id),
            "note": note,
            "updated_by": user_id,
        }

        try:
            response = client.table("event_internal_notes").upsert(
                values, on_conflict="event_id"
            ).execute()
            rows = supabase_client.extract_data(response) or []
            if rows:
                return rows[0]

            fallback_response = (
                client.table("event_internal_notes")
                .select("event_id,note,updated_at,updated_by")
                .eq("event_id", str(event_id))
                .limit(1)
                .execute()
            )
            fallback_rows = supabase_client.extract_data(fallback_response) or []
            if not fallback_rows:
                raise AppError(
                    code="FORBIDDEN",
                    message="Unable to update internal note",
                    details={"event_id": str(event_id)},
                    http_status=403,
                )
            return fallback_rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="INTERNAL_NOTE_UPSERT_FAILED") from exc

    def create_ticket_type(self, jwt: str, event_id: UUID, payload: dict) -> dict:
        client = supabase_client.authed_client(jwt)

        values = {
            **payload,
            "event_id": str(event_id),
            "price_cents": 0,
            "currency": "TWD",
        }

        try:
            response = client.table("ticket_types").insert(values).execute()
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="FORBIDDEN",
                    message="Unable to create ticket type",
                    http_status=403,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="CREATE_TICKET_TYPE_FAILED") from exc

    def list_attendees(self, jwt: str, event_id: UUID, keyword: str | None = None) -> list[dict]:
        client = supabase_client.authed_client(jwt)

        try:
            ticket_response = (
                client.table("tickets")
                .select("id,user_id,status,checked_in_at,ticket_type_id,event_id,created_at")
                .eq("event_id", str(event_id))
                .order("created_at", desc=False)
                .execute()
            )
            rows = supabase_client.extract_data(ticket_response) or []

            response_rows = (
                client.table("ticket_form_responses")
                .select("ticket_id,answers")
                .eq("event_id", str(event_id))
                .execute()
            )
            answers_rows = supabase_client.extract_data(response_rows) or []
            answers_by_ticket_id = {
                str(row.get("ticket_id")): row.get("answers")
                for row in answers_rows
            }

            for row in rows:
                row["answers"] = answers_by_ticket_id.get(str(row.get("id")))

            if not keyword:
                return rows

            needle = keyword.lower()
            return [
                row
                for row in rows
                if needle in str(row.get("id", "")).lower()
                or needle in str(row.get("user_id", "")).lower()
                or needle in str(row.get("status", "")).lower()
            ]
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="LIST_ATTENDEES_FAILED") from exc

    def resend_attendee_ticket(self, jwt: str, event_id: UUID, ticket_id: UUID) -> None:
        """主辦方代參加者重寄票券信。僅 organizer member 可呼叫。"""
        client = supabase_client.authed_client(jwt)
        try:
            response = (
                client.table("tickets")
                .select("id,event_id,ticket_type_id,user_id,status,issued_at,checked_in_at,qr_secret")
                .eq("id", str(ticket_id))
                .eq("event_id", str(event_id))
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="TICKET_NOT_FOUND",
                    message="Ticket not found",
                    details={"ticket_id": str(ticket_id), "event_id": str(event_id)},
                    http_status=404,
                )
            ticket = rows[0]
            user_id = str(ticket.get("user_id", ""))
            to_email = supabase_client.get_user_email_by_id(user_id)
            event_title = self.get_event_title(event_id)
            frontend_base_url = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:5173")
            email_service.send_ticket_email(to_email, event_title, ticket, frontend_base_url)
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="RESEND_ATTENDEE_TICKET_FAILED") from exc

    def upload_event_media(
        self,
        jwt: str,
        event_id: UUID,
        file_data: bytes,
        content_type: str,
        user_id: str,
    ) -> dict:
        """上傳活動圖片至 Storage 並寫入 event_media。僅 event admin 可呼叫。"""
        # 先確認是 event member（取得 detail 會透過 RLS 檢查）
        detail = self.get_organizer_event_detail(jwt, event_id, user_id)
        if not detail:
            raise AppError(
                code="FORBIDDEN",
                message="Not an organizer of this event",
                http_status=403,
            )
        ext = "jpg"
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"
        elif "gif" in content_type:
            ext = "gif"
        path = f"{event_id}/{uuid.uuid4().hex}.{ext}"
        try:
            sr_client = supabase_client.service_role_client()
            sr_client.storage.from_("event-media").upload(
                path,
                file_data,
                {"content-type": content_type, "upsert": "true"},
            )
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="UPLOAD_EVENT_MEDIA_FAILED") from exc
        client = supabase_client.authed_client(jwt)
        try:
            max_order = 0
            order_resp = (
                client.table("event_media")
                .select("sort_order")
                .eq("event_id", str(event_id))
                .order("sort_order", desc=True)
                .limit(1)
                .execute()
            )
            order_rows = supabase_client.extract_data(order_resp) or []
            if order_rows:
                max_order = int(order_rows[0].get("sort_order") or 0) + 1
            insert_resp = (
                client.table("event_media")
                .insert({"event_id": str(event_id), "path": path, "sort_order": max_order})
                .execute()
            )
            rows = supabase_client.extract_data(insert_resp) or []
            return rows[0] if rows else {"event_id": str(event_id), "path": path, "sort_order": max_order}
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="INSERT_EVENT_MEDIA_FAILED") from exc


events_service = EventsService()
