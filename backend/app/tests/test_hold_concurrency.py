"""防超賣併發測試。MVP-2.4：capacity=1 時 2 人同時 hold，1 成功、1 SOLD_OUT。"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from app.services.supabase_client import supabase_client


# 整合測試：可用 TEST_USER_1_* / TEST_USER_2_* 或 seed 帳密
def _user1() -> tuple[str, str]:
    e = os.getenv("TEST_USER_1_EMAIL") or os.getenv("ORGANIZER_CLOUD_TEST_EMAIL", "organizer-cloud-test@cypherhub.local")
    p = os.getenv("TEST_USER_1_PASSWORD") or os.getenv("ORGANIZER_CLOUD_TEST_PASSWORD", "TestOrganizer123!")
    return (e, p)


def _user2() -> tuple[str, str]:
    e = os.getenv("TEST_USER_2_EMAIL") or os.getenv("ATTENDEE_CLOUD_TEST_EMAIL", "attendee-cloud-test@cypherhub.local")
    p = os.getenv("TEST_USER_2_PASSWORD") or os.getenv("ATTENDEE_CLOUD_TEST_PASSWORD", "TestAttendee123!")
    return (e, p)


def _env_ready() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def _login(client, email: str, password: str) -> str | None:
    """Login，成功回傳 token；失敗（網路/帳密）回傳 None。"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        content_type="application/json",
    )
    if resp.status_code != 200:
        return None
    data = resp.get_json()
    return (data or {}).get("access_token")


@pytest.mark.skipif(
    not _env_ready(),
    reason="SUPABASE_* + SERVICE_ROLE_KEY required for concurrency integration test",
)
def test_concurrent_hold_last_ticket_one_succeeds_one_sold_out(client, app) -> None:
    """
    capacity=1 時，2 人同時 create_hold_order → 1 成功、1 SOLD_OUT。
    develop.md MVP-2.4 防超賣。需真實 Supabase、可達網路、2 組測試帳密。
    若登入或 Supabase API 失敗（如沙盒、專案暫停）→ skip。
    """
    email1, pass1 = _user1()
    email2, pass2 = _user2()

    try:
        jwt1 = _login(client, email1, pass1)
        jwt2 = _login(client, email2, pass2)
        if not jwt1 or not jwt2:
            pytest.skip("Login failed (network/Supabase unreachable or credentials invalid)")

        # 2) 建立 org / event / ticket_type (capacity=1)
        from supabase import create_client

        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        admin = create_client(url, key)
        user_resp = admin.auth.admin.list_users()
    except Exception:
        pytest.skip("Supabase unreachable (network/proxy/project paused)")
    users = getattr(user_resp, "users", []) or []
    uid1 = next((u.id for u in users if getattr(u, "email", None) == email1), None)
    if not uid1:
        pytest.skip("TEST_USER_1 not found in Supabase Auth")

    org_row = admin.table("organizations").insert({"name": "Concurrency Test Org", "owner_user_id": uid1}).execute()
    org_id = org_row.data[0]["id"]

    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    event_row = (
        admin.table("events")
        .insert(
            {
                "org_id": org_id,
                "title": "Concurrency Test Event",
                "start_at": (now + timedelta(hours=1)).isoformat(),
                "end_at": (now + timedelta(hours=2)).isoformat(),
                "status": "published",
                "published_at": now.isoformat(),
                "created_by": uid1,
            }
        )
        .execute()
    )
    event_id = event_row.data[0]["id"]

    tt_row = (
        admin.table("ticket_types")
        .insert(
            {
                "event_id": event_id,
                "name": "Last Ticket",
                "capacity": 1,
                "per_user_limit": 1,
                "price_cents": 0,
                "is_active": True,
                "sold_count": 0,
                "hold_count": 0,
            }
        )
        .execute()
    )
    ticket_type_id = tt_row.data[0]["id"]

    # 3) 併發 hold
    results = {"success": [], "errors": []}

    def run_hold(jwt: str):
        with app.app_context():
            try:
                result = supabase_client.call_rpc(
                    "create_hold_order",
                    {"p_items": [{"ticket_type_id": ticket_type_id, "quantity": 1}], "p_hold_minutes": 15},
                    jwt=jwt,
                )
                return ("ok", result)
            except Exception as e:
                return ("err", e)

    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(run_hold, jwt1)
        f2 = ex.submit(run_hold, jwt2)
        for f in as_completed([f1, f2]):
            status, val = f.result()
            if status == "ok":
                results["success"].append(val)
            else:
                results["errors"].append(val)

    assert len(results["success"]) == 1, f"Expected exactly 1 success, got {results}"
    assert len(results["errors"]) == 1, f"Expected exactly 1 error, got {results}"

    err = results["errors"][0]
    err_str = str(err).upper()
    assert "SOLD_OUT" in err_str or "SOLD OUT" in err_str or "22023" in err_str or "CAPACITY" in err_str, (
        f"Expected SOLD_OUT, got: {err}"
    )
