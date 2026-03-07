from __future__ import annotations

from app.services.forms_service import forms_service


def test_forms_public_get_returns_active_schema(client, monkeypatch) -> None:
    event_id = "4ad9a9da-2753-41df-8d14-f29a7f4ec5c2"
    ticket_type_id = "25a1437b-4eb0-4af2-9ed7-6ca715529fe9"

    monkeypatch.setattr(
        forms_service,
        "get_public_form",
        lambda *_args, **_kwargs: {
            "id": "7677752d-d86e-429e-9fb1-669678de2d4b",
            "event_id": event_id,
            "ticket_type_id": ticket_type_id,
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
            },
            "version": 1,
            "is_active": True,
        },
    )

    response = client.get(
        f"/api/v1/events/{event_id}/forms?ticket_type_id={ticket_type_id}",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["form"]["event_id"] == event_id
    assert payload["form"]["ticket_type_id"] == ticket_type_id
    assert payload["form"]["schema"]["fields"][0]["key"] == "full_name"
