import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_name="Restaurant Business AI Test",
        app_version="0.1.0-test",
        environment="test",
        log_level="CRITICAL",
    )


@pytest.fixture
def application(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(application: FastAPI) -> TestClient:
    with TestClient(application) as test_client:
        yield test_client

