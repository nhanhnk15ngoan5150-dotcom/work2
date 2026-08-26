from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import AppException


def test_app_exception_uses_stable_error_contract(
    application: FastAPI, client: TestClient
) -> None:
    @application.get("/_test/error")
    async def raise_test_error() -> None:
        raise AppException(
            code="TEST_ERROR",
            message="Expected test error",
            status_code=409,
            details={"reason": "contract-check"},
        )

    response = client.get("/_test/error", headers={"X-Request-ID": "error-request"})

    assert response.status_code == 409
    assert response.headers["X-Request-ID"] == "error-request"
    assert response.json() == {
        "request_id": "error-request",
        "error": {
            "code": "TEST_ERROR",
            "message": "Expected test error",
            "details": {"reason": "contract-check"},
        },
    }


def test_validation_error_uses_stable_error_contract(
    application: FastAPI, client: TestClient
) -> None:
    @application.get("/_test/items/{item_id}")
    async def get_test_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    response = client.get("/_test/items/not-an-integer")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]

