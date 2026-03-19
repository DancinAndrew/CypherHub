"""MVP-3.3: 結算與提款。develop.md mvp3-master-plan 四。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from flask import current_app

from app.domain.errors import AppError, map_supabase_error

from .audit_service import audit_service
from .events_service import events_service
from .supabase_client import supabase_client

UTC = getattr(datetime, "UTC", timezone(timedelta(0)))


class SettlementService:
    """結算批次產生、主辦方查詢、提款申請。"""

    def generate_settlements(
        self,
        period_start: datetime,
        period_end: datetime,
        admin_user_id: str | None = None,
    ) -> list[dict]:
        """
        產生結算批次。需 Admin 權限（由 blueprint 檢查）。
        彙總 period 內 status in (paid, issued) 的訂單，依 org 分組計算 gross、platform_fee、net。
        """
        sr = supabase_client.service_role_client()
        rate = float(current_app.config.get("PLATFORM_FEE_RATE", 0.05))

        # 查詢 period 內已付款/出票訂單的 order_items，含 org_id
        # order updated_at 在期間內；join order_items, ticket_types, events
        try:
            order_resp = (
                sr.table("orders")
                .select("id,updated_at")
                .in_("status", ["paid", "issued"])
                .gte("updated_at", period_start.isoformat())
                .lt("updated_at", period_end.isoformat())
                .execute()
            )
            order_rows = supabase_client.extract_data(order_resp) or []
            if not order_rows:
                return []

            order_ids = [str(r["id"]) for r in order_rows]
            items_resp = (
                sr.table("order_items")
                .select("order_id,ticket_type_id,quantity,price_cents")
                .in_("order_id", order_ids)
                .execute()
            )
            items = supabase_client.extract_data(items_resp) or []
            if not items:
                return []

            # 取得 ticket_type -> event -> org
            tt_ids = list({str(r["ticket_type_id"]) for r in items})
            tt_resp = (
                sr.table("ticket_types")
                .select("id,event_id")
                .in_("id", tt_ids)
                .execute()
            )
            tt_rows = supabase_client.extract_data(tt_resp) or []
            tt_to_event = {str(r["id"]): str(r["event_id"]) for r in tt_rows}
            event_ids = list(tt_to_event.values())
            ev_resp = (
                sr.table("events")
                .select("id,org_id")
                .in_("id", event_ids)
                .execute()
            )
            ev_rows = supabase_client.extract_data(ev_resp) or []
            event_to_org = {str(r["id"]): str(r["org_id"]) for r in ev_rows}

            org_gross: dict[str, int] = {}
            for it in items:
                ev_id = tt_to_event.get(str(it["ticket_type_id"]))
                org_id = event_to_org.get(ev_id, "") if ev_id else ""
                if org_id:
                    amt = (it.get("quantity") or 0) * (it.get("price_cents") or 0)
                    org_gross[org_id] = org_gross.get(org_id, 0) + amt

            if not org_gross:
                return []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="SETTLEMENT_GENERATE_FAILED") from exc

        results: list[dict] = []
        now = datetime.now(UTC).isoformat()

        for org_id, gross_cents in org_gross.items():
            platform_fee_cents = int(gross_cents * rate)
            net_cents = gross_cents - platform_fee_cents

            set_row = {
                "org_id": org_id,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "gross_cents": gross_cents,
                "platform_fee_cents": platform_fee_cents,
                "net_cents": net_cents,
                "status": "finalized",
            }
            set_resp = sr.table("settlements").insert(set_row).execute()
            set_data = supabase_client.extract_data(set_resp) or []
            if isinstance(set_data, dict):
                set_data = [set_data]
            if not set_data:
                continue
            settlement = set_data[0]
            set_id = settlement.get("id")

            # ledger: sale (+gross), platform_fee (-fee)
            sr.table("ledger_entries").insert({
                "org_id": org_id,
                "type": "sale",
                "amount_cents": gross_cents,
                "settlement_id": set_id,
            }).execute()
            sr.table("ledger_entries").insert({
                "org_id": org_id,
                "type": "platform_fee",
                "amount_cents": -platform_fee_cents,
                "settlement_id": set_id,
            }).execute()

            results.append(settlement)

        if admin_user_id:
            audit_service.log_settlement_generate(
                admin_user_id,
                period_start.isoformat(),
                period_end.isoformat(),
                len(results),
            )
        return results

    def list_settlements_for_org(self, jwt: str, user_id: str) -> list[dict]:
        """主辦方看自己所有 org 的結算列表。"""
        summary = events_service.get_my_organizer_summary(jwt, user_id)
        org_ids = [str(o["id"]) for o in (summary.get("organizations") or [])]
        if not org_ids:
            return []

        client = supabase_client.authed_client(jwt)
        try:
            resp = (
                client.table("settlements")
                .select("id,org_id,period_start,period_end,gross_cents,platform_fee_cents,net_cents,status,created_at")
                .in_("org_id", org_ids)
                .order("period_end", desc=True)
                .limit(100)
                .execute()
            )
            return supabase_client.extract_data(resp) or []
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="SETTLEMENTS_LIST_FAILED") from exc

    def get_settlement_detail(self, jwt: str, settlement_id: UUID, user_id: str) -> dict:
        """主辦方看單一結算明細（需為 org 成員）。"""
        client = supabase_client.authed_client(jwt)
        try:
            resp = (
                client.table("settlements")
                .select("id,org_id,period_start,period_end,gross_cents,platform_fee_cents,net_cents,status,created_at")
                .eq("id", str(settlement_id))
                .limit(1)
                .execute()
            )
            rows = supabase_client.extract_data(resp) or []
            if not rows:
                raise AppError(
                    code="SETTLEMENT_NOT_FOUND",
                    message="Settlement not found",
                    details={"settlement_id": str(settlement_id)},
                    http_status=404,
                )
            return rows[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="SETTLEMENT_FETCH_FAILED") from exc

    def get_org_balance_cents(self, sr, org_id: str) -> int:
        """計算 org 的可用餘額（ledger 加總）。"""
        resp = sr.table("ledger_entries").select("amount_cents").eq("org_id", org_id).execute()
        rows = supabase_client.extract_data(resp) or []
        return sum(r.get("amount_cents", 0) for r in rows)

    def create_payout_request(
        self, jwt: str, org_id: str, amount_cents: int, user_id: str
    ) -> dict:
        """主辦方申請提款。僅 owner/admin 可呼叫，餘額需足夠。"""
        events_service.require_org_admin(jwt, org_id, user_id)
        if amount_cents <= 0:
            raise AppError(
                code="VALIDATION_ERROR",
                message="amount_cents must be positive",
                details={"amount_cents": amount_cents},
                http_status=400,
            )

        sr = supabase_client.service_role_client()
        balance = self.get_org_balance_cents(sr, org_id)
        if amount_cents > balance:
            raise AppError(
                code="INSUFFICIENT_BALANCE",
                message="Available balance is insufficient for this payout",
                details={"amount_cents": amount_cents, "balance_cents": balance},
                http_status=400,
            )

        client = supabase_client.authed_client(jwt)
        try:
            row = {
                "org_id": org_id,
                "amount_cents": amount_cents,
                "status": "requested",
            }
            resp = client.table("payout_requests").insert(row).execute()
            data = supabase_client.extract_data(resp) or []
            if isinstance(data, dict):
                data = [data]
            if not data:
                raise AppError(
                    code="PAYOUT_CREATE_FAILED",
                    message="Failed to create payout request",
                    http_status=500,
                )
            return data[0]
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="PAYOUT_CREATE_FAILED") from exc

    def list_payout_requests_admin(self, status: str | None = None) -> list[dict]:
        """Admin 列表。"""
        sr = supabase_client.service_role_client()
        q = sr.table("payout_requests").select(
            "id,org_id,amount_cents,status,requested_at,processed_at,failure_reason"
        ).order("requested_at", desc=True).limit(200)
        if status:
            q = q.eq("status", status)
        resp = q.execute()
        return supabase_client.extract_data(resp) or []

    def approve_payout_request(self, payout_id: UUID, admin_user_id: str) -> dict:
        """Admin 核准提款：寫入 ledger payout 負額、更新 status=paid。"""
        sr = supabase_client.service_role_client()
        resp = sr.table("payout_requests").select("*").eq("id", str(payout_id)).limit(1).execute()
        rows = supabase_client.extract_data(resp) or []
        if not rows:
            raise AppError(
                code="PAYOUT_NOT_FOUND",
                message="Payout request not found",
                details={"payout_id": str(payout_id)},
                http_status=404,
            )
        pr = rows[0]
        if pr.get("status") != "requested":
            raise AppError(
                code="PAYOUT_ALREADY_PROCESSED",
                message=f"Payout already {pr.get('status')}",
                http_status=409,
            )

        org_id = str(pr.get("org_id", ""))
        amount_cents = int(pr.get("amount_cents", 0))
        now = datetime.now(UTC).isoformat()

        sr.table("ledger_entries").insert({
            "org_id": org_id,
            "type": "payout",
            "amount_cents": -amount_cents,
        }).execute()
        sr.table("payout_requests").update({
            "status": "paid",
            "processed_at": now,
        }).eq("id", str(payout_id)).execute()

        audit_service.log_payout_approve(payout_id, admin_user_id, org_id, amount_cents)

        pr["status"] = "paid"
        pr["processed_at"] = now
        return pr

    def reject_payout_request(
        self, payout_id: UUID, admin_user_id: str, failure_reason: str | None = None
    ) -> dict:
        """Admin 退件。"""
        sr = supabase_client.service_role_client()
        resp = sr.table("payout_requests").select("*").eq("id", str(payout_id)).limit(1).execute()
        rows = supabase_client.extract_data(resp) or []
        if not rows:
            raise AppError(
                code="PAYOUT_NOT_FOUND",
                message="Payout request not found",
                details={"payout_id": str(payout_id)},
                http_status=404,
            )
        pr = rows[0]
        if pr.get("status") != "requested":
            raise AppError(
                code="PAYOUT_ALREADY_PROCESSED",
                message=f"Payout already {pr.get('status')}",
                http_status=409,
            )

        now = datetime.now(UTC).isoformat()
        sr.table("payout_requests").update({
            "status": "failed",
            "processed_at": now,
            "failure_reason": failure_reason,
        }).eq("id", str(payout_id)).execute()

        audit_service.log_payout_reject(payout_id, admin_user_id, failure_reason)

        pr["status"] = "failed"
        pr["processed_at"] = now
        pr["failure_reason"] = failure_reason
        return pr


settlement_service = SettlementService()
