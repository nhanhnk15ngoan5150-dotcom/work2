from pathlib import Path

from app.core.config import (
    DEMO_KNOWLEDGE_DIR,
    KNOWLEDGE_INDEX_PATH,
    PROJECT_ROOT,
    Settings,
)


def test_settings_load_app_prefixed_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "staging")
    monkeypatch.setenv("APP_DEFAULT_TENANT_ID", "tenant_from_env")

    settings = Settings(_env_file=None)

    assert settings.environment == "staging"
    assert settings.default_tenant_id == "tenant_from_env"


def test_settings_load_embedding_environment(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://embedding.example/v1")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
    monkeypatch.setenv("EMBEDDING_MODEL", "test-model")

    settings = Settings(_env_file=None)

    assert settings.embedding_provider == "openai_compatible"
    assert settings.embedding_base_url == "https://embedding.example/v1"
    assert settings.embedding_api_key == "test-key"
    assert settings.embedding_model == "test-model"


def test_project_data_paths_do_not_depend_on_working_directory(
    monkeypatch,
) -> None:
    monkeypatch.chdir(PROJECT_ROOT / "tests")

    settings = Settings(_env_file=None)

    assert Path(settings.database_url.removeprefix("sqlite:///")) == (
        PROJECT_ROOT / "data" / "moneki.db"
    )
    assert KNOWLEDGE_INDEX_PATH == PROJECT_ROOT / "data" / "knowledge_index.json"
    assert DEMO_KNOWLEDGE_DIR == PROJECT_ROOT / "data" / "demo_knowledge"
