"""Centralized, environment-driven application settings."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Service Desk API"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://service_desk:service_desk@localhost:5432/service_desk"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=list)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for dependency injection."""
    return Settings()
