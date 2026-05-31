"""FastAPI application entry point for sell-out-service (TMF699 Sales Management)."""

from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.infrastructure.db.session import engine
from telco_common.db.base import Base
from telco_common.kafka.producer_factory import KafkaProducer
from telco_common.middleware.correlation_middleware import CorrelationMiddleware
from telco_common.middleware.tenant_middleware import TenantMiddleware

log = structlog.get_logger(__name__)

# Module-level Kafka producer shared across the app lifecycle
_kafka_producer: KafkaProducer | None = None


def get_kafka_producer() -> KafkaProducer:
    """Return the app-level Kafka producer (set during lifespan startup)."""
    if _kafka_producer is None:
        raise RuntimeError("Kafka producer not initialised")
    return _kafka_producer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle startup and shutdown events."""
    global _kafka_producer

    log.info("Starting sell-out-service", service=settings.service_name)

    # Initialise database tables (Alembic handles schema migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start Kafka producer
    _kafka_producer = KafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await _kafka_producer.start()
    log.info("Kafka producer started", bootstrap_servers=settings.kafka_bootstrap_servers)

    # Expose on app state for dependency injection
    app.state.kafka_producer = _kafka_producer

    yield

    # Shutdown
    log.info("Shutting down sell-out-service")
    await _kafka_producer.stop()
    await engine.dispose()
    log.info("sell-out-service shutdown complete")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Sell-Out Service",
        description="TMF699 Sales Management for Telco Distribution sell-out transactions",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Middleware — outermost first
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantMiddleware)
    app.add_middleware(CorrelationMiddleware)

    # Prometheus metrics
    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")

    # Routers
    from app.api.v1.router import router as v1_router

    app.include_router(v1_router)

    @app.get("/health", tags=["ops"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    return app


app = create_app()
