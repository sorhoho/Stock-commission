from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "commission-rules-service"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres-commission-rules:5432/commission_rules"
    kafka_bootstrap_servers: str = "kafka:9092"
    keycloak_jwks_uri: str = "http://keycloak:8080/realms/telco/protocol/openid-connect/certs"
    keycloak_audience: str = "telco-services"
    log_level: str = "INFO"


settings = Settings()
