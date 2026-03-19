"""MVP-2.3 補償服務：paid 但未 issued 的訂單出票。develop.md 2.2.1、2.3."""

from __future__ import annotations

from .supabase_client import supabase_client


def run_compensate_paid_orders() -> int:
    """
    執行 compensate_paid_orders RPC，處理 paid 但未出票的訂單。
    冪等：已 issued 不再建立。回傳處理的訂單數。
    """
    svc = supabase_client.service_role_client()
    resp = svc.rpc("compensate_paid_orders", {}).execute()
    result = supabase_client.extract_data(resp)
    if result is None:
        return 0
    if isinstance(result, list) and result:
        return int(result[0]) if isinstance(result[0], int | float) else 0
    return int(result) if isinstance(result, int | float) else 0
