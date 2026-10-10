"""Application configuration loaded from environment variables.

All security-sensitive values are read from the environment. Insecure defaults
are only acceptable in non-production environments and are guarded at startup.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "OpsCommand"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # --- Security ---
    secret_key: str = "insecure-dev-secret-change-me"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 14 * 24 * 60 * 60
    jwt_algorithm: str = "HS256"
    # When true, startup refuses to boot with the insecure default secret.
    enforce_secure_secret: bool = True

    # --- Database ---
    database_url: str = "postgresql+psycopg://opscommand:opscommand@localhost:5432/opscommand"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Login throttling ---
    login_max_attempts: int = 5
    login_window_seconds: int = 60

    # --- Observability ---
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"
    metrics_enabled: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
