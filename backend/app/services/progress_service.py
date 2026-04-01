from __future__ import annotations

from uuid import UUID

from app.domain.errors import AppError, map_supabase_error
from app.domain.schemas import EventStageItem

from .supabase_client import supabase_client


class ProgressService:
    """即時活動進度：階段管理 + 進度更新 + 歷史查詢。"""

    # ------------------------------------------------------------------
    # Stages CRUD
    # ------------------------------------------------------------------

    def list_stages(self, event_id: UUID, jwt: str | None = None) -> list[dict]:
        client = supabase_client.authed_client(jwt) if jwt else supabase_client.public_client()
        try:
            resp = (
                client.table("event_stages")
                .select("id,event_id,title,description,sort_order,created_at,updated_at")
                .eq("event_id", str(event_id))
                .order("sort_order")
                .execute()
            )
            return supabase_client.extract_data(resp) or []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="STAGES_LIST_FAILED") from exc

    def replace_stages(
        self,
        jwt: str,
        event_id: UUID,
        user_id: str,
        stages: list[EventStageItem],
    ) -> list[dict]:
        """批量替換活動階段（刪除舊的 → 建立新的）。"""
        from .events_service import events_service

        events_service.require_event_admin(jwt, event_id, user_id)

        client = supabase_client.authed_client(jwt)
        try:
            # 刪除現有階段
            client.table("event_stages").delete().eq("event_id", str(event_id)).execute()

            # 建立新階段
            rows = [
                {
                    "event_id": str(event_id),
                    "title": s.title,
                    "description": s.description,
                    "sort_order": s.sort_order,
                }
                for s in stages
            ]
            resp = client.table("event_stages").insert(rows).execute()
            created = supabase_client.extract_data(resp) or []

            # 初始化 event_progress（如果還沒有的話）
            self._ensure_progress_row(client, event_id, user_id)

            return sorted(created, key=lambda r: r.get("sort_order", 0))
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="STAGES_REPLACE_FAILED") from exc

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def get_progress(self, event_id: UUID, jwt: str | None = None) -> dict | None:
        """取得活動進度（含 current_stage_title 和 current_stage_order）。"""
        client = supabase_client.authed_client(jwt) if jwt else supabase_client.public_client()
        try:
            resp = (
                client.table("event_progress")
                .select("id,event_id,current_stage_id,status,note,updated_by,updated_at")
                .eq("event_id", str(event_id))
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(resp) or []
            if not rows:
                return None

            progress = rows[0]
            stages = self.list_stages(event_id, jwt)
            total_stages = len(stages)
            current_stage_title = None
            current_stage_order = None

            if progress.get("current_stage_id"):
                for s in stages:
                    if str(s["id"]) == str(progress["current_stage_id"]):
                        current_stage_title = s["title"]
                        current_stage_order = s["sort_order"]
                        break

            progress["current_stage_title"] = current_stage_title
            progress["current_stage_order"] = current_stage_order
            progress["total_stages"] = total_stages
            return progress
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="PROGRESS_GET_FAILED") from exc

    def update_progress(
        self,
        jwt: str,
        event_id: UUID,
        user_id: str,
        current_stage_id: UUID | None = None,
        status: str | None = None,
        note: str | None = ...,  # type: ignore[assignment]
    ) -> dict:
        """更新活動進度（切換階段、狀態、備註）。"""
        from .events_service import events_service

        events_service.require_event_admin(jwt, event_id, user_id)

        client = supabase_client.authed_client(jwt)
        try:
            # 確保 progress 存在
            self._ensure_progress_row(client, event_id, user_id)

            update_values: dict = {"updated_by": user_id}

            if current_stage_id is not None:
                # 驗證 stage 屬於此活動
                stage_resp = (
                    client.table("event_stages")
                    .select("id")
                    .eq("id", str(current_stage_id))
                    .eq("event_id", str(event_id))
                    .limit(1)
                    .execute()
                )
                stage_rows = supabase_client.extract_data(stage_resp) or []
                if not stage_rows:
                    raise AppError(
                        code="STAGE_NOT_FOUND",
                        message="Stage does not belong to this event",
                        details={"stage_id": str(current_stage_id)},
                        http_status=400,
                    )
                update_values["current_stage_id"] = str(current_stage_id)

            if status is not None:
                update_values["status"] = status

            if note is not ...:
                update_values["note"] = note

            resp = (
                client.table("event_progress")
                .update(update_values)
                .eq("event_id", str(event_id))
                .execute()
            )
            supabase_client.extract_data(resp)

            return self.get_progress(event_id, jwt)  # type: ignore[return-value]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="PROGRESS_UPDATE_FAILED") from exc

    # ------------------------------------------------------------------
    # Progress Log
    # ------------------------------------------------------------------

    def get_progress_log(self, event_id: UUID, jwt: str | None = None) -> list[dict]:
        client = supabase_client.authed_client(jwt) if jwt else supabase_client.public_client()
        try:
            resp = (
                client.table("event_progress_log")
                .select("id,event_id,stage_id,status,note,changed_by,changed_at")
                .eq("event_id", str(event_id))
                .order("changed_at", desc=True)
                .limit(100)
                .execute()
            )
            log_rows = supabase_client.extract_data(resp) or []

            # enrich with stage titles
            stages = self.list_stages(event_id, jwt)
            stage_map = {str(s["id"]): s["title"] for s in stages}
            for entry in log_rows:
                entry["stage_title"] = stage_map.get(str(entry.get("stage_id") or ""))

            return log_rows
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="PROGRESS_LOG_FAILED") from exc

    # ------------------------------------------------------------------
    # Public: progress + stages for participants
    # ------------------------------------------------------------------

    def get_public_progress(self, event_id: UUID) -> dict:
        """回傳公開的 progress + stages（給參加者）。"""
        progress = self.get_progress(event_id)
        stages = self.list_stages(event_id)
        return {
            "progress": progress,
            "stages": stages,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_progress_row(client, event_id: UUID, user_id: str) -> None:
        """若 event_progress 不存在則建立。"""
        resp = (
            client.table("event_progress")
            .select("id")
            .eq("event_id", str(event_id))
            .limit(1)
            .execute()
        )
        rows = supabase_client.extract_data(resp) or []
        if not rows:
            client.table("event_progress").insert(
                {
                    "event_id": str(event_id),
                    "status": "not_started",
                    "updated_by": user_id,
                }
            ).execute()


progress_service = ProgressService()
