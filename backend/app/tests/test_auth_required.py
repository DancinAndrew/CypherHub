from __future__ import annotations


def test_me_tickets_requires_bearer_token(client) -> None:
    response = client.get("/api/v1/me/tickets")

    assert response.status_code == 401
    assert response.get_json() == {
        "error": {
            "code": "AUTH_REQUIRED",
            "message": "Missing Authorization Bearer token",
            "details": None,
        }
    }
