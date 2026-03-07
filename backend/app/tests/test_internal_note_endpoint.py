from __future__ import annotations

from app.domain.errors import AppError
from app.services.events_service import events_service
from app.services.supabase_client import supabase_client


def test_internal_note_upsert_requires_admin(client, monkeypatch) -> None:
    event_id = "0ef24fc6-ce65-4f5a-bd5a-fb8e6739cf73"
    jwt = "fake.jwt.token"
    user_id = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"

    no_token_response = client.patch(
        f"/api/v1/organizer/events/{event_id}/internal-note",
        json={"note": "private note"},
    )
    assert no_token_response.status_code == 401

    monkeypatch.setattr(supabase_client, "get_user", lambda _token: {"id": user_id})

    def _forbidden(*_args, **_kwargs):
        raise AppError(
            code="FORBIDDEN",
            message="Operation blocked by RLS policy",
            http_status=403,
        )

    monkeypatch.setattr(events_service, "upsert_event_internal_note", _forbidden)

    forbidden_response = client.patch(
        f"/api/v1/organizer/events/{event_id}/internal-note",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"note": "private note"},
    )
    assert forbidden_response.status_code == 403
    assert forbidden_response.get_json()["error"]["code"] == "FORBIDDEN"

    def _ok(*_args, **_kwargs):
        return {
            "event_id": event_id,
            "note": "private note",
            "updated_by": user_id,
            "updated_at": "2026-02-27T00:00:00+00:00",
        }

    monkeypatch.setattr(events_service, "upsert_event_internal_note", _ok)

    ok_response = client.patch(
        f"/api/v1/organizer/events/{event_id}/internal-note",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"note": "private note"},
    )
    assert ok_response.status_code == 200
    payload = ok_response.get_json()
    assert payload["event_id"] == event_id
    assert payload["note"] == "private note"

