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
    jwt_secret_key: SecretStr = SecretStr("development-only-change-this-secret-before-use")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=20, ge=1, le=1440)
    jwt_issuer: str = "service-desk-api"
    jwt_audience: str = "service-desk-clients"

    def validate_security_settings(self) -> None:
        """Reject insecure development defaults when running in production."""
        if self.environment.lower() == "production":
            secret = self.jwt_secret_key.get_secret_value()
            if len(secret) < 32 or secret.startswith("development-only"):
                raise ValueError("JWT_SECRET_KEY must be a strong, unique production secret")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for dependency injection."""
    return Settings()
