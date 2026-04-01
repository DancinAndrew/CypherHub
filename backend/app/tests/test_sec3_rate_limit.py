"""SEC-3: Rate limit 補全 + 檔案上傳 MIME 白名單測試。

新增 rate limit：
- orders: create 30/min, cancel 30/min
- payments/checkout: 30/min
- tickets: cancel 20/min, resend 5/min
- organizer: apply 5/min, create event 10/min, media upload 10/min
- admin: refund 10/min, approval 10/min, settlements 5/min, payout 10/min
- settlements: payout-requests 5/min

MIME 白名單：僅允許 image/jpeg, image/png, image/webp, image/gif
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock

from app.services.events_service import events_service
from app.services.orders_service import orders_service
from app.services.payment_service import payment_service
from app.services.supabase_client import supabase_client
from app.services.ticket_service import ticket_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JWT = "fake.jwt.token"
_USER_ID = "5f67f4da-44d7-46a0-bd27-b94692d7d3c2"
_EVENT_ID = "ff895f3f-dd7b-496c-a6ff-6c9d95de43e6"
_ORDER_ID = "aaaa1111-bbbb-cccc-dddd-eeeeffffaaaa"
_TICKET_ID = "f5de9492-6fcb-49f8-bb27-a9ff728acbbf"
_ORG_ID = "11111111-2222-3333-4444-555555555555"
_HEADERS = {"Authorization": f"Bearer {_JWT}"}


def _mock_auth(monkeypatch):
    monkeypatch.setattr(supabase_client, "get_user", lambda token: {"id": _USER_ID})


# ---------------------------------------------------------------------------
# Orders rate limit
# ---------------------------------------------------------------------------


def test_create_order_rate_limit(client, monkeypatch) -> None:
    """POST /orders：30/min，第 31 次應回 429。"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(
        orders_service,
        "create_hold_order",
        MagicMock(return_value=_ORDER_ID),
    )
    monkeypatch.setattr(
        orders_service,
        "get_order_detail",
        MagicMock(
            return_value={
                "order": {
                    "id": _ORDER_ID,
                    "user_id": _USER_ID,
                    "status": "holding",
                    "total_cents": 0,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                },
                "items": [],
                "payments": [],
            }
        ),
    )

    for i in range(30):
        resp = client.post(
            "/api/v1/orders",
            headers=_HEADERS,
            json={
                "items": [
                    {"ticket_type_id": "34f9bc6e-bfdf-4668-a2a4-4e6ff2f3f0ce", "quantity": 1}
                ],
            },
        )
        assert resp.status_code == 201, f"Request {i+1} expected 201, got {resp.status_code}"

    resp = client.post(
        "/api/v1/orders",
        headers=_HEADERS,
        json={
            "items": [{"ticket_type_id": "34f9bc6e-bfdf-4668-a2a4-4e6ff2f3f0ce", "quantity": 1}],
        },
    )
    assert resp.status_code == 429


def test_cancel_order_rate_limit(client, monkeypatch) -> None:
    """DELETE /orders/<id>：30/min，第 31 次應回 429。"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(
        orders_service,
        "cancel_holding_order",
        MagicMock(return_value=None),
    )

    for i in range(30):
        resp = client.delete(f"/api/v1/orders/{_ORDER_ID}", headers=_HEADERS)
        assert resp.status_code == 200, f"Request {i+1} expected 200, got {resp.status_code}"

    resp = client.delete(f"/api/v1/orders/{_ORDER_ID}", headers=_HEADERS)
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Payments rate limit
# ---------------------------------------------------------------------------


def test_checkout_rate_limit(client, monkeypatch) -> None:
    """POST /payments/checkout：30/min，第 31 次應回 429。"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(
        payment_service,
        "create_checkout",
        MagicMock(return_value={"form_params": {}, "cashier_url": "https://example.com"}),
    )

    for i in range(30):
        resp = client.post(
            "/api/v1/payments/checkout",
            headers=_HEADERS,
            json={"order_id": _ORDER_ID},
        )
        assert resp.status_code == 200, f"Request {i+1} expected 200, got {resp.status_code}"

    resp = client.post(
        "/api/v1/payments/checkout",
        headers=_HEADERS,
        json={"order_id": _ORDER_ID},
    )
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Tickets rate limit
# ---------------------------------------------------------------------------


def test_cancel_ticket_rate_limit(client, monkeypatch) -> None:
    """DELETE /me/tickets/<id>：20/min，第 21 次應回 429。"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(
        ticket_service,
        "cancel_ticket",
        MagicMock(return_value=None),
    )

    for i in range(20):
        resp = client.delete(f"/api/v1/me/tickets/{_TICKET_ID}", headers=_HEADERS)
        assert resp.status_code == 200, f"Request {i+1} expected 200, got {resp.status_code}"

    resp = client.delete(f"/api/v1/me/tickets/{_TICKET_ID}", headers=_HEADERS)
    assert resp.status_code == 429


def test_resend_ticket_rate_limit(client, monkeypatch) -> None:
    """POST /me/tickets/<id>/resend：5/min，第 6 次應回 429。"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(
        ticket_service,
        "resend_ticket_email",
        MagicMock(return_value=None),
    )

    for i in range(5):
        resp = client.post(f"/api/v1/me/tickets/{_TICKET_ID}/resend", headers=_HEADERS)
        assert resp.status_code == 200, f"Request {i+1} expected 200, got {resp.status_code}"

    resp = client.post(f"/api/v1/me/tickets/{_TICKET_ID}/resend", headers=_HEADERS)
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Organizer rate limit
# ---------------------------------------------------------------------------


def test_organizer_apply_rate_limit(client, monkeypatch) -> None:
    """POST /organizer/apply：5/min，第 6 次應回 429。"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(
        events_service,
        "apply_organizer",
        MagicMock(return_value={"id": _ORG_ID, "name": "TestOrg"}),
    )

    for i in range(5):
        resp = client.post(
            "/api/v1/organizer/apply",
            headers=_HEADERS,
            json={"name": "TestOrg"},
        )
        assert resp.status_code == 201, f"Request {i+1} expected 201, got {resp.status_code}"

    resp = client.post(
        "/api/v1/organizer/apply",
        headers=_HEADERS,
        json={"name": "TestOrg"},
    )
    assert resp.status_code == 429


def test_organizer_create_event_rate_limit(client, monkeypatch) -> None:
    """POST /organizer/events：10/min，第 11 次應回 429。"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(
        events_service,
        "create_event",
        MagicMock(
            return_value={
                "id": _EVENT_ID,
                "title": "Test",
                "org_id": _ORG_ID,
                "status": "draft",
                "start_at": "2026-06-01T10:00:00Z",
                "end_at": "2026-06-01T18:00:00Z",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ),
    )

    for i in range(10):
        resp = client.post(
            "/api/v1/organizer/events",
            headers=_HEADERS,
            json={
                "title": "Test Event",
                "org_id": _ORG_ID,
                "start_at": "2026-06-01T10:00:00Z",
                "end_at": "2026-06-01T18:00:00Z",
            },
        )
        assert resp.status_code == 201, f"Request {i+1} expected 201, got {resp.status_code}"

    resp = client.post(
        "/api/v1/organizer/events",
        headers=_HEADERS,
        json={"title": "Test Event", "org_id": _ORG_ID},
    )
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# File upload MIME whitelist
# ---------------------------------------------------------------------------


def test_upload_media_allowed_jpeg(client, monkeypatch) -> None:
    """image/jpeg → 201"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(events_service, "require_event_admin", MagicMock(return_value=None))
    monkeypatch.setattr(
        events_service,
        "upload_event_media",
        MagicMock(return_value={"id": "media-1", "url": "https://example.com/img.jpg"}),
    )

    data = {"file": (io.BytesIO(b"fake image data"), "test.jpg", "image/jpeg")}
    resp = client.post(
        f"/api/v1/organizer/events/{_EVENT_ID}/media",
        headers=_HEADERS,
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201


def test_upload_media_allowed_png(client, monkeypatch) -> None:
    """image/png → 201"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(events_service, "require_event_admin", MagicMock(return_value=None))
    monkeypatch.setattr(
        events_service,
        "upload_event_media",
        MagicMock(return_value={"id": "media-1", "url": "https://example.com/img.png"}),
    )

    data = {"file": (io.BytesIO(b"fake image data"), "test.png", "image/png")}
    resp = client.post(
        f"/api/v1/organizer/events/{_EVENT_ID}/media",
        headers=_HEADERS,
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201


def test_upload_media_allowed_webp(client, monkeypatch) -> None:
    """image/webp → 201"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(events_service, "require_event_admin", MagicMock(return_value=None))
    monkeypatch.setattr(
        events_service,
        "upload_event_media",
        MagicMock(return_value={"id": "media-1", "url": "https://example.com/img.webp"}),
    )

    data = {"file": (io.BytesIO(b"fake image data"), "test.webp", "image/webp")}
    resp = client.post(
        f"/api/v1/organizer/events/{_EVENT_ID}/media",
        headers=_HEADERS,
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201


def test_upload_media_allowed_gif(client, monkeypatch) -> None:
    """image/gif → 201"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(events_service, "require_event_admin", MagicMock(return_value=None))
    monkeypatch.setattr(
        events_service,
        "upload_event_media",
        MagicMock(return_value={"id": "media-1", "url": "https://example.com/img.gif"}),
    )

    data = {"file": (io.BytesIO(b"fake image data"), "test.gif", "image/gif")}
    resp = client.post(
        f"/api/v1/organizer/events/{_EVENT_ID}/media",
        headers=_HEADERS,
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201


def test_upload_media_rejected_html(client, monkeypatch) -> None:
    """text/html → 400"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(events_service, "require_event_admin", MagicMock(return_value=None))

    data = {"file": (io.BytesIO(b"<html>xss</html>"), "evil.html", "text/html")}
    resp = client.post(
        f"/api/v1/organizer/events/{_EVENT_ID}/media",
        headers=_HEADERS,
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "不支援" in resp.get_json()["error"]["message"]


def test_upload_media_rejected_svg(client, monkeypatch) -> None:
    """image/svg+xml → 400（SVG 可含 XSS）"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(events_service, "require_event_admin", MagicMock(return_value=None))

    data = {"file": (io.BytesIO(b"<svg>xss</svg>"), "evil.svg", "image/svg+xml")}
    resp = client.post(
        f"/api/v1/organizer/events/{_EVENT_ID}/media",
        headers=_HEADERS,
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_media_rejected_octet_stream(client, monkeypatch) -> None:
    """application/octet-stream → 400"""
    _mock_auth(monkeypatch)
    monkeypatch.setattr(events_service, "require_event_admin", MagicMock(return_value=None))

    data = {"file": (io.BytesIO(b"\x00\x01\x02"), "unknown.bin", "application/octet-stream")}
    resp = client.post(
        f"/api/v1/organizer/events/{_EVENT_ID}/media",
        headers=_HEADERS,
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
