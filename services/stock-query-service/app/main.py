"""FastAPI application entry point for stock-query-service (CQRS read model)."""

from __future__ import annotations

import asyncio
import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.infrastructure.cache.stock_read_model import StockReadModel
from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer
from telco_common.middleware.correlation_middleware import CorrelationMiddleware
from telco_common.middleware.tenant_middleware import TenantMiddleware

log = structlog.get_logger(__name__)

# Module-level singletons set during lifespan
_redis_client: aioredis.Redis | None = None
_stock_read_model: StockReadModel | None = None
_consumer_task: asyncio.Task | None = None


def get_redis_client() -> aioredis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client not initialised")
    return _redis_client


def get_stock_read_model() -> StockReadModel:
    if _stock_read_model is None:
        raise RuntimeError("StockReadModel not initialised")
    return _stock_read_model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle startup and shutdown events — no DB, pure Redis + Kafka."""
    global _redis_client, _stock_read_model, _consumer_task

    log.info("Starting stock-query-service", service=settings.service_name)

    # Connect to Redis
    _redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    await _redis_client.ping()
    log.info("Redis connection established", url=settings.redis_url)

    # Build read model
    _stock_read_model = StockReadModel(
        redis_client=_redis_client,
        key_ttl=settings.redis_key_ttl_seconds,
    )

    # Expose on app.state for dependency injection
    app.state.redis_client = _redis_client
    app.state.stock_read_model = _stock_read_model

    # Start Kafka consumer as background task
    consumer = InventoryConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group_id,
        read_model=_stock_read_model,
    )
    _consumer_task = asyncio.create_task(consumer.run(), name="inventory-consumer")
    log.info("Kafka inventory consumer task started")

    yield

    # Shutdown
    log.info("Shutting down stock-query-service")
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    await consumer.stop()
    await _redis_client.aclose()
    log.info("stock-query-service shutdown complete")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Stock Query Service",
        description="CQRS read-model service for TMF637 stock availability — Redis-backed, Kafka-driven",
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
