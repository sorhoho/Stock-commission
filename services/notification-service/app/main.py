"""Notification Service — event-driven notifications via Kafka consumers."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.infrastructure.kafka.consumers.multi_event_consumer import start_notification_consumer
from telco_common.middleware import CorrelationMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer_task = asyncio.create_task(start_notification_consumer())
    logger.info("Notification service started")
    yield
    consumer_task.cancel()


app = FastAPI(title="Notification Service", description="Event-driven notifications", version="1.0.0", lifespan=lifespan)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
