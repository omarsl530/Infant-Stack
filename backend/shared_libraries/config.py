"""
Shared configuration for all backend services.
Uses pydantic-settings for environment variable loading.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "admin"
    postgres_password: str = "securepassword"
    postgres_db: str = "biobaby_db"
    database_url: str | None = None

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # MongoDB
    mongodb_host: str = "localhost"
    mongodb_port: int = 27017
    mongodb_database: str = "infant_stack_logs"

    @property
    def mongodb_url(self) -> str:
        """Construct MongoDB connection URL."""
        return f"mongodb://{self.mongodb_host}:{self.mongodb_port}"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"

    # MQTT
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_movements: str = "hospital/+/movements"
    mqtt_topic_alerts: str = "hospital/alerts"

    # JWT Authentication
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Keycloak Identity Provider
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "infant-stack"
    keycloak_client_id: str = "infant-stack-spa"
    keycloak_admin_client_id: str = "infant-stack-admin"
    keycloak_admin_client_secret: str = "admin-client-secret-change-in-production"

    @property
    def keycloak_issuer(self) -> str:
        """Construct Keycloak issuer URL (external, for token validation)."""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_internal_url(self) -> str:
        """
        Internal Keycloak URL for Docker networking.
        When running inside Docker, use the container name instead of localhost.
        """
        import os

        # Check if running inside Docker (common indicators)
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            return "http://keycloak:8080"
        return self.keycloak_url

    @property
    def keycloak_jwks_url(self) -> str:
        """Construct Keycloak JWKS URL (uses internal URL for Docker networking)."""
        return f"{self.keycloak_internal_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"

    @property
    def keycloak_openid_config_url(self) -> str:
        """Construct Keycloak OpenID Configuration URL."""
        return f"{self.keycloak_issuer}/.well-known/openid-configuration"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
