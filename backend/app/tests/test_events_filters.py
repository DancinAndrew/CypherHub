from __future__ import annotations

from app.services.events_service import events_service


def test_list_events_passes_styles_and_types_filters(client, monkeypatch) -> None:
    captured: dict = {}

    def _fake_list_public_events(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(events_service, "list_public_events", _fake_list_public_events)

    response = client.get("/api/v1/events?styles=HipHop,popping,hiphop&types=cypher")

    assert response.status_code == 200
    assert captured["styles"] == ["hiphop", "popping"]
    assert captured["types"] == ["cypher"]
