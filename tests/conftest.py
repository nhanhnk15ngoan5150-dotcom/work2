import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.infrastructure.database.sqlite import SQLiteBackend
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_name="Restaurant Business AI Test",
        app_version="0.1.0-test",
        environment="test",
        log_level="CRITICAL",
        embedding_api_key=None,
        llm_api_key=None,
    )


@pytest.fixture
def application(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(application: FastAPI) -> TestClient:
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def database_backend() -> SQLiteBackend:
    backend = SQLiteBackend(Settings(_env_file=None).database_url)
    yield backend
    backend.dispose()
