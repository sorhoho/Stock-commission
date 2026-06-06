"""Product-catalog-service configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "product-catalog-service"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/product_catalog"
    keycloak_jwks_uri: str = "http://keycloak:8080/realms/telco/protocol/openid-connect/certs"
    keycloak_audience: str = "telco-services"
    log_level: str = "INFO"
    debug: bool = False
    allowed_origins: list[str] = ["*"]


settings = Settings()
