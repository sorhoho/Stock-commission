"""Commission-calculation-service configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "commission-calculation-service"

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@commission-db:5432/commission"
    )

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_consumer_group_id: str = "commission-calculation-service"

    # Redis
    redis_url: str = "redis://redis:6379/3"

    # Upstream services
    commission_rules_service_url: str = "http://commission-rules-service:8000"

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


settings = Settings()
