"""Commission Calculation Service — TMF666 Account & Finance Management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.config import settings
from app.infrastructure.db.session import engine
from app.infrastructure.db.models import Base
from app.infrastructure.kafka.consumer_runner import start_consumer
from telco_common.middleware import CorrelationMiddleware, TenantMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    consumer_task = asyncio.create_task(start_consumer())
    logger.info("Commission calculation service started")
    yield
    consumer_task.cancel()
    await engine.dispose()
    logger.info("Commission calculation service stopped")


app = FastAPI(
    title="Commission Calculation Service",
    description="TMF666 Account & Finance Management — commission calculation and statements",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(TenantMiddleware)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": settings.service_name}
