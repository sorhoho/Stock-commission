"""Stock Reconciliation API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, status

from app.dependencies import CorrelationId, DbSession, KafkaProducerDep, TenantId
from app.domain.models import (
    ReconciliationStatus,
    StockReconciliation,
    StockReconciliationCreate,
)
from app.domain.services import approve_reconciliation
from app.infrastructure.db.repository import InventoryRepository, ReconciliationRepository
from telco_common.exceptions import NotFoundException, UnprocessableEntityException

router = APIRouter(prefix="/stockReconciliation", tags=["StockReconciliation"])


@router.post("/", response_model=StockReconciliation, status_code=status.HTTP_201_CREATED)
async def create_reconciliation(
    body: StockReconciliationCreate,
    tenant_id: TenantId,
    db: DbSession,
) -> StockReconciliation:
    """Create a new stock reconciliation record in DRAFT status."""
    repo = ReconciliationRepository(db)
    items = [
        {
            "product_id": item.product_id,
            "system_quantity": item.system_quantity,
            "physical_quantity": item.physical_quantity,
        }
        for item in body.items
    ]
    recon = await repo.create(
        data_dict={
            "location_id": body.location_id,
            "reconciliation_date": body.reconciliation_date,
            "counted_by": body.counted_by,
            "notes": body.notes,
        },
        items=items,
        tenant_id=tenant_id,
    )
    return _to_pydantic(recon)


@router.get("/{reconciliation_id}", response_model=StockReconciliation)
async def get_reconciliation(
    reconciliation_id: uuid.UUID,
    tenant_id: TenantId,
    db: DbSession,
) -> StockReconciliation:
    """Get a reconciliation by ID."""
    repo = ReconciliationRepository(db)
    recon = await repo.get_by_id(reconciliation_id, tenant_id)
    if recon is None:
        raise NotFoundException("StockReconciliation", str(reconciliation_id))
    return _to_pydantic(recon)


@router.post("/{reconciliation_id}/submit", response_model=StockReconciliation)
async def submit_reconciliation(
    reconciliation_id: uuid.UUID,
    tenant_id: TenantId,
    db: DbSession,
) -> StockReconciliation:
    """Submit a DRAFT reconciliation for approval."""
    repo = ReconciliationRepository(db)
    recon = await repo.get_by_id(reconciliation_id, tenant_id)
    if recon is None:
        raise NotFoundException("StockReconciliation", str(reconciliation_id))
    if recon.status != ReconciliationStatus.DRAFT:
        raise UnprocessableEntityException(
            f"Only DRAFT reconciliations can be submitted (current={recon.status})"
        )
    updated = await repo.update_status(reconciliation_id, tenant_id, ReconciliationStatus.SUBMITTED)
    return _to_pydantic(updated)


@router.post("/{reconciliation_id}/approve", response_model=StockReconciliation)
async def approve_reconciliation_endpoint(
    reconciliation_id: uuid.UUID,
    approved_by: str = Body(..., embed=True),
    tenant_id: TenantId = ...,
    correlation_id: CorrelationId = ...,
    db: DbSession = ...,
    kafka_producer: KafkaProducerDep = ...,
) -> StockReconciliation:
    """Approve a SUBMITTED reconciliation and apply variance adjustments to stock."""
    recon_repo = ReconciliationRepository(db)
    inventory_repo = InventoryRepository(db)
    updated = await approve_reconciliation(
        reconciliation_id=reconciliation_id,
        approved_by=approved_by,
        tenant_id=tenant_id,
        recon_repo=recon_repo,
        inventory_repo=inventory_repo,
        kafka_producer=kafka_producer,
        correlation_id=correlation_id,
    )
    return _to_pydantic(updated)


def _to_pydantic(orm_obj) -> StockReconciliation:
    from app.domain.models import StockReconciliationItem as ItemModel
    items = [
        ItemModel.model_validate(i) for i in (orm_obj.items or [])
    ]
    recon = StockReconciliation.model_validate(orm_obj)
    recon.items = items
    return recon
