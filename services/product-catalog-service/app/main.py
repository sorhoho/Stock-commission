"""FastAPI application entry point for product-catalog-service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.infrastructure.db.session import engine
from telco_common.db.base import Base
from telco_common.middleware.correlation_middleware import CorrelationMiddleware
from telco_common.middleware.tenant_middleware import TenantMiddleware

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("Starting product-catalog-service")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    log.info("product-catalog-service stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Product Catalog Service",
        description="TMF620 Product Catalog for Telco Distribution",
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
        return {"status": "ok", "service": "product-catalog-service"}

    return app


app = create_app()
