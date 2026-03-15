from __future__ import annotations

from app.services.supabase_client import supabase_client
from app.services.ticket_service import ticket_service


def test_me_tickets_route_scopes_to_authenticated_user(client, monkeypatch) -> None:
    jwt = "fake.jwt.token"
    user_id = "f4f65d24-a934-4af7-9e6b-3cad7f24652d"
    captured: dict[str, str] = {}

    monkeypatch.setattr(supabase_client, "get_user", lambda _token: {"id": user_id})

    def _fake_list_my_tickets(jwt_token: str, scoped_user_id: str) -> list[dict]:
        captured["jwt"] = jwt_token
        captured["user_id"] = scoped_user_id
        return []

    monkeypatch.setattr(ticket_service, "list_my_tickets", _fake_list_my_tickets)

    response = client.get(
        "/api/v1/me/tickets",
        headers={"Authorization": f"Bearer {jwt}"},
    )

    assert response.status_code == 200
    assert captured == {"jwt": jwt, "user_id": user_id}


def test_resend_ticket_route_scopes_to_authenticated_user(client, monkeypatch) -> None:
    jwt = "fake.jwt.token"
    user_id = "f4f65d24-a934-4af7-9e6b-3cad7f24652d"
    ticket_id = "5e08e9a0-8b6e-411a-9852-2f99d07cf5ab"
    captured: dict[str, str] = {}

    monkeypatch.setattr(supabase_client, "get_user", lambda _token: {"id": user_id})

    def _fake_resend_ticket_email(
        jwt_token: str, scoped_ticket_id, scoped_user_id: str, *, to_email: str | None = None
    ) -> None:
        captured["jwt"] = jwt_token
        captured["ticket_id"] = str(scoped_ticket_id)
        captured["user_id"] = scoped_user_id
        captured["to_email"] = to_email

    monkeypatch.setattr(ticket_service, "resend_ticket_email", _fake_resend_ticket_email)

    response = client.post(
        f"/api/v1/me/tickets/{ticket_id}/resend",
        headers={"Authorization": f"Bearer {jwt}"},
    )

    assert response.status_code == 200
    assert captured["jwt"] == jwt and captured["ticket_id"] == ticket_id and captured["user_id"] == user_id


def test_cancel_ticket_route_scopes_to_authenticated_user(client, monkeypatch) -> None:
    jwt = "fake.jwt.token"
    user_id = "f4f65d24-a934-4af7-9e6b-3cad7f24652d"
    ticket_id = "5e08e9a0-8b6e-411a-9852-2f99d07cf5ab"
    captured: dict[str, str] = {}

    monkeypatch.setattr(supabase_client, "get_user", lambda _token: {"id": user_id})

    def _fake_cancel_ticket(jwt_token: str, scoped_ticket_id, scoped_user_id: str) -> None:
        captured["jwt"] = jwt_token
        captured["ticket_id"] = str(scoped_ticket_id)
        captured["user_id"] = scoped_user_id

    monkeypatch.setattr(ticket_service, "cancel_ticket", _fake_cancel_ticket)

    response = client.delete(
        f"/api/v1/me/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {jwt}"},
    )

    assert response.status_code == 200
    assert captured == {"jwt": jwt, "ticket_id": ticket_id, "user_id": user_id}
