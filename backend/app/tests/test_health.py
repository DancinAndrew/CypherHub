from __future__ import annotations


def test_health_endpoint(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
