"""Stock Adjustment API — manual stock deductions and corrections."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.dependencies import CorrelationId, DbSession, KafkaProducerDep, TenantId
from app.domain.models import ProductInventory, StockAdjustmentCreate
from app.domain.services import adjust_stock
from app.infrastructure.db.repository import InventoryRepository

router = APIRouter(prefix="/stockAdjustment", tags=["StockAdjustment"])


@router.post("/", response_model=ProductInventory, status_code=status.HTTP_200_OK)
async def create_stock_adjustment(
    body: StockAdjustmentCreate,
    tenant_id: TenantId,
    correlation_id: CorrelationId,
    db: DbSession,
    kafka_producer: KafkaProducerDep,
) -> ProductInventory:
    """Adjust inventory quantity (positive = add, negative = deduct/write-off).

    Publishes INVENTORY_STOCK_ADJUSTED event on success.
    """
    inventory_repo = InventoryRepository(db)
    item = await adjust_stock(
        inventory_id=body.inventory_id,
        delta=body.delta,
        reason=body.reason,
        adjusted_by=body.adjusted_by,
        tenant_id=tenant_id,
        inventory_repo=inventory_repo,
        kafka_producer=kafka_producer,
        correlation_id=correlation_id,
    )
    return ProductInventory.model_validate(item)
