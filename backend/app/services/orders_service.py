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

    def create_hold_order(
        self, jwt: str, items: list[dict], hold_minutes: int = 15
    ) -> UUID:
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


orders_service = OrdersService()
