from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "payout-service"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres-payout:5432/payout"
    kafka_bootstrap_servers: str = "kafka:9092"
    keycloak_jwks_uri: str = "http://keycloak:8080/realms/telco/protocol/openid-connect/certs"
    keycloak_audience: str = "telco-services"
    payment_gateway_url: str = "http://payment-gateway:8080"
    payout_schedule_cron: str = "0 2 1 * *"
    log_level: str = "INFO"


settings = Settings()
