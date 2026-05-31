"""FastAPI dependency injection helpers for sell-out-service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repository import SaleTransactionRepository
from app.infrastructure.db.session import get_db_session
from telco_common.kafka.producer_factory import KafkaProducer


def get_kafka_producer(request: Request) -> KafkaProducer:
    """Retrieve the shared Kafka producer from app state."""
    return request.app.state.kafka_producer


def get_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SaleTransactionRepository:
    """Provide a SaleTransactionRepository bound to the current DB session."""
    return SaleTransactionRepository(session)


def get_tenant_id(request: Request) -> str:
    """Extract tenant_id from request state (set by TenantMiddleware)."""
    return request.state.tenant_id


def get_correlation_id(request: Request) -> str:
    """Extract correlation_id from request state (set by CorrelationMiddleware)."""
    return getattr(request.state, "correlation_id", "")
