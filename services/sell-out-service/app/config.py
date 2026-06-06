"""Sell-out-service configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "sell-out-service"

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@sellout-db:5432/sellout"
    )

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Redis
    redis_url: str = "redis://redis:6379/2"

    # Keycloak / Auth
    keycloak_jwks_uri: str = (
        "http://keycloak:8080/realms/telco/protocol/openid-connect/certs"
    )
    keycloak_audience: str = "telco-services"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://tempo:4317"
    log_level: str = "INFO"
    debug: bool = False

    # CORS
    allowed_origins: list[str] = ["*"]

    # Stock availability check before sale
    stock_query_service_url: str = "http://stock-query-service:8004"


settings = Settings()
