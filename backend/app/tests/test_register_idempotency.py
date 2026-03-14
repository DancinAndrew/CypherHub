"""Register: per-user limit (second call same user/ticket_type returns 409)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.forms_service import forms_service
from app.services.supabase_client import supabase_client


class _FakeQuery:
    def __init__(self, rows: list) -> None:
        self.rows = rows

    def select(self, *_args: object, **_kwargs: object) -> _FakeQuery:
        return self

    def eq(self, *_args: object, **_kwargs: object) -> _FakeQuery:
        return self

    def limit(self, *_args: object, **_kwargs: object) -> _FakeQuery:
        return self

    def execute(self) -> dict:
        return {"data": self.rows}


class _FakeClient:
    def __init__(self, ticket_type_rows: list) -> None:
        self.ticket_type_rows = ticket_type_rows

    def table(self, table_name: str) -> _FakeQuery:
        assert table_name == "ticket_types"
        return _FakeQuery(self.ticket_type_rows)


@pytest.fixture()
def register_mocks(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    event_id = "ff895f3f-dd7b-496c-a6ff-6c9d95de43e6"
    ticket_type_id = "34f9bc6e-bfdf-4668-a2a4-4e6ff2f3f0ce"
    user_id = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"

    monkeypatch.setattr(supabase_client, "get_user", lambda token: {"id": user_id})
    monkeypatch.setattr(
        supabase_client,
        "authed_client",
        lambda token: _FakeClient(
            [
                {
                    "id": ticket_type_id,
                    "event_id": event_id,
                    "price_cents": 0,
                    "is_active": True,
                }
            ]
        ),
    )
    monkeypatch.setattr(forms_service, "get_public_form", lambda *_a, **_k: None)
    monkeypatch.setattr(forms_service, "validate_answers", lambda *_a, **_k: {})

    call_rpc_mock = MagicMock()
    monkeypatch.setattr(supabase_client, "call_rpc", call_rpc_mock)
    return call_rpc_mock


def test_register_second_call_per_user_limit_exceeded_returns_409(
    client: object,
    register_mocks: MagicMock,
) -> None:
    """Second register for same user/ticket_type returns 409 PER_USER_LIMIT_EXCEEDED."""
    event_id = "ff895f3f-dd7b-496c-a6ff-6c9d95de43e6"
    ticket_type_id = "34f9bc6e-bfdf-4668-a2a4-4e6ff2f3f0ce"
    user_id = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"
    jwt = "fake.jwt.token"

    ticket_row = {
        "id": "f5de9492-6fcb-49f8-bb27-a9ff728acbbf",
        "event_id": event_id,
        "ticket_type_id": ticket_type_id,
        "user_id": user_id,
        "status": "issued",
        "qr_secret": "abcdef123456",
        "issued_at": "2026-02-26T00:00:00+00:00",
        "checked_in_at": None,
    }

    # First call: success
    register_mocks.return_value = [ticket_row]

    r1 = client.post(
        f"/api/v1/events/{event_id}/register",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"ticket_type_id": ticket_type_id, "quantity": 1},
    )
    assert r1.status_code == 200
    assert register_mocks.call_count == 1

    # Second call: RPC raises PER_USER_LIMIT_EXCEEDED (simulated by message string)
    register_mocks.side_effect = RuntimeError("PER_USER_LIMIT_EXCEEDED")

    r2 = client.post(
        f"/api/v1/events/{event_id}/register",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"ticket_type_id": ticket_type_id, "quantity": 1},
    )
    assert r2.status_code == 409
    data = r2.get_json()
    assert data.get("error", {}).get("code") == "PER_USER_LIMIT_EXCEEDED"
