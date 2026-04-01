from __future__ import annotations

from app.services.events_service import events_service
from app.services.progress_service import progress_service
from app.services.supabase_client import supabase_client

FAKE_EVENT_ID = "0ef24fc6-ce65-4f5a-bd5a-fb8e6739cf73"
FAKE_USER_ID = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"
FAKE_JWT = "fake.jwt.token"
FAKE_STAGE_ID_1 = "aaaaaaaa-0001-0001-0001-aaaaaaaaaaaa"
FAKE_STAGE_ID_2 = "aaaaaaaa-0002-0002-0002-aaaaaaaaaaaa"


# ---- Public progress endpoint ----


def test_public_progress_returns_data(client, monkeypatch) -> None:
    """GET /api/v1/events/<id>/progress returns progress + stages."""

    def _mock_public_progress(_event_id):
        return {
            "progress": {
                "id": "pid",
                "event_id": str(_event_id),
                "current_stage_id": FAKE_STAGE_ID_1,
                "current_stage_title": "海選",
                "status": "in_progress",
                "note": "第二輪",
                "updated_at": "2026-03-25T10:00:00+00:00",
                "total_stages": 5,
                "current_stage_order": 1,
            },
            "stages": [
                {
                    "id": FAKE_STAGE_ID_1,
                    "event_id": str(_event_id),
                    "title": "報到",
                    "sort_order": 0,
                },
                {
                    "id": FAKE_STAGE_ID_2,
                    "event_id": str(_event_id),
                    "title": "海選",
                    "sort_order": 1,
                },
            ],
        }

    monkeypatch.setattr(progress_service, "get_public_progress", _mock_public_progress)

    resp = client.get(f"/api/v1/events/{FAKE_EVENT_ID}/progress")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["progress"]["status"] == "in_progress"
    assert len(data["stages"]) == 2


def test_public_progress_no_data(client, monkeypatch) -> None:
    """No progress set → returns null progress."""

    def _mock_public_progress(_event_id):
        return {"progress": None, "stages": []}

    monkeypatch.setattr(progress_service, "get_public_progress", _mock_public_progress)

    resp = client.get(f"/api/v1/events/{FAKE_EVENT_ID}/progress")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["progress"] is None
    assert data["stages"] == []


# ---- Organizer stages endpoint ----


def test_replace_stages_requires_auth(client) -> None:
    """PUT /api/v1/organizer/events/<id>/stages requires JWT."""
    resp = client.put(
        f"/api/v1/organizer/events/{FAKE_EVENT_ID}/stages",
        json={"stages": [{"title": "報到", "sort_order": 0}]},
    )
    assert resp.status_code == 401


def test_replace_stages_validation_empty(client, monkeypatch) -> None:
    """PUT stages with empty array → 400."""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": FAKE_USER_ID})

    resp = client.put(
        f"/api/v1/organizer/events/{FAKE_EVENT_ID}/stages",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
        json={"stages": []},
    )
    assert resp.status_code == 400


def test_replace_stages_success(client, monkeypatch) -> None:
    """PUT stages with valid data → 200."""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": FAKE_USER_ID})
    monkeypatch.setattr(events_service, "require_event_admin", lambda *_, **__: None)

    created_stages = [
        {"id": FAKE_STAGE_ID_1, "event_id": FAKE_EVENT_ID, "title": "報到", "sort_order": 0},
        {"id": FAKE_STAGE_ID_2, "event_id": FAKE_EVENT_ID, "title": "海選", "sort_order": 1},
    ]
    monkeypatch.setattr(progress_service, "replace_stages", lambda *_, **__: created_stages)

    resp = client.put(
        f"/api/v1/organizer/events/{FAKE_EVENT_ID}/stages",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
        json={
            "stages": [
                {"title": "報到", "sort_order": 0},
                {"title": "海選", "sort_order": 1},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["stages"]) == 2
    assert data["stages"][0]["title"] == "報到"


# ---- Organizer progress update ----


def test_update_progress_requires_auth(client) -> None:
    """PATCH progress requires JWT."""
    resp = client.patch(
        f"/api/v1/organizer/events/{FAKE_EVENT_ID}/progress",
        json={"status": "in_progress"},
    )
    assert resp.status_code == 401


def test_update_progress_success(client, monkeypatch) -> None:
    """PATCH progress → 200."""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": FAKE_USER_ID})

    updated = {
        "id": "pid",
        "event_id": FAKE_EVENT_ID,
        "current_stage_id": FAKE_STAGE_ID_1,
        "current_stage_title": "海選",
        "status": "in_progress",
        "note": None,
        "updated_at": "2026-03-25T10:00:00+00:00",
        "total_stages": 5,
        "current_stage_order": 1,
    }
    monkeypatch.setattr(progress_service, "update_progress", lambda *_, **__: updated)

    resp = client.patch(
        f"/api/v1/organizer/events/{FAKE_EVENT_ID}/progress",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
        json={"status": "in_progress"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["progress"]["status"] == "in_progress"


def test_update_progress_invalid_status(client, monkeypatch) -> None:
    """PATCH with invalid status → 400."""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": FAKE_USER_ID})

    resp = client.patch(
        f"/api/v1/organizer/events/{FAKE_EVENT_ID}/progress",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
        json={"status": "invalid_status"},
    )
    assert resp.status_code == 400


def test_update_progress_note(client, monkeypatch) -> None:
    """PATCH with note → 200."""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": FAKE_USER_ID})

    updated = {
        "id": "pid",
        "event_id": FAKE_EVENT_ID,
        "current_stage_id": None,
        "current_stage_title": None,
        "status": "in_progress",
        "note": "休息 15 分鐘",
        "updated_at": "2026-03-25T10:00:00+00:00",
        "total_stages": 3,
        "current_stage_order": None,
    }
    monkeypatch.setattr(progress_service, "update_progress", lambda *_, **__: updated)

    resp = client.patch(
        f"/api/v1/organizer/events/{FAKE_EVENT_ID}/progress",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
        json={"note": "休息 15 分鐘"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["progress"]["note"] == "休息 15 分鐘"


# ---- Organizer progress log ----


def test_progress_log_requires_auth(client) -> None:
    """GET progress log requires JWT."""
    resp = client.get(f"/api/v1/organizer/events/{FAKE_EVENT_ID}/progress/log")
    assert resp.status_code == 401


def test_progress_log_success(client, monkeypatch) -> None:
    """GET progress log → 200."""
    monkeypatch.setattr(supabase_client, "get_user", lambda _: {"id": FAKE_USER_ID})

    log_entries = [
        {
            "id": "log1",
            "event_id": FAKE_EVENT_ID,
            "stage_id": FAKE_STAGE_ID_1,
            "stage_title": "海選",
            "status": "in_progress",
            "note": None,
            "changed_by": FAKE_USER_ID,
            "changed_at": "2026-03-25T10:00:00+00:00",
        },
    ]
    monkeypatch.setattr(progress_service, "get_progress_log", lambda *_, **__: log_entries)

    resp = client.get(
        f"/api/v1/organizer/events/{FAKE_EVENT_ID}/progress/log",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["log"]) == 1
    assert data["log"][0]["stage_title"] == "海選"


# ---- Invalid UUID ----


def test_invalid_event_id(client) -> None:
    """Invalid UUID → 400."""
    resp = client.get("/api/v1/events/not-a-uuid/progress")
    assert resp.status_code == 400
