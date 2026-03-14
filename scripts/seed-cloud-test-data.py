#!/usr/bin/env python3
"""
在 Supabase Cloud 建立測試用戶與資料，保持專案活躍。
需在 backend/.env 填入 SUPABASE_URL 與 SUPABASE_SERVICE_ROLE_KEY。
執行：python scripts/seed-cloud-test-data.py
"""
from __future__ import annotations

import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

# 載入 backend/.env
def _load_env(path: Path) -> None:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                val = v.strip().strip('"').strip("'")
                if val:
                    os.environ[k.strip()] = val


_backend_root = Path(__file__).resolve().parent.parent / "backend"
_load_env(_backend_root / ".env")

# 確保能找到 backend app
sys.path.insert(0, str(_backend_root))

try:
    from supabase import create_client
except ImportError:
    print("請先安裝 supabase：cd backend && pip install -r requirements.txt")
    sys.exit(1)

URL = os.environ.get("SUPABASE_URL", "").strip()
SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

TEST_OWNER_EMAIL = "organizer-cloud-test@cypherhub.local"
TEST_OWNER_PASSWORD = "TestOrganizer123!"
TEST_ATTENDEE_EMAIL = "attendee-cloud-test@cypherhub.local"
TEST_ATTENDEE_PASSWORD = "TestAttendee123!"


def main() -> None:
    if not URL or not SERVICE_ROLE:
        print("錯誤：請在 backend/.env 填入 SUPABASE_URL 與 SUPABASE_SERVICE_ROLE_KEY")
        print("  取得位置：Supabase Dashboard → Project Settings → API")
        sys.exit(1)

    if "YOUR_PROJECT_REF" in URL or "your-project" in URL.lower():
        print("錯誤：請填入真實的 Supabase Cloud URL，不要使用範本")
        sys.exit(1)

    client = create_client(URL, SERVICE_ROLE)

    print("==> 建立測試用戶")
    # 使用 admin API 建立用戶（service_role 可略過 email 驗證）
    try:
        owner_resp = client.auth.admin.create_user(
            {
                "email": TEST_OWNER_EMAIL,
                "password": TEST_OWNER_PASSWORD,
                "email_confirm": True,
            }
        )
        owner_id = _get_user_id(owner_resp)
        print(f"  ✓ organizer: {TEST_OWNER_EMAIL} (id={owner_id})")
    except Exception as e:
        if "already been registered" in str(e).lower() or "already exists" in str(e).lower():
            # 若已存在，嘗試取得 user id
            users = client.auth.admin.list_users()
            owner_id = None
            for u in getattr(users, "users", []) or []:
                uid = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
                email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
                if email == TEST_OWNER_EMAIL:
                    owner_id = uid
                    break
            if not owner_id:
                print(f"  用戶 {TEST_OWNER_EMAIL} 已存在，無法取得 id，請手動刪除後重試")
                sys.exit(1)
            print(f"  (organizer 已存在) id={owner_id}")
        else:
            raise

    try:
        attendee_resp = client.auth.admin.create_user(
            {
                "email": TEST_ATTENDEE_EMAIL,
                "password": TEST_ATTENDEE_PASSWORD,
                "email_confirm": True,
            }
        )
        attendee_id = _get_user_id(attendee_resp)
        print(f"  ✓ attendee: {TEST_ATTENDEE_EMAIL} (id={attendee_id})")
    except Exception as e:
        if "already been registered" in str(e).lower() or "already exists" in str(e).lower():
            users = client.auth.admin.list_users()
            attendee_id = None
            for u in getattr(users, "users", []) or []:
                uid = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
                email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
                if email == TEST_ATTENDEE_EMAIL:
                    attendee_id = uid
                    break
            if not attendee_id:
                print(f"  用戶 {TEST_ATTENDEE_EMAIL} 已存在")
                sys.exit(1)
            print(f"  (attendee 已存在) id={attendee_id}")
        else:
            raise

    print("\n==> 建立 profiles")
    for uid, name in [(owner_id, "測試主辦"), (attendee_id, "測試觀眾")]:
        client.table("profiles").upsert(
            {"id": uid, "display_name": name},
            on_conflict="id",
        ).execute()
    print("  ✓ profiles 已建立")

    print("\n==> 建立 organization、event、ticket_type")
    org_row = (
        client.table("organizations")
        .insert(
            {
                "name": "Cloud 測試主辦",
                "owner_user_id": owner_id,
            }
        )
        .execute()
    )
    org_id = org_row.data[0]["id"]
    print(f"  ✓ org_id={org_id}")

    start = datetime.now(timezone.utc)
    from datetime import timedelta

    end = start + timedelta(hours=2)
    event_row = (
        client.table("events")
        .insert(
            {
                "org_id": org_id,
                "title": "Cloud 測試活動",
                "start_at": start.isoformat(),
                "end_at": end.isoformat(),
                "status": "published",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "created_by": owner_id,
            }
        )
        .execute()
    )
    event_id = event_row.data[0]["id"]
    print(f"  ✓ event_id={event_id}")

    tt_row = (
        client.table("ticket_types")
        .insert(
            {
                "event_id": event_id,
                "name": "免費票",
                "capacity": 10,
                "per_user_limit": 2,
                "price_cents": 0,
                "is_active": True,
            }
        )
        .execute()
    )
    ticket_type_id = tt_row.data[0]["id"]
    print(f"  ✓ ticket_type_id={ticket_type_id}")

    print("\n==> 建立測試票券（給 attendee）")
    qr_secret = secrets.token_hex(16)
    ticket_row = (
        client.table("tickets")
        .insert(
            {
                "event_id": event_id,
                "ticket_type_id": ticket_type_id,
                "user_id": attendee_id,
                "qr_secret": qr_secret,
                "status": "issued",
            }
        )
        .execute()
    )
    ticket_id = ticket_row.data[0]["id"]

    # 更新 sold_count
    client.table("ticket_types").update({"sold_count": 1}).eq("id", ticket_type_id).execute()
    print(f"  ✓ ticket_id={ticket_id}")

    print("\n" + "=" * 50)
    print("Cloud 測試資料建立完成")
    print("=" * 50)
    print("\n測試帳號：")
    print(f"  主辦方：{TEST_OWNER_EMAIL} / {TEST_OWNER_PASSWORD}")
    print(f"  觀眾：  {TEST_ATTENDEE_EMAIL} / {TEST_ATTENDEE_PASSWORD}")
    print("\n可登入前端，用主辦方帳號管理活動、用觀眾帳號查看票券。")
    print("專案已有資料與 API 存取，較不易被 pause。\n")


def _get_user_id(resp) -> str:
    user = getattr(resp, "user", None)
    if user is None and isinstance(resp, dict):
        user = resp.get("user")
    if user is None:
        raise RuntimeError("create_user 未回傳 user")
    uid = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)
    if not uid:
        raise RuntimeError("無法取得 user id")
    return str(uid)


if __name__ == "__main__":
    main()
