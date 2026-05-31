"""Audit Service — append-only event audit log for all domain events."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import router
from app.config import settings
from app.infrastructure.db.session import engine
from app.infrastructure.db.models import Base
from telco_common.kafka import KafkaConsumer
from telco_common.middleware import CorrelationMiddleware, TenantMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    consumer_task = asyncio.create_task(_run_consumer())
    logger.info("Audit service started", topics=settings.audit_topics)
    yield
    consumer_task.cancel()
    await engine.dispose()


async def _run_consumer() -> None:
    from app.infrastructure.db.session import async_session_factory
    from app.infrastructure.kafka.consumers.audit_consumer import handle_any_event

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="audit-service",
        topics=settings.audit_topics,
    )
    await consumer.start()

    async def handler(event: dict) -> None:
        async with async_session_factory() as session:
            try:
                await handle_any_event(event, session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    await consumer.consume(handler)


app = FastAPI(title="Audit Service", description="Append-only audit log for all domain events", version="1.0.0", lifespan=lifespan)
app.add_middleware(TenantMiddleware)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
