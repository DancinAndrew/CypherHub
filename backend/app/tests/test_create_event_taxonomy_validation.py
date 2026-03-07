from __future__ import annotations

from app.services.supabase_client import supabase_client


def test_create_event_rejects_invalid_dance_style(client, monkeypatch) -> None:
    monkeypatch.setattr(
        supabase_client,
        "get_user",
        lambda _token: {"id": "11111111-1111-1111-1111-111111111111"},
    )

    response = client.post(
        "/api/v1/organizer/events",
        headers={"Authorization": "Bearer fake.jwt.token"},
        json={
            "org_id": "22222222-2222-4222-9222-222222222222",
            "title": "Taxonomy test event",
            "start_at": "2026-03-01T10:00:00+00:00",
            "end_at": "2026-03-01T12:00:00+00:00",
            "status": "published",
            "dance_styles": ["hip_hop"],
            "event_types": ["battle"],
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert any("dance_styles" in str(item.get("loc", "")) for item in payload["error"]["details"])
