"""Gateway configuration from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Gateway settings loaded from env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    api_keys: str = ""  # Comma-separated valid API keys

    # Backends (comma-separated URLs for round-robin)
    orders_backends: str = "http://orders1:8001,http://orders2:8002"
    locations_backends: str = "http://locations1:8003,http://locations2:8004"

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    @property
    def orders_backend_list(self) -> list[str]:
        return [u.strip() for u in self.orders_backends.split(",") if u.strip()]

    @property
    def locations_backend_list(self) -> list[str]:
        return [u.strip() for u in self.locations_backends.split(",") if u.strip()]

    @property
    def valid_api_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


def get_settings() -> Settings:
    return Settings()
