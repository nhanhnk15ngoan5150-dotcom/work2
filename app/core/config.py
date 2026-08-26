from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{(PROJECT_ROOT / 'data' / 'moneki.db').as_posix()}"
KNOWLEDGE_INDEX_PATH = PROJECT_ROOT / "data" / "knowledge_index.json"
DEMO_KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "demo_knowledge"


class Settings(BaseSettings):
    """Application configuration loaded from APP_* environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_name: str = "Restaurant Business AI"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = (
        "development"
    )
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    default_tenant_id: str = Field(default="dev_tenant", min_length=1, max_length=128)
    database_url: str = DEFAULT_DATABASE_URL
    embedding_provider: str = Field(
        default="openai_compatible",
        validation_alias=AliasChoices("EMBEDDING_PROVIDER", "APP_EMBEDDING_PROVIDER"),
    )
    embedding_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("EMBEDDING_BASE_URL", "APP_EMBEDDING_BASE_URL"),
    )
    embedding_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_API_KEY", "APP_EMBEDDING_API_KEY"),
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "APP_EMBEDDING_MODEL"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
