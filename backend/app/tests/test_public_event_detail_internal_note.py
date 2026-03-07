from __future__ import annotations

from app.services.events_service import events_service


def test_public_event_detail_does_not_include_internal_note(client, monkeypatch) -> None:
    event_id = "158a6f2a-89f2-4a9f-a57f-b6955510afe6"

    def _fake_get_public_event_detail(_event_uuid):
        return {
            "event": {
                "id": event_id,
                "org_id": "6c90c132-6849-4e0a-bf49-f10824712df8",
                "title": "Public Event",
                "description": "Public description",
                "short_desc": "Short",
                "start_at": "2026-03-01T10:00:00+00:00",
                "end_at": "2026-03-01T12:00:00+00:00",
                "status": "published",
                "dance_styles": ["hiphop"],
                "event_types": ["battle"],
                "socials": {},
                "schedule": [],
                "internal_note": "should never be exposed",
            },
            "event_media": [],
            "ticket_types": [],
        }

    monkeypatch.setattr(events_service, "get_public_event_detail", _fake_get_public_event_detail)

    response = client.get(f"/api/v1/events/{event_id}")

    assert response.status_code == 200
    payload = response.get_json()
    assert "internal_note" not in payload["event"]

