"""Base settings — each service extends this."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Keycloak
    keycloak_jwks_uri: str = "http://keycloak:8080/realms/telco/protocol/openid-connect/certs"
    keycloak_audience: str = "telco-services"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://tempo:4317"
    log_level: str = "INFO"
