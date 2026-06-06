"""TMF699-aligned Sale Transaction router for sell-out-service."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import (
    get_correlation_id,
    get_kafka_producer,
    get_repo,
    get_tenant_id,
)
from app.domain.models import (
    SaleChannel,
    SaleStatus,
    SaleTransaction,
    SaleTransactionCreate,
    SaleTransactionSummary,
    SaleTransactionUpdate,
)
from app.domain.services import create_sale_transaction, reverse_transaction
from app.infrastructure.db.repository import SaleTransactionRepository
from telco_common.auth.jwt_bearer import require_auth
from telco_common.auth.scopes import Scopes
from telco_common.exceptions import ConflictException, NotFoundException
from telco_common.kafka.producer_factory import KafkaProducer

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/saleTransaction",
    tags=["Sale Transactions"],
)


@router.post(
    "",
    response_model=SaleTransaction,
    status_code=status.HTTP_201_CREATED,
    summary="Create a sell-out transaction (TMF699 POST /saleTransaction)",
    dependencies=[Depends(require_auth([Scopes.SELL_OUT_CREATE]))],
)
async def create_transaction(
    body: SaleTransactionCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    repo: Annotated[SaleTransactionRepository, Depends(get_repo)],
    kafka_producer: Annotated[KafkaProducer, Depends(get_kafka_producer)],
) -> SaleTransaction:
    """Record a new sell-out transaction and publish a domain event."""
    log.info(
        "api.sale_transaction.create",
        dealer_party_id=str(body.dealer_party_id),
        channel=body.channel,
        item_count=len(body.items),
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )
    return await create_sale_transaction(
        data=body,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        repo=repo,
        kafka_producer=kafka_producer,
        stock_query_url=settings.stock_query_service_url,
    )


@router.get(
    "",
    response_model=dict,
    summary="List sale transactions with optional filters (TMF699 GET /saleTransaction)",
    dependencies=[Depends(require_auth([Scopes.SELL_OUT_READ]))],
)
async def list_transactions(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[SaleTransactionRepository, Depends(get_repo)],
    dealer_party_id: uuid.UUID | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    sale_status: SaleStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Paginated list of sell-out transactions with optional filtering."""
    items, total = await repo.list_with_filters(
        tenant_id=tenant_id,
        dealer_party_id=dealer_party_id,
        from_date=from_date,
        to_date=to_date,
        status=sale_status,
        page=page,
        size=size,
    )
    return {
        "items": [t.model_dump(mode="json") for t in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total else 0,
    }


@router.get(
    "/summary",
    response_model=SaleTransactionSummary,
    summary="Get aggregated sell-out summary for a dealer",
    dependencies=[Depends(require_auth([Scopes.SELL_OUT_READ]))],
)
async def get_summary(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[SaleTransactionRepository, Depends(get_repo)],
    dealer_party_id: uuid.UUID = Query(...),
    period: str = Query(..., description="Period in YYYY-MM format, e.g. 2024-03"),
) -> SaleTransactionSummary:
    """Return transaction summary aggregates for a dealer in a given period."""
    return await repo.get_summary(
        dealer_party_id=dealer_party_id,
        period=period,
        tenant_id=tenant_id,
    )


@router.get(
    "/{transaction_id}",
    response_model=SaleTransaction,
    summary="Get a single sell-out transaction by ID (TMF699 GET /saleTransaction/{id})",
    dependencies=[Depends(require_auth([Scopes.SELL_OUT_READ]))],
)
async def get_transaction(
    transaction_id: uuid.UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[SaleTransactionRepository, Depends(get_repo)],
) -> SaleTransaction:
    """Retrieve a specific sell-out transaction by its UUID."""
    txn = await repo.get_by_id(transaction_id, tenant_id)
    if txn is None:
        raise NotFoundException("SaleTransaction", str(transaction_id))
    return txn


@router.patch(
    "/{transaction_id}",
    response_model=SaleTransaction,
    summary="Update or reverse a sale transaction (TMF699 PATCH /saleTransaction/{id})",
    dependencies=[Depends(require_auth([Scopes.SELL_OUT_REVERSE]))],
)
async def update_transaction(
    transaction_id: uuid.UUID,
    body: SaleTransactionUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[SaleTransactionRepository, Depends(get_repo)],
    kafka_producer: Annotated[KafkaProducer, Depends(get_kafka_producer)],
) -> SaleTransaction:
    """
    Update transaction status or initiate a reversal.

    If status=REVERSED is requested, triggers the full reversal workflow
    (validates current status, updates DB, publishes reversal event).
    """
    log.info(
        "api.sale_transaction.patch",
        transaction_id=str(transaction_id),
        requested_status=body.status,
        tenant_id=tenant_id,
    )

    # Reversal path
    if body.status == SaleStatus.REVERSED:
        reason = body.reversal_reason or "No reason provided"
        return await reverse_transaction(
            transaction_id=str(transaction_id),
            reason=reason,
            tenant_id=tenant_id,
            repo=repo,
            kafka_producer=kafka_producer,
        )

    # Generic status update
    if body.status is not None:
        updated = await repo.update_status(transaction_id, body.status, tenant_id)
        if updated is None:
            raise NotFoundException("SaleTransaction", str(transaction_id))
        return updated

    # No-op if nothing to update
    txn = await repo.get_by_id(transaction_id, tenant_id)
    if txn is None:
        raise NotFoundException("SaleTransaction", str(transaction_id))
    return txn
