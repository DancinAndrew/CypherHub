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


def test_register_validates_required_fields_before_rpc(client, monkeypatch) -> None:
    event_id = "1e55d935-3c86-4d5d-904a-1dfb6474fc3d"
    ticket_type_id = "3d316e5d-a4d4-4a07-b36c-f17ad08d5a4f"
    user_id = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"
    jwt = "fake.jwt.token"

    monkeypatch.setattr(supabase_client, "get_user", lambda _token: {"id": user_id})
    monkeypatch.setattr(
        supabase_client,
        "authed_client",
        lambda _token: _FakeClient(
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
    monkeypatch.setattr(
        forms_service,
        "get_public_form",
        lambda *_args, **_kwargs: {
            "schema": {
                "version": 1,
                "fields": [
                    {
                        "key": "full_name",
                        "label": "Full Name",
                        "type": "text",
                        "required": True,
                        "options": [],
                    }
                ],
            }
        },
    )

    rpc_mock = MagicMock(return_value=[])
    monkeypatch.setattr(supabase_client, "call_rpc", rpc_mock)

    response = client.post(
        f"/api/v1/events/{event_id}/register",
        headers={"Authorization": f"Bearer {jwt}"},
        json={
            "ticket_type_id": ticket_type_id,
            "quantity": 1,
            "answers": {},
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["details"]["field"] == "full_name"
    rpc_mock.assert_not_called()
