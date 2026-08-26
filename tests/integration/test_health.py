from uuid import UUID

from fastapi.testclient import TestClient


def test_health_returns_application_status(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Restaurant Business AI Test",
        "version": "0.1.0-test",
        "environment": "test",
    }
    UUID(response.headers["X-Request-ID"])


def test_health_preserves_caller_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "caller-request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "caller-request-123"


def test_health_replaces_oversized_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "x" * 129})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "x" * 129
    UUID(response.headers["X-Request-ID"])

