from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from flask import current_app

from app.domain.errors import AppError, map_supabase_error

from .audit_service import audit_service
from .email_service import email_service
from .supabase_client import supabase_client

UTC = getattr(datetime, "UTC", timezone(timedelta(0)))
EVENT_PUBLIC_SELECT = (
    "id,org_id,title,description,short_desc,start_at,end_at,timezone,location_name,"
    "location_address,map_url,contact_email,contact_phone,registration_start_at,"
    "registration_end_at,socials,eligibility,event_language,checkin_open_at,checkin_note,"
    "schedule,rules,refund_policy,status,published_at,dance_styles,event_types"
)


def _escape_like_pattern(s: str) -> str:
    """PostgreSQL LIKE：將使用者字元中的 % _ \\ 跳脫為字面比對。"""
    return "".join("\\" + c if c in ("%", "_", "\\") else c for c in s)


def _apply_keyword_search(query, q: str | None):
    """
    關鍵字搜尋：標題、短描述、地點名稱、地址（ILIKE 不分大小寫，多欄 OR）。
    PostgREST or() 以逗號分隔條件，故搜尋字串內逗號改空白；含空白時值需雙引號包起來。
    """
    raw = (q or "").strip()
    if not raw:
        return query
    cleaned = raw.replace(",", " ").replace('"', "").strip()
    if len(cleaned) > 200:
        cleaned = cleaned[:200].strip()
    if not cleaned:
        return query
    pat = f"%{_escape_like_pattern(cleaned)}%"
    # PostgREST：值含空白或保留字時以雙引號包住（內部 " 改為 ""）
    quoted = '"' + pat.replace('"', '""') + '"'
    return query.or_(
        f"title.ilike.{quoted},short_desc.ilike.{quoted},"
        f"location_name.ilike.{quoted},location_address.ilike.{quoted}"
    )


class EventsService:
    @staticmethod
    def _pg_array_literal(values: list[str]) -> str:
        # PostgREST overlap filter expects postgres array literal, e.g. "{hiphop,popping}".
        escaped = [value.replace('"', '\\"') for value in values]
        return "{" + ",".join(escaped) + "}"

    @staticmethod
    def _fetch_total_sold_per_event(client, event_ids: list[str]) -> dict[str, int]:
        """MVP-3.5: Return {event_id: total_sold_count} from ticket_types.sold_count sum."""
        if not event_ids:
            return {}
        try:
            resp = (
                client.table("ticket_types")
                .select("event_id,sold_count")
                .in_("event_id", event_ids)
                .execute()
            )
            rows = supabase_client.extract_data(resp) or []
            totals: dict[str, int] = {eid: 0 for eid in event_ids}
            for r in rows:
                eid = str(r.get("event_id", ""))
                if eid:
                    totals[eid] = totals.get(eid, 0) + int(r.get("sold_count") or 0)
            return totals
        except Exception as exc:
            current_app.logger.warning(f"Error: {exc}")
            return {eid: 0 for eid in event_ids}

    def list_events(
        self,
        q: str | None = None,
        from_at: str | None = None,
        to_at: str | None = None,
        org_id: str | None = None,
        styles: list[str] | None = None,
        types: list[str] | None = None,
        sort: str | None = None,
    ) -> list[dict]:
        client = supabase_client.public_client()

        query = client.table("events").select(EVENT_PUBLIC_SELECT)
        query = query.eq("status", "published")

        if org_id:
            query = query.eq("org_id", org_id)

        query = _apply_keyword_search(query, q)

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
            events = supabase_client.extract_data(response) or []
            if not events:
                return []
            event_ids = [str(e["id"]) for e in events]
            thumbs = self._fetch_first_thumbnail_per_event(client, event_ids)
            for e in events:
                e["thumbnail_path"] = thumbs.get(str(e["id"]))

            # MVP-3.5: 熱門排序（售票數、報名數）
            if sort == "hot":
                totals = self._fetch_total_sold_per_event(client, event_ids)
                for e in events:
                    e["total_sold_count"] = totals.get(str(e["id"]), 0)
                events.sort(
                    key=lambda x: (
                        -(x.get("total_sold_count") or 0),
                        x.get("start_at") or "",
                    )
                )
            else:
                for e in events:
                    e["total_sold_count"] = None
            return events
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="EVENTS_LIST_FAILED") from exc

    @staticmethod
    def _fetch_first_thumbnail_per_event(client, event_ids: list[str]) -> dict[str, str]:
        """Return {event_id: path} for first media (by sort_order) per event."""
        if not event_ids:
            return {}
        try:
            resp = (
                client.table("event_media")
                .select("event_id,path,sort_order")
                .in_("event_id", event_ids)
                .order("event_id")
                .order("sort_order")
                .execute()
            )
            rows = supabase_client.extract_data(resp) or []
            seen: dict[str, str] = {}
            for r in rows:
                eid = str(r.get("event_id", ""))
                if eid and eid not in seen:
                    seen[eid] = str(r.get("path", ""))
            return seen
        except Exception as exc:
            current_app.logger.warning(f"Error: {exc}")
            return {}

    def list_public_events(
        self,
        q: str | None = None,
        from_at: str | None = None,
        to_at: str | None = None,
        org_id: str | None = None,
        styles: list[str] | None = None,
        types: list[str] | None = None,
        sort: str | None = None,
    ) -> list[dict]:
        return self.list_events(
            q=q,
            from_at=from_at,
            to_at=to_at,
            org_id=org_id,
            styles=styles,
            types=types,
            sort=sort,
        )

    def list_admin_events(
        self,
        q: str | None = None,
        from_at: str | None = None,
        to_at: str | None = None,
        org_id: str | None = None,
    ) -> list[dict]:
        """Admin: 全站活動（含 draft/cancelled/ended/disabled），不 filter status。"""
        client = supabase_client.service_role_client()
        query = client.table("events").select(EVENT_PUBLIC_SELECT)
        if org_id:
            query = query.eq("org_id", org_id)
        query = _apply_keyword_search(query, q)
        if from_at:
            query = query.gte("start_at", from_at)
        if to_at:
            query = query.lte("start_at", to_at)
        try:
            response = query.order("start_at", desc=False).execute()
            return supabase_client.extract_data(response) or []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="ADMIN_EVENTS_LIST_FAILED") from exc

    def list_admin_organizations(self, status: str | None = None) -> list[dict]:
        """Admin: 全站主辦方，可依 approval_status 篩選。MVP-3.2。"""
        client = supabase_client.service_role_client()
        org_select = (
            "id,name,description,contact_email,owner_user_id,approval_status,"
            "approved_at,approved_by,rejection_reason,created_at"
        )
        query = client.table("organizations").select(org_select)
        if status:
            query = query.eq("approval_status", status)
        try:
            response = query.order("created_at", desc=True).execute()
            return supabase_client.extract_data(response) or []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="ADMIN_ORGANIZATIONS_LIST_FAILED") from exc

    def admin_approve_organization(
        self,
        org_id: UUID,
        status: str,
        admin_user_id: str,
        rejection_reason: str | None = None,
    ) -> dict:
        """Admin: 審核主辦方通過/退件。MVP-3.2。"""
        if status not in ("approved", "rejected"):
            raise AppError(
                code="VALIDATION_ERROR",
                message="status must be approved or rejected",
                details={"status": status},
                http_status=400,
            )
        client = supabase_client.service_role_client()
        now = datetime.now(UTC).isoformat()
        update_values: dict = {
            "approval_status": status,
            "approved_at": now if status == "approved" else None,
            "approved_by": admin_user_id if status == "approved" else None,
            "rejection_reason": rejection_reason if status == "rejected" else None,
        }
        try:
            response = (
                client.table("organizations").update(update_values).eq("id", str(org_id)).execute()
            )
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="ORGANIZATION_NOT_FOUND",
                    message="Organization not found",
                    details={"org_id": str(org_id)},
                    http_status=404,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(
                exc, fallback_code="ADMIN_ORGANIZATION_APPROVAL_FAILED"
            ) from exc

    def get_event_title(self, event_id: UUID) -> str:
        """取得活動標題（供 email 等使用，不檢查 published）。"""
        client = supabase_client.public_client()
        try:
            response = (
                client.table("events").select("title").eq("id", str(event_id)).limit(1).execute()
            )
            rows = supabase_client.extract_data(response) or []
            return rows[0].get("title", "活動") if rows else "活動"
        except Exception as exc:
            current_app.logger.warning(f"Error: {exc}")
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

            # Live progress
            from .progress_service import progress_service

            progress_data = progress_service.get_public_progress(event_id)

            return {
                "event": event,
                "event_media": supabase_client.extract_data(media_response) or [],
                "ticket_types": supabase_client.extract_data(ticket_type_response) or [],
                "organizer": organizer,
                "other_events": other_events,
                "progress": progress_data.get("progress"),
                "stages": progress_data.get("stages", []),
            }
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="EVENT_DETAIL_FAILED") from exc

    def get_my_organizer_summary(self, jwt: str, user_id: str) -> dict:
        """回傳目前使用者所屬主辦方與其底下的活動（供個人資料頁使用）。"""
        client = supabase_client.authed_client(jwt)
        try:
            members_resp = (
                client.table("organizer_members")
                .select("org_id,role")
                .eq("user_id", user_id)
                .execute()
            )
            members = supabase_client.extract_data(members_resp) or []
            if not members:
                return {"organizations": [], "events": []}
            org_ids = [str(m["org_id"]) for m in members]
            role_by_org = {str(m["org_id"]): m.get("role", "staff") for m in members}
            orgs_resp = (
                client.table("organizations")
                .select("id,name,approval_status")
                .in_("id", org_ids)
                .execute()
            )
            orgs_rows = supabase_client.extract_data(orgs_resp) or []
            organizations = [
                {
                    "id": o["id"],
                    "name": o["name"],
                    "role": role_by_org.get(str(o["id"]), "staff"),
                    "approval_status": o.get("approval_status", "approved"),
                }
                for o in orgs_rows
            ]
            events_resp = (
                client.table("events")
                .select("id,org_id,title,status,start_at")
                .in_("org_id", org_ids)
                .order("start_at", desc=True)
                .limit(100)
                .execute()
            )
            events_rows = supabase_client.extract_data(events_resp) or []
            events = [
                {
                    "id": e["id"],
                    "org_id": e["org_id"],
                    "title": e["title"],
                    "status": e.get("status", "draft"),
                    "start_at": e.get("start_at"),
                }
                for e in events_rows
            ]
            return {"organizations": organizations, "events": events}
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="MY_ORGANIZER_SUMMARY_FAILED") from exc

    def _get_org_role(self, jwt: str, org_id: str, user_id: str) -> str | None:
        """取得 user 在 org 的 role；非成員回 None。MVP-3.1。"""
        client = supabase_client.authed_client(jwt)
        try:
            resp = (
                client.table("organizer_members")
                .select("role")
                .eq("org_id", org_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(resp) or []
            return rows[0].get("role") if rows else None
        except Exception as exc:
            current_app.logger.warning(f"Error: {exc}")
            return None

    def require_org_admin(self, jwt: str, org_id: str, user_id: str) -> None:
        """僅 owner/admin 可管理；staff 拋 STAFF_CANNOT_MANAGE。MVP-3.1。"""
        role = self._get_org_role(jwt, org_id, user_id)
        if role is None:
            raise AppError(
                code="FORBIDDEN",
                message="You are not a member of this organization",
                http_status=403,
            )
        if role == "staff":
            raise AppError(
                code="STAFF_CANNOT_MANAGE",
                message="Staff role cannot create or edit events. Only owner or admin can.",
                http_status=403,
            )

    def list_org_members(self, jwt: str, org_id: str, user_id: str) -> list[dict]:
        """MVP-3.1: 列出主辦方成員。僅 owner/admin 可呼叫。"""
        self.require_org_admin(jwt, org_id, user_id)
        client = supabase_client.authed_client(jwt)
        try:
            resp = (
                client.table("organizer_members")
                .select("user_id,org_id,role,created_at")
                .eq("org_id", org_id)
                .order("created_at", desc=False)
                .execute()
            )
            return supabase_client.extract_data(resp) or []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="LIST_ORG_MEMBERS_FAILED") from exc

    def add_org_member(
        self,
        jwt: str,
        org_id: str,
        target_user_id: str,
        role: str,
        actor_user_id: str,
    ) -> dict:
        """MVP-3.1: 新增成員。僅 owner/admin 可呼叫，role 限 admin|staff。"""
        self.require_org_admin(jwt, org_id, actor_user_id)
        if role not in ("admin", "staff"):
            raise AppError(
                code="VALIDATION_ERROR",
                message="New member role must be admin or staff",
                details={"role": role},
                http_status=400,
            )
        client = supabase_client.authed_client(jwt)
        try:
            resp = (
                client.table("organizer_members")
                .insert(
                    {
                        "org_id": org_id,
                        "user_id": target_user_id,
                        "role": role,
                    }
                )
                .execute()
            )
            rows = supabase_client.extract_data(resp) or []
            if not rows:
                raise AppError(
                    code="FORBIDDEN",
                    message="Unable to add member",
                    http_status=403,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="ADD_ORG_MEMBER_FAILED") from exc

    def update_org_member_role(
        self,
        jwt: str,
        org_id: str,
        target_user_id: str,
        new_role: str,
        actor_user_id: str,
    ) -> dict:
        """MVP-3.1: 修改成員 role。owner 可改任意；admin 不可將任何人改為 owner。"""
        self.require_org_admin(jwt, org_id, actor_user_id)
        actor_role = self._get_org_role(jwt, org_id, actor_user_id)
        if actor_role == "admin" and new_role == "owner":
            raise AppError(
                code="FORBIDDEN",
                message="Admin cannot assign owner role",
                details={"target_user_id": target_user_id},
                http_status=403,
            )
        client = supabase_client.authed_client(jwt)
        try:
            resp = (
                client.table("organizer_members")
                .update({"role": new_role})
                .eq("org_id", org_id)
                .eq("user_id", target_user_id)
                .execute()
            )
            rows = supabase_client.extract_data(resp) or []
            if not rows:
                raise AppError(
                    code="MEMBER_NOT_FOUND",
                    message="Member not found",
                    details={"org_id": org_id, "user_id": target_user_id},
                    http_status=404,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="UPDATE_ORG_MEMBER_FAILED") from exc

    def remove_org_member(
        self,
        jwt: str,
        org_id: str,
        target_user_id: str,
        actor_user_id: str,
    ) -> None:
        """MVP-3.1: 移除成員。owner/admin 可刪；不可刪自己為唯一 owner。"""
        self.require_org_admin(jwt, org_id, actor_user_id)
        if target_user_id == actor_user_id:
            # 檢查是否為唯一 owner
            client = supabase_client.authed_client(jwt)
            owners = (
                client.table("organizer_members")
                .select("user_id")
                .eq("org_id", org_id)
                .eq("role", "owner")
                .execute()
            )
            owner_rows = supabase_client.extract_data(owners) or []
            if len(owner_rows) <= 1:
                raise AppError(
                    code="FORBIDDEN",
                    message="Cannot remove the only owner. Transfer ownership first.",
                    http_status=403,
                )
        client = supabase_client.authed_client(jwt)
        try:
            client.table("organizer_members").delete().eq("org_id", org_id).eq(
                "user_id", target_user_id
            ).execute()
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="REMOVE_ORG_MEMBER_FAILED") from exc

    def require_event_admin(self, jwt: str, event_id: UUID, user_id: str) -> None:
        """僅 event 所屬 org 的 owner/admin 可管理；staff 拋 STAFF_CANNOT_MANAGE。MVP-3.1。"""
        client = supabase_client.authed_client(jwt)
        try:
            resp = (
                client.table("events").select("org_id").eq("id", str(event_id)).limit(1).execute()
            )
            rows = supabase_client.extract_data(resp) or []
            if not rows:
                raise AppError(
                    code="EVENT_NOT_FOUND",
                    message="Event not found",
                    details={"event_id": str(event_id)},
                    http_status=404,
                )
            org_id = str(rows[0].get("org_id", ""))
            self.require_org_admin(jwt, org_id, user_id)
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(
                exc, fallback_code="ORGANIZER_PERMISSION_CHECK_FAILED"
            ) from exc

    def require_event_member(self, jwt: str, event_id: UUID, user_id: str) -> None:
        """event 所屬 org 的任何成員（owner/admin/staff）皆可存取。"""
        client = supabase_client.authed_client(jwt)
        try:
            resp = (
                client.table("events").select("org_id").eq("id", str(event_id)).limit(1).execute()
            )
            rows = supabase_client.extract_data(resp) or []
            if not rows:
                raise AppError(
                    code="EVENT_NOT_FOUND",
                    message="Event not found",
                    details={"event_id": str(event_id)},
                    http_status=404,
                )
            org_id = str(rows[0].get("org_id", ""))
            role = self._get_org_role(jwt, org_id, user_id)
            if role is None:
                raise AppError(
                    code="FORBIDDEN",
                    message="You are not a member of this organization",
                    http_status=403,
                )
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(
                exc, fallback_code="ORGANIZER_PERMISSION_CHECK_FAILED"
            ) from exc

    def _require_org_approved(self, jwt: str, org_id: str) -> None:
        """MVP-3.2: 僅 approval_status=approved 的 org 可建立活動。"""
        client = supabase_client.authed_client(jwt)
        resp = (
            client.table("organizations")
            .select("approval_status")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )
        rows = supabase_client.extract_data(resp) or []
        if not rows:
            raise AppError(
                code="ORGANIZATION_NOT_FOUND",
                message="Organization not found",
                details={"org_id": org_id},
                http_status=404,
            )
        status = (rows[0].get("approval_status") or "").strip()
        if status != "approved":
            raise AppError(
                code="ORG_NOT_APPROVED",
                message=(
                    "Organization is pending approval. "
                    "You cannot create events until Admin approves."
                ),
                details={"approval_status": status},
                http_status=403,
            )

    def apply_organizer(self, jwt: str, user_id: str, payload: dict) -> dict:
        """申請主辦方。ORG_APPROVAL_REQUIRED=True 時新 org 為 pending，需 Admin 審核。"""
        client = supabase_client.authed_client(jwt)
        approval_required = current_app.config.get("ORG_APPROVAL_REQUIRED", False)
        approval_status = "pending" if approval_required else "approved"

        values = {
            "name": payload["name"],
            "description": payload.get("description"),
            "contact_email": payload.get("contact_email"),
            "logo_url": payload.get("logo_url"),
            "owner_user_id": user_id,
            "approval_status": approval_status,
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
        """建立活動。僅 org approval_status=approved 時可建立。MVP-3.2。"""
        org_id = str(payload.get("org_id", ""))
        self.require_org_admin(jwt, org_id, user_id)
        self._require_org_approved(jwt, org_id)
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

    def admin_update_event_status(
        self, event_id: UUID, status: str, admin_user_id: str | None = None
    ) -> dict:
        """Admin 下架：僅允許將 status 改為 disabled 或 cancelled。"""
        if status not in ("disabled", "cancelled"):
            raise AppError(
                code="VALIDATION_ERROR",
                message="Admin can only set status to disabled or cancelled",
                details={"status": status},
                http_status=400,
            )
        client = supabase_client.service_role_client()
        try:
            response = (
                client.table("events").update({"status": status}).eq("id", str(event_id)).execute()
            )
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="EVENT_NOT_FOUND",
                    message="Event not found",
                    details={"event_id": str(event_id)},
                    http_status=404,
                )
            if admin_user_id:
                from app.services.audit_service import audit_service

                audit_service.log_unpublish(event_id, admin_user_id, status)
            # MVP-3.5: 活動取消/下架時通知參加者
            try:
                from app.services.event_notification_service import event_notification_service

                event_notification_service.notify_event_cancelled(
                    event_id, rows[0].get("title", "活動")
                )
            except Exception as exc:
                current_app.logger.warning(
                    "[events] notify_event_cancelled failed event=%s: %s", event_id, exc
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="ADMIN_UPDATE_EVENT_FAILED") from exc

    def update_event(self, jwt: str, event_id: UUID, payload: dict, user_id: str) -> dict:
        self.require_event_admin(jwt, event_id, user_id)
        client = supabase_client.authed_client(jwt)

        # MVP-3.5: 取得舊資料以便異動後通知參加者
        old_event: dict | None = None
        if any(k in payload for k in ("start_at", "end_at", "status")):
            try:
                resp = (
                    client.table("events")
                    .select("start_at,end_at,status,title")
                    .eq("id", str(event_id))
                    .limit(1)
                    .execute()
                )
                old_rows = supabase_client.extract_data(resp) or []
                old_event = old_rows[0] if old_rows else None
            except Exception as exc:
                current_app.logger.warning(f"Error: {exc}")
                old_event = None

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
                client.table("events").update(update_values).eq("id", str(event_id)).execute()
            )
            rows = supabase_client.extract_data(response) or []
            if not rows:
                raise AppError(
                    code="EVENT_NOT_FOUND",
                    message="Event not found or no permission",
                    details={"event_id": str(event_id)},
                    http_status=404,
                )
            updated = rows[0]

            # MVP-3.5: 異動/取消通知
            if old_event:
                try:
                    from app.services.event_notification_service import (
                        event_notification_service,
                    )

                    title = updated.get("title", old_event.get("title", "活動"))
                    new_status = updated.get("status") or old_event.get("status")

                    if new_status in ("cancelled", "disabled"):
                        event_notification_service.notify_event_cancelled(event_id, title)
                    else:
                        old_start = old_event.get("start_at")
                        new_start = updated.get("start_at") or old_start
                        if old_start and new_start and str(old_start) != str(new_start):
                            old_s = (
                                old_start.strftime("%Y-%m-%d %H:%M")
                                if hasattr(old_start, "strftime")
                                else str(old_start)
                            )
                            new_s = (
                                new_start.strftime("%Y-%m-%d %H:%M")
                                if hasattr(new_start, "strftime")
                                else str(new_start)
                            )
                            event_notification_service.notify_event_time_changed(
                                event_id, title, old_s, new_s
                            )
                except Exception as exc:
                    current_app.logger.warning(
                        "[events] notify_event_change failed event=%s: %s", event_id, exc
                    )

            return updated
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

            ticket_types_response = (
                client.table("ticket_types")
                .select(
                    "id,event_id,name,description,price_cents,currency,capacity,sold_count,per_user_limit,sale_start_at,sale_end_at,is_active"
                )
                .eq("event_id", str(event_id))
                .order("created_at", desc=False)
                .execute()
            )
            ticket_types = supabase_client.extract_data(ticket_types_response) or []

            return {
                "event": event_rows[0],
                "internal_note": note,
                "event_media": event_media,
                "ticket_types": ticket_types,
            }
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
            response = (
                client.table("event_internal_notes")
                .upsert(values, on_conflict="event_id")
                .execute()
            )
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

    def create_ticket_type(self, jwt: str, event_id: UUID, payload: dict, user_id: str) -> dict:
        self.require_event_admin(jwt, event_id, user_id)
        client = supabase_client.authed_client(jwt)

        values = {
            **payload,
            "event_id": str(event_id),
            "price_cents": payload.get("price_cents", 0),
            "currency": payload.get("currency", "TWD"),
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

    def update_ticket_type(
        self,
        jwt: str,
        event_id: UUID,
        ticket_type_id: UUID,
        payload: dict,
        user_id: str,
    ) -> dict:
        """更新票種。capacity 不可小於 sold_count。"""
        self.require_event_admin(jwt, event_id, user_id)
        client = supabase_client.authed_client(jwt)
        try:
            existing = (
                client.table("ticket_types")
                .select("id,event_id,capacity,sold_count")
                .eq("id", str(ticket_type_id))
                .eq("event_id", str(event_id))
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(existing) or []
            if not rows:
                raise AppError(
                    code="TICKET_TYPE_NOT_FOUND",
                    message="Ticket type not found or no permission",
                    details={"ticket_type_id": str(ticket_type_id), "event_id": str(event_id)},
                    http_status=404,
                )
            sold_count = int(rows[0].get("sold_count") or 0)
            new_capacity = payload.get("capacity")
            if new_capacity is not None and new_capacity < sold_count:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="名額不可小於已售出數量",
                    details={"sold_count": sold_count, "capacity": new_capacity},
                    http_status=400,
                )
            update_values = {k: v for k, v in payload.items() if v is not None}
            if not update_values:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="No updatable fields provided",
                    http_status=400,
                )
            response = (
                client.table("ticket_types")
                .update(update_values)
                .eq("id", str(ticket_type_id))
                .eq("event_id", str(event_id))
                .execute()
            )
            result = supabase_client.extract_data(response) or []
            if not result:
                raise AppError(
                    code="TICKET_TYPE_NOT_FOUND",
                    message="Ticket type not found or no permission",
                    details={"ticket_type_id": str(ticket_type_id), "event_id": str(event_id)},
                    http_status=404,
                )
            return result[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="UPDATE_TICKET_TYPE_FAILED") from exc

    def delete_ticket_type(
        self, jwt: str, event_id: UUID, ticket_type_id: UUID, user_id: str
    ) -> None:
        """刪除票種。已售出（sold_count > 0）不可刪除。"""
        self.require_event_admin(jwt, event_id, user_id)
        client = supabase_client.authed_client(jwt)
        try:
            existing = (
                client.table("ticket_types")
                .select("id,event_id,sold_count")
                .eq("id", str(ticket_type_id))
                .eq("event_id", str(event_id))
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(existing) or []
            if not rows:
                raise AppError(
                    code="TICKET_TYPE_NOT_FOUND",
                    message="Ticket type not found or no permission",
                    details={"ticket_type_id": str(ticket_type_id), "event_id": str(event_id)},
                    http_status=404,
                )
            sold_count = int(rows[0].get("sold_count") or 0)
            if sold_count > 0:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="已售出票種不可刪除",
                    details={"sold_count": sold_count},
                    http_status=400,
                )
            client.table("ticket_types").delete().eq("id", str(ticket_type_id)).eq(
                "event_id", str(event_id)
            ).execute()
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="DELETE_TICKET_TYPE_FAILED") from exc

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

            tt_resp = (
                client.table("ticket_types")
                .select("id,name")
                .eq("event_id", str(event_id))
                .execute()
            )
            tt_rows = supabase_client.extract_data(tt_resp) or []
            type_name_by_id = {str(r.get("id")): (r.get("name") or "").strip() for r in tt_rows}

            user_ids = list({str(r.get("user_id")) for r in rows if r.get("user_id")})
            display_by_uid: dict[str, str] = {}
            if user_ids:
                sr = supabase_client.service_role_client()
                pr = sr.table("profiles").select("id,display_name").in_("id", user_ids).execute()
                prow = supabase_client.extract_data(pr) or []
                display_by_uid = {
                    str(p.get("id")): (p.get("display_name") or "").strip() for p in prow
                }

            response_rows = (
                client.table("ticket_form_responses")
                .select("ticket_id,answers")
                .eq("event_id", str(event_id))
                .execute()
            )
            answers_rows = supabase_client.extract_data(response_rows) or []
            answers_by_ticket_id = {
                str(row.get("ticket_id")): row.get("answers") for row in answers_rows
            }

            for row in rows:
                row["answers"] = answers_by_ticket_id.get(str(row.get("id")))
                tid = str(row.get("ticket_type_id") or "")
                row["ticket_type_name"] = type_name_by_id.get(tid) or ""
                uid = str(row.get("user_id") or "")
                row["user_display_name"] = display_by_uid.get(uid) or ""

            if not keyword:
                return rows

            needle = keyword.lower()
            return [
                row
                for row in rows
                if needle in str(row.get("id", "")).lower()
                or needle in str(row.get("user_id", "")).lower()
                or needle in str(row.get("status", "")).lower()
                or needle in str(row.get("ticket_type_name", "")).lower()
                or needle in str(row.get("user_display_name", "")).lower()
            ]
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="LIST_ATTENDEES_FAILED") from exc

    def resend_attendee_ticket(self, jwt: str, event_id: UUID, ticket_id: UUID) -> None:
        """主辦方代參加者重寄票券信。僅 organizer member 可呼叫。"""
        client = supabase_client.authed_client(jwt)
        try:
            response = (
                client.table("tickets")
                .select(
                    "id,event_id,ticket_type_id,user_id,status,issued_at,checked_in_at,qr_secret"
                )
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
            if not to_email or not to_email.strip():
                # Fallback: email from registration form answers (e.g. 報名表單 email 欄位)
                try:
                    ans_resp = (
                        client.table("ticket_form_responses")
                        .select("answers")
                        .eq("ticket_id", str(ticket_id))
                        .eq("event_id", str(event_id))
                        .limit(1)
                        .execute()
                    )
                    ans_rows = supabase_client.extract_data(ans_resp) or []
                    answers = (ans_rows[0] or {}).get("answers") if ans_rows else {}
                    if isinstance(answers, dict):
                        to_email = (answers.get("email") or answers.get("信箱") or "").strip()
                except Exception as exc:
                    current_app.logger.warning(f"Error: {exc}")
                    to_email = ""
            if not to_email or not to_email.strip():
                raise AppError(
                    code="ATTENDEE_NO_EMAIL",
                    message="該參加者帳號無信箱，無法重寄票券",
                    details={"ticket_id": str(ticket_id), "user_id": user_id},
                    http_status=400,
                )
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
            return (
                rows[0]
                if rows
                else {"event_id": str(event_id), "path": path, "sort_order": max_order}
            )
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="INSERT_EVENT_MEDIA_FAILED") from exc

    def create_comp_ticket(
        self,
        jwt: str,
        event_id: UUID,
        ticket_type_id: UUID,
        email: str | None,
        user_id: str | None,
        note: str | None,
        actor_user_id: str,
        *,
        skip_permission_check: bool = False,
        actor_type: str | None = None,
    ) -> dict:
        """手動補票（公關票）。MVP-3.4。需 event admin（或 Admin 免檢），不建立 order。"""
        if not skip_permission_check:
            self.require_event_admin(jwt, event_id, actor_user_id)
        recipient_id = user_id
        if email:
            recipient_id = supabase_client.get_user_id_by_email(email)
            if not recipient_id:
                raise AppError(
                    code="USER_NOT_FOUND",
                    message="No user found with this email",
                    details={"email": email},
                    http_status=404,
                )
        if not recipient_id:
            raise AppError(
                code="VALIDATION_ERROR",
                message="Provide email or user_id",
                http_status=400,
            )
        sr = supabase_client.service_role_client()
        tt_resp = (
            sr.table("ticket_types")
            .select("id,event_id,capacity,sold_count")
            .eq("id", str(ticket_type_id))
            .eq("event_id", str(event_id))
            .limit(1)
            .execute()
        )
        tt_rows = supabase_client.extract_data(tt_resp) or []
        if not tt_rows:
            raise AppError(
                code="TICKET_TYPE_NOT_FOUND",
                message="Ticket type not found or does not belong to this event",
                details={"ticket_type_id": str(ticket_type_id)},
                http_status=404,
            )
        tt = tt_rows[0]
        sold = int(tt.get("sold_count") or 0)
        cap = int(tt.get("capacity") or 0)
        if sold >= cap:
            raise AppError(
                code="CAPACITY_EXCEEDED",
                message="Ticket type is sold out",
                details={"sold_count": sold, "capacity": cap},
                http_status=409,
            )
        qr_secret = secrets.token_hex(16)
        ticket_row = {
            "event_id": str(event_id),
            "ticket_type_id": str(ticket_type_id),
            "user_id": str(recipient_id),
            "order_id": None,
            "qr_secret": qr_secret,
            "status": "issued",
        }
        ins = sr.table("tickets").insert(ticket_row).execute()
        ticket_data = supabase_client.extract_data(ins) or []
        if isinstance(ticket_data, dict):
            ticket_data = [ticket_data]
        if not ticket_data:
            raise AppError(
                code="COMP_TICKET_FAILED",
                message="Failed to create ticket",
                http_status=500,
            )
        ticket = ticket_data[0]
        ticket_uuid = ticket.get("id")
        sr.table("ticket_types").update({"sold_count": sold + 1}).eq(
            "id", str(ticket_type_id)
        ).execute()
        audit_service.log_comp_ticket(
            ticket_id=UUID(str(ticket_uuid)),
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            recipient_user_id=str(recipient_id),
            actor_type=actor_type or audit_service.ACTOR_ORGANIZER,
            actor_id=actor_user_id,
            note=note,
        )
        event_title = self.get_event_title(event_id) or "活動"
        frontend_url = current_app.config.get("FRONTEND_BASE_URL", "").rstrip("/")
        to_email = supabase_client.get_user_email_by_id(str(recipient_id))
        if to_email:
            try:
                email_service.send_ticket_email(to_email, event_title, ticket, frontend_url)
            except Exception as exc:
                current_app.logger.warning("[comp_ticket] send_ticket_email failed: %s", exc)
        return ticket


events_service = EventsService()
