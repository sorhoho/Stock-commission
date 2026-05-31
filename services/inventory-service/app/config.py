"""Inventory-service configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "inventory-service"

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@inventory-db:5432/inventory"
    )

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Redis
    redis_url: str = "redis://redis:6379/1"

    # Keycloak / Auth
    keycloak_jwks_uri: str = (
        "http://keycloak:8080/realms/telco/protocol/openid-connect/certs"
    )
    keycloak_audience: str = "telco-services"

    # Observability
    log_level: str = "INFO"
    debug: bool = False

    # CORS
    allowed_origins: list[str] = ["*"]


settings = Settings()
