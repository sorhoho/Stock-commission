"""FastAPI dependency providers for warehouse-service."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import AsyncSessionLocal
from telco_common.kafka.producer_factory import KafkaProducer


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_kafka_producer(request: Request) -> KafkaProducer:
    producer: KafkaProducer | None = getattr(request.app.state, "kafka_producer", None)
    if producer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kafka producer not available",
        )
    return producer


def get_current_tenant_id(request: Request) -> str:
    tenant_id: str = getattr(request.state, "tenant_id", "")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Tenant-ID header",
        )
    return tenant_id


def get_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


DbSession = Annotated[AsyncSession, Depends(get_db)]
KafkaProducerDep = Annotated[KafkaProducer, Depends(get_kafka_producer)]
TenantId = Annotated[str, Depends(get_current_tenant_id)]
CorrelationId = Annotated[str, Depends(get_correlation_id)]
