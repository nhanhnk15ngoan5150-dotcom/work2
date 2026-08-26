from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{(PROJECT_ROOT / 'data' / 'moneki.db').as_posix()}"


class Settings(BaseSettings):
    """Application configuration loaded from APP_* environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
        case_sensitive=False,
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
