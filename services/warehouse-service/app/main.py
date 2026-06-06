"""FastAPI application entry point for warehouse-service."""

from __future__ import annotations

import asyncio
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

_kafka_producer: KafkaProducer | None = None


def get_kafka_producer() -> KafkaProducer:
    if _kafka_producer is None:
        raise RuntimeError("Kafka producer not initialised")
    return _kafka_producer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _kafka_producer

    log.info("Starting warehouse-service", service=settings.service_name)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _kafka_producer = KafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await _kafka_producer.start()
    app.state.kafka_producer = _kafka_producer

    from app.infrastructure.kafka.consumers.sellin_consumer import start_consumer
    consumer_task = asyncio.create_task(
        start_consumer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id="warehouse-service-sellin",
            kafka_producer=_kafka_producer,
            inventory_service_url=settings.inventory_service_url,
        )
    )

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

    log.info("Shutting down warehouse-service")
    await _kafka_producer.stop()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Warehouse Service",
        description="WMS — bin locations, pick lists, packing & dispatch",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantMiddleware)
    app.add_middleware(CorrelationMiddleware)

    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")

    from app.api.v1.router import router as v1_router
    app.include_router(v1_router)

    @app.get("/health", tags=["ops"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "warehouse-service"}

    return app


app = create_app()
