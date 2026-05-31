"""Sell-in-service configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "sell-in-service"

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@sellin-db:5432/sellin"
    )

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_consumer_group_id: str = "sell-in-service-group"

    # Redis
    redis_url: str = "redis://redis:6379/4"

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
