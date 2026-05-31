"""Payout Service — TMF666 Financial Management."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import router
from app.config import settings
from app.dependencies import set_kafka_producer
from app.domain.scheduler import create_scheduler
from app.infrastructure.db.session import engine
from app.infrastructure.db.models import Base
from telco_common.kafka import KafkaConsumer, KafkaProducer
from telco_common.events import Topics
from telco_common.middleware import CorrelationMiddleware, TenantMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await producer.start()
    set_kafka_producer(producer)

    scheduler = create_scheduler(lambda: None, settings.payout_schedule_cron)
    scheduler.start()

    consumer_task = asyncio.create_task(_run_consumer(producer))
    logger.info("Payout service started")
    yield

    consumer_task.cancel()
    scheduler.shutdown(wait=False)
    await producer.stop()
    await engine.dispose()


async def _run_consumer(producer: KafkaProducer) -> None:
    from app.infrastructure.db.session import async_session_factory
    from app.infrastructure.kafka.consumers.statement_consumer import handle_statement_confirmed
    from app.infrastructure.db.repository import PayoutRequestRepository

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="payout-service",
        topics=[Topics.COMMISSION_STATEMENT_CONFIRMED],
    )
    await consumer.start()

    async def handler(event: dict) -> None:
        async with async_session_factory() as session:
            try:
                repo = PayoutRequestRepository(session)
                await handle_statement_confirmed(event, repo, producer)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    await consumer.consume(handler, dlq_producer=producer)


app = FastAPI(title="Payout Service", description="TMF666 — payout management", version="1.0.0", lifespan=lifespan)
app.add_middleware(TenantMiddleware)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
