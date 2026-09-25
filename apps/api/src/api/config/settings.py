"""Typed runtime configuration loaded from environment variables."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Deployment and request-facing settings shared by application modules."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = Field("production", validation_alias="ENVIRONMENT")
    debug: bool = Field(False, validation_alias="DEBUG")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    release_version: str = Field("goblin-assistant@1.0.0", validation_alias="RELEASE_VERSION")
    port: int = Field(8080, validation_alias="PORT")

    frontend_url: str = Field("http://localhost:3000", validation_alias="FRONTEND_URL")
    backend_url: str = Field("http://localhost:8004", validation_alias="BACKEND_URL")
    error_type_base_url: str | None = Field(
        None,
        validation_alias=AliasChoices("ERROR_TYPE_BASE_URL", "BACKEND_URL"),
    )
    allowed_origins: str = Field("", validation_alias="ALLOWED_ORIGINS")

    database_url: str = Field(
        "sqlite+aiosqlite:///./goblin_assistant.db", validation_alias="DATABASE_URL"
    )
    redis_url: str = Field("redis://localhost:6379/0", validation_alias="REDIS_URL")
    local_llm_api_key: str | None = Field(None, validation_alias="LOCAL_LLM_API_KEY")
    auth_cookie_samesite: str | None = Field(None, validation_alias="AUTH_COOKIE_SAMESITE")
    rate_limit_enabled: bool | None = Field(None, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(100, validation_alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(1000, validation_alias="RATE_LIMIT_PER_HOUR")

    @field_validator("debug", "rate_limit_enabled", mode="before")
    @classmethod
    def parse_bool(cls, value: object) -> object:
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value

    @property
    def error_type_url(self) -> str:
        """Base URL for stable error-type links in API responses."""
        return (self.error_type_base_url or self.backend_url).rstrip("/")


def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Reset settings for tests and explicit runtime reconfiguration."""
    # Kept as a compatibility hook for callers that previously cached settings.
    return None
