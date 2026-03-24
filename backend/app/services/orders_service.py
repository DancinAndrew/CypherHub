"""MVP-2 orders service. develop.md 2.1.1, 2.1.2."""

from __future__ import annotations

from uuid import UUID

from app.domain.errors import AppError, map_supabase_error

from .supabase_client import supabase_client

ORDERS_SELECT = "id,user_id,status,total_cents,currency,hold_expires_at,created_at,updated_at"
ORDER_ITEMS_SELECT = "id,order_id,ticket_type_id,quantity,price_cents,created_at"
PAYMENTS_SELECT = "id,order_id,provider,external_id,amount_cents,currency,status,created_at"


class OrdersService:
    def list_orders_for_user(self, jwt: str) -> list[dict]:
        """取得目前使用者的訂單列表。透過 RLS 僅回傳 user_id = auth.uid() 的訂單。"""
        client = supabase_client.authed_client(jwt)
        try:
            response = (
                client.table("orders")
                .select(ORDERS_SELECT)
                .order("created_at", desc=True)
                .execute()
            )
            rows = supabase_client.extract_data(response) or []
            return rows
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="ORDERS_LIST_FAILED") from exc

    def get_order_detail(self, jwt: str, order_id: UUID) -> dict:
        """取得單一訂單詳情（含 items、payments）。RLS 僅允取自己的訂單。"""
        client = supabase_client.authed_client(jwt)
        try:
            order_resp = (
                client.table("orders")
                .select(ORDERS_SELECT)
                .eq("id", str(order_id))
                .limit(1)
                .execute()
            )
            orders = supabase_client.extract_data(order_resp) or []
            if not orders:
                raise AppError(
                    code="ORDER_NOT_FOUND",
                    message="Order not found",
                    http_status=404,
                )
            order = orders[0]

            items_resp = (
                client.table("order_items")
                .select(ORDER_ITEMS_SELECT)
                .eq("order_id", str(order_id))
                .execute()
            )
            items = supabase_client.extract_data(items_resp) or []

            payments_resp = (
                client.table("payments")
                .select(PAYMENTS_SELECT)
                .eq("order_id", str(order_id))
                .execute()
            )
            payments = supabase_client.extract_data(payments_resp) or []

            return {
                "order": order,
                "items": items,
                "payments": payments,
            }
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="ORDER_FETCH_FAILED") from exc

    def create_hold_order(self, jwt: str, items: list[dict], hold_minutes: int = 15) -> UUID:
        """選票種 → 建立 holding 訂單，原子扣 hold_count。逾時由 pg_cron 釋放。"""
        payload = [
            {
                "ticket_type_id": str(it["ticket_type_id"]),
                "quantity": it["quantity"],
            }
            for it in items
        ]
        try:
            result = supabase_client.call_rpc(
                "create_hold_order",
                {"p_items": payload, "p_hold_minutes": hold_minutes},
                jwt=jwt,
            )
            # PostgREST RPC RETURNS uuid → 可能是 str 或 [{"create_hold_order": "uuid"}]
            if isinstance(result, list) and result:
                row = result[0]
                if isinstance(row, dict):
                    val = row.get("create_hold_order") or row.get("id")
                    if val:
                        return UUID(val) if isinstance(val, str) else val
            if isinstance(result, str):
                return UUID(result)
            raise AppError(
                code="HOLD_ORDER_CREATE_FAILED",
                message="Unexpected RPC response",
                http_status=500,
            )
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="HOLD_ORDER_CREATE_FAILED") from exc

    def cancel_holding_order(self, jwt: str, order_id: UUID) -> None:
        """取消自己的 holding 訂單，釋放 hold_count。"""
        try:
            supabase_client.call_rpc(
                "cancel_holding_order",
                {"p_order_id": str(order_id)},
                jwt=jwt,
            )
        except AppError:
            raise
        except Exception as exc:
            raise map_supabase_error(exc, fallback_code="CANCEL_ORDER_FAILED") from exc

    def list_admin_orders(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        from_at: str | None = None,
        to_at: str | None = None,
        org_id: str | None = None,
        event_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Admin 全站訂單查詢。MVP-3.4。回傳 orders + items + payments。"""
        sr = supabase_client.service_role_client()
        order_ids_filter: list[str] | None = None
        if org_id or event_id:
            # 透過 order_items -> ticket_types -> events 取得 order_ids
            tt_query = sr.table("ticket_types").select("id").eq("event_id", event_id or "")
            if org_id:
                ev_resp = sr.table("events").select("id").eq("org_id", org_id).execute()
                ev_rows = supabase_client.extract_data(ev_resp) or []
                ev_ids = [str(r["id"]) for r in ev_rows]
                if not ev_ids:
                    return []
                tt_query = sr.table("ticket_types").select("id").in_("event_id", ev_ids)
            else:
                tt_query = sr.table("ticket_types").select("id").eq("event_id", event_id)
            tt_resp = tt_query.execute()
            tt_rows = supabase_client.extract_data(tt_resp) or []
            tt_ids = [str(r["id"]) for r in tt_rows]
            if not tt_ids:
                return []
            oi_resp = (
                sr.table("order_items").select("order_id").in_("ticket_type_id", tt_ids).execute()
            )
            oi_rows = supabase_client.extract_data(oi_resp) or []
            order_ids_filter = list({str(r["order_id"]) for r in oi_rows})
            if not order_ids_filter:
                return []
        query = (
            sr.table("orders")
            .select(ORDERS_SELECT)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if status:
            query = query.eq("status", status)
        if from_at:
            query = query.gte("created_at", from_at)
        if to_at:
            query = query.lt("created_at", to_at)
        if order_ids_filter:
            query = query.in_("id", order_ids_filter)
        if q:
            # q: 搜尋 order id（前綴或完整）
            try:
                _ = UUID(q)
                query = query.eq("id", q)
            except (ValueError, TypeError):
                pass
        resp = query.execute()
        orders = supabase_client.extract_data(resp) or []
        if not orders:
            return []
        order_ids = [str(o["id"]) for o in orders]
        items_resp = (
            sr.table("order_items").select(ORDER_ITEMS_SELECT).in_("order_id", order_ids).execute()
        )
        items = supabase_client.extract_data(items_resp) or []
        pay_resp = sr.table("payments").select(PAYMENTS_SELECT).in_("order_id", order_ids).execute()
        payments = supabase_client.extract_data(pay_resp) or []
        items_by_order: dict[str, list] = {}
        for it in items:
            oid = str(it["order_id"])
            items_by_order.setdefault(oid, []).append(it)
        pays_by_order: dict[str, list] = {}
        for p in payments:
            oid = str(p["order_id"])
            pays_by_order.setdefault(oid, []).append(p)
        result = []
        for o in orders:
            oid = str(o["id"])
            result.append(
                {
                    "order": o,
                    "items": items_by_order.get(oid, []),
                    "payments": pays_by_order.get(oid, []),
                }
            )
        return result


orders_service = OrdersService()
