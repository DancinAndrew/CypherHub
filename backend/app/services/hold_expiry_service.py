"""MVP-2 Hold 逾時釋放：release_expired_holds RPC。develop.md 2.1.2."""

from __future__ import annotations

from .supabase_client import supabase_client


def run_release_expired_holds() -> int:
    """
    執行 release_expired_holds RPC，逾時 holding → cancelled，釋放 hold_count。
    回傳處理的訂單數。
    """
    svc = supabase_client.service_role_client()
    resp = svc.rpc("release_expired_holds", {}).execute()
    result = supabase_client.extract_data(resp)
    if result is None:
        return 0
    if isinstance(result, list) and result:
        return int(result[0]) if isinstance(result[0], int | float) else 0
    return int(result) if isinstance(result, int | float) else 0
