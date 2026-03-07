from __future__ import annotations

from uuid import UUID

from app.services.events_service import events_service
from app.services.supabase_client import supabase_client


class _TicketsQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        return {"data": self.rows}


class _FakeClient:
    def __init__(self, tickets_rows, response_rows):
        self.tickets_rows = tickets_rows
        self.response_rows = response_rows

    def table(self, table_name: str):
        if table_name == "tickets":
            return _TicketsQuery(self.tickets_rows)
        if table_name == "ticket_form_responses":
            return _TicketsQuery(self.response_rows)
        raise AssertionError(f"Unexpected table {table_name}")


def test_attendees_merges_answers_by_ticket_id(monkeypatch) -> None:
    event_id = UUID("b9e61eb1-1cda-49db-a4d2-5665ecf7d913")

    monkeypatch.setattr(
        supabase_client,
        "authed_client",
        lambda _jwt: _FakeClient(
            tickets_rows=[
                {
                    "id": "a1ab3fc5-3192-473d-84bc-b7dadd6b1bc9",
                    "user_id": "5f67f4da-44d7-46a0-bd27-b94692d7d3c2",
                    "status": "issued",
                    "checked_in_at": None,
                    "ticket_type_id": "5df2460b-785d-4b38-a77c-c1c7ea9120c2",
                }
            ],
            response_rows=[
                {
                    "ticket_id": "a1ab3fc5-3192-473d-84bc-b7dadd6b1bc9",
                    "answers": {"full_name": "Andrew", "agree_media": True},
                }
            ],
        ),
    )

    rows = events_service.list_attendees("fake.jwt.token", event_id)

    assert rows[0]["answers"] == {"full_name": "Andrew", "agree_media": True}
