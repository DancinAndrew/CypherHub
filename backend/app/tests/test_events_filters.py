from __future__ import annotations

from app.services.events_service import _apply_keyword_search, events_service


def test_keyword_search_builds_or_on_title_and_locations() -> None:
    """關鍵字搜尋應對 title / short_desc / location_name / location_address 做 OR ilike。"""
    captured: list[str] = []

    class _Q:
        def or_(self, s: str):
            captured.append(s)
            return self

    q = _Q()
    _apply_keyword_search(q, " 信義 ")
    assert captured
    assert "title.ilike." in captured[0]
    assert "short_desc.ilike." in captured[0]
    assert "location_name.ilike." in captured[0]
    assert "location_address.ilike." in captured[0]
    assert "信義" in captured[0]


def test_keyword_search_empty_q_returns_query_unchained() -> None:
    class _Q:
        def or_(self, s: str) -> None:
            raise AssertionError("should not call or_")

    _apply_keyword_search(_Q(), "   ")


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


def test_list_events_sort_hot(client, monkeypatch) -> None:
    """MVP-3.5: sort=hot 傳遞至 list_public_events。"""
    captured: dict = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(events_service, "list_public_events", _fake)

    response = client.get("/api/v1/events?sort=hot")

    assert response.status_code == 200
    assert captured.get("sort") == "hot"
