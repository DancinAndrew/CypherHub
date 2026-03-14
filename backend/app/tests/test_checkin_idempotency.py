"""Checkin commit: second commit on same ticket returns 200 with already_checked_in=true."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.supabase_client import supabase_client


@pytest.fixture()
def checkin_mocks(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    user_id = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"
    monkeypatch.setattr(supabase_client, "get_user", lambda token: {"id": user_id})

    call_rpc = MagicMock()
    monkeypatch.setattr(supabase_client, "call_rpc", call_rpc)
    return call_rpc


def test_commit_checkin_idempotent_second_call_returns_already_checked_in(
    client: object,
    checkin_mocks: MagicMock,
) -> None:
    """First commit: ok=true, already_checked_in=false; second: ok=true, already_checked_in=true."""
    event_id = "ff895f3f-dd7b-496c-a6ff-6c9d95de43e6"
    ticket_id = "f5de9492-6fcb-49f8-bb27-a9ff728acbbf"
    qr_secret = "abcdef123456"
    jwt = "fake.jwt.token"

    payload = {"ticket_id": ticket_id, "qr_secret": qr_secret}
    url = f"/api/v1/organizer/events/{event_id}/checkin/commit"

    # First commit: success, not yet checked in
    checkin_mocks.return_value = {"ok": True, "already_checked_in": False}

    r1 = client.post(
        url,
        headers={"Authorization": f"Bearer {jwt}"},
        json=payload,
    )
    assert r1.status_code == 200
    data1 = r1.get_json()
    assert data1.get("ok") is True
    assert data1.get("already_checked_in") is False

    # Second commit: idempotent, already checked in
    checkin_mocks.return_value = {"ok": True, "already_checked_in": True}

    r2 = client.post(
        url,
        headers={"Authorization": f"Bearer {jwt}"},
        json=payload,
    )
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert data2.get("ok") is True
    assert data2.get("already_checked_in") is True

    assert checkin_mocks.call_count == 2
    for call in checkin_mocks.call_args_list:
        assert call[0][0] == "commit_checkin"
        assert call[1]["jwt"] == jwt
