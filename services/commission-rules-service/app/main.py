"""Commission Rules Service — TMF651 Agreement Management."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import router
from app.config import settings
from app.infrastructure.db.session import engine
from app.infrastructure.db.models import Base
from telco_common.middleware import CorrelationMiddleware, TenantMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Commission rules service started")
    yield
    await engine.dispose()


app = FastAPI(
    title="Commission Rules Service",
    description="TMF651 Agreement Management — commission schemes and rules",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(TenantMiddleware)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)
app.include_router(router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": settings.service_name}
