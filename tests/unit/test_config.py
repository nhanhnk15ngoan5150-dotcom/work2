from app.core.config import Settings


def test_settings_load_app_prefixed_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "staging")
    monkeypatch.setenv("APP_DEFAULT_TENANT_ID", "tenant_from_env")

    settings = Settings(_env_file=None)

    assert settings.environment == "staging"
    assert settings.default_tenant_id == "tenant_from_env"

