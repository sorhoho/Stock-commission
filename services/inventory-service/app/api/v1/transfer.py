"""Stock Transfer API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import (
    CorrelationId,
    DbSession,
    KafkaProducerDep,
    TenantId,
    get_correlation_id,
    get_current_tenant_id,
    get_db,
    get_kafka_producer,
)
from app.domain.models import StockTransfer, StockTransferCreate, StockTransferUpdate, TransferStatus
from app.domain import services
from app.infrastructure.db.repository import InventoryRepository, StockTransferRepository
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/stockTransfer", tags=["StockTransfer"])


@router.get("/", response_model=list[StockTransfer])
async def list_transfers(
    status: TransferStatus | None = Query(default=None),
    product_id: uuid.UUID | None = Query(default=None),
    source_location_id: uuid.UUID | None = Query(default=None),
    destination_location_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> list[StockTransfer]:
    """List stock transfers with optional filters."""
    repo = StockTransferRepository(db)
    items = await repo.list_with_filters(
        tenant_id=tenant_id,
        status=status,
        product_id=product_id,
        source_location_id=source_location_id,
        destination_location_id=destination_location_id,
        page=page,
        size=size,
    )
    return [StockTransfer.model_validate(item) for item in items]


@router.post("/", response_model=StockTransfer, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    body: StockTransferCreate,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    correlation_id: CorrelationId = Depends(get_correlation_id),
    db: DbSession = Depends(get_db),
    kafka_producer: KafkaProducerDep = Depends(get_kafka_producer),
) -> StockTransfer:
    """Create a new stock transfer."""
    transfer_repo = StockTransferRepository(db)
    transfer = await services.create_transfer(
        data=body,
        tenant_id=tenant_id,
        transfer_repo=transfer_repo,
        kafka_producer=kafka_producer,
        correlation_id=correlation_id,
    )
    return StockTransfer.model_validate(transfer)


@router.post("/{transfer_id}/complete", response_model=StockTransfer)
async def complete_transfer(
    transfer_id: uuid.UUID,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    correlation_id: CorrelationId = Depends(get_correlation_id),
    db: DbSession = Depends(get_db),
    kafka_producer: KafkaProducerDep = Depends(get_kafka_producer),
) -> StockTransfer:
    """Mark a transfer as DELIVERED and update stock-on-hand."""
    transfer_repo = StockTransferRepository(db)
    inventory_repo = InventoryRepository(db)
    transfer = await services.complete_transfer(
        transfer_id=transfer_id,
        tenant_id=tenant_id,
        transfer_repo=transfer_repo,
        inventory_repo=inventory_repo,
        kafka_producer=kafka_producer,
        correlation_id=correlation_id,
    )
    return StockTransfer.model_validate(transfer)


@router.patch("/{transfer_id}", response_model=StockTransfer)
async def update_transfer(
    transfer_id: uuid.UUID,
    body: StockTransferUpdate,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> StockTransfer:
    """Patch transfer status or completed_date."""
    repo = StockTransferRepository(db)
    transfer = await repo.update_status(
        transfer_id=transfer_id,
        tenant_id=tenant_id,
        status=body.status or TransferStatus.PENDING,
        completed_date=body.completed_date,
    )
    if transfer is None:
        raise NotFoundException("StockTransfer", str(transfer_id))
    return StockTransfer.model_validate(transfer)
