from __future__ import annotations

from unittest.mock import MagicMock

from app.services.forms_service import forms_service
from app.services.supabase_client import supabase_client


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return {"data": self.rows}


class _FakeClient:
    def __init__(self, ticket_type_rows):
        self.ticket_type_rows = ticket_type_rows

    def table(self, table_name: str):
        assert table_name == "ticket_types"
        return _FakeQuery(self.ticket_type_rows)


def test_register_route_calls_register_free_rpc(client, monkeypatch) -> None:
    event_id = "ff895f3f-dd7b-496c-a6ff-6c9d95de43e6"
    ticket_type_id = "34f9bc6e-bfdf-4668-a2a4-4e6ff2f3f0ce"
    user_id = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"
    jwt = "fake.jwt.token"

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

    monkeypatch.setattr(forms_service, "get_public_form", lambda *_args, **_kwargs: None)

    rpc_mock = MagicMock(
        return_value=[
            {
                "id": "f5de9492-6fcb-49f8-bb27-a9ff728acbbf",
                "event_id": event_id,
                "ticket_type_id": ticket_type_id,
                "user_id": user_id,
                "status": "issued",
                "qr_secret": "abcdef123456",
                "issued_at": "2026-02-26T00:00:00+00:00",
                "checked_in_at": None,
            }
        ]
    )
    monkeypatch.setattr(supabase_client, "call_rpc", rpc_mock)

    response = client.post(
        f"/api/v1/events/{event_id}/register",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"ticket_type_id": ticket_type_id, "quantity": 1},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["tickets"][0]["ticket_id"] == "f5de9492-6fcb-49f8-bb27-a9ff728acbbf"

    rpc_mock.assert_called_once_with(
        "register_free_v2",
        {"p_ticket_type_id": ticket_type_id, "p_quantity": 1, "p_answers": {}},
        jwt=jwt,
    )
