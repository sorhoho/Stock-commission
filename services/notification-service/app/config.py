"""Notification-service configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "notification-service"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_consumer_group_id: str = "notification-service"

    # SMTP (mock mode — no real emails sent in dev/test)
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = "notifications@telco.local"
    smtp_password: str = ""
    smtp_from_name: str = "Telco Distribution"
    smtp_mock: bool = True  # When True, log instead of sending

    # SMS gateway (optional)
    sms_gateway_url: str | None = None
    sms_mock: bool = True  # When True, log instead of sending

    # Webhook
    webhook_base_url: str = "http://internal-webhook-router:8080"

    # Observability
    log_level: str = "INFO"
    debug: bool = False

    # CORS (for health endpoint)
    allowed_origins: list[str] = ["*"]


settings = Settings()
