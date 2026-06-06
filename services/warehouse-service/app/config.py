"""Warehouse-service configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "warehouse-service"

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@postgres:5432/warehouse"
    )
    kafka_bootstrap_servers: str = "kafka:9092"
    keycloak_jwks_uri: str = (
        "http://keycloak:8080/realms/telco/protocol/openid-connect/certs"
    )
    keycloak_audience: str = "telco-services"
    otel_exporter_otlp_endpoint: str = "http://tempo:4317"
    log_level: str = "INFO"
    debug: bool = False
    allowed_origins: list[str] = ["*"]

    # Inventory service URL for auto-creating GoodsReceipts from sell-in events
    inventory_service_url: str = "http://inventory-service:8001"


settings = Settings()
