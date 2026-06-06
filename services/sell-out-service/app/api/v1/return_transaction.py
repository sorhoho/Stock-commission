"""Return Transaction API — RMA flow for retail sell-out."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_kafka_producer, get_tenant_id
from app.domain.models import ReturnTransaction, ReturnTransactionCreate
from app.domain.services import process_return
from app.infrastructure.db.repository import ReturnRepository
from app.infrastructure.db.session import get_db_session
from telco_common.exceptions import NotFoundException
from telco_common.kafka.producer_factory import KafkaProducer

router = APIRouter(prefix="/returnTransaction", tags=["Return Transaction"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
TenantId = Annotated[str, Depends(get_tenant_id)]
KafkaProducerDep = Annotated[KafkaProducer, Depends(get_kafka_producer)]


@router.post("/", response_model=ReturnTransaction, status_code=status.HTTP_201_CREATED)
async def create_return(
    body: ReturnTransactionCreate, tenant_id: TenantId, db: DbSession
) -> ReturnTransaction:
    """Initiate a return/RMA request."""
    repo = ReturnRepository(db)
    return await repo.create(body, tenant_id)


@router.get("/{return_id}", response_model=ReturnTransaction)
async def get_return(return_id: uuid.UUID, tenant_id: TenantId, db: DbSession) -> ReturnTransaction:
    repo = ReturnRepository(db)
    ret = await repo.get_by_id(return_id, tenant_id)
    if ret is None:
        raise NotFoundException("ReturnTransaction", str(return_id))
    return ret


@router.post("/{return_id}/approve", response_model=ReturnTransaction)
async def approve_return(
    return_id: uuid.UUID, tenant_id: TenantId, db: DbSession, kafka_producer: KafkaProducerDep
) -> ReturnTransaction:
    """Approve a pending return and publish SALES_RETURN_PROCESSED event."""
    repo = ReturnRepository(db)
    return await process_return(return_id, "approve", tenant_id, repo, kafka_producer)


@router.post("/{return_id}/reject", response_model=ReturnTransaction)
async def reject_return(
    return_id: uuid.UUID, tenant_id: TenantId, db: DbSession, kafka_producer: KafkaProducerDep
) -> ReturnTransaction:
    """Reject a pending return."""
    repo = ReturnRepository(db)
    return await process_return(return_id, "reject", tenant_id, repo, kafka_producer)
