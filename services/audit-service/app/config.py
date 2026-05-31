from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "audit-service"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres-audit:5432/audit"
    kafka_bootstrap_servers: str = "kafka:9092"
    keycloak_jwks_uri: str = "http://keycloak:8080/realms/telco/protocol/openid-connect/certs"
    keycloak_audience: str = "telco-services"
    log_level: str = "INFO"
    audit_topics: list[str] = [
        "telco.sales.sellout.completed",
        "telco.sales.sellout.reversed",
        "telco.inventory.stock.transferred",
        "telco.inventory.stock.adjusted",
        "telco.commission.event.calculated",
        "telco.commission.statement.confirmed",
        "telco.payout.request.created",
        "telco.payout.request.completed",
        "telco.party.dealer.onboarded",
    ]


settings = Settings()
