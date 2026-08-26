from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()

