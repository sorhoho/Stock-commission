"""Stock Reservation API — allocate stock for orders."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.dependencies import CorrelationId, DbSession, KafkaProducerDep, TenantId
from app.domain.models import StockReservation, StockReservationCreate
from app.domain.services import release_reservation, reserve_stock
from app.infrastructure.db.repository import InventoryRepository, StockReservationRepository
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/stockReservation", tags=["StockReservation"])


@router.post("/", response_model=StockReservation, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    body: StockReservationCreate,
    tenant_id: TenantId,
    correlation_id: CorrelationId,
    db: DbSession,
    kafka_producer: KafkaProducerDep,
) -> StockReservation:
    """Reserve stock quantity for an order, validating available stock."""
    inventory_repo = InventoryRepository(db)
    reservation_repo = StockReservationRepository(db)
    reservation = await reserve_stock(
        data=body,
        tenant_id=tenant_id,
        inventory_repo=inventory_repo,
        reservation_repo=reservation_repo,
        kafka_producer=kafka_producer,
        correlation_id=correlation_id,
    )
    return StockReservation.model_validate(reservation)


@router.get("/", response_model=list[StockReservation])
async def list_reservations(
    inventory_id: uuid.UUID,
    tenant_id: TenantId,
    db: DbSession,
) -> list[StockReservation]:
    """List reservations for a given inventory item."""
    repo = StockReservationRepository(db)
    items = await repo.list_for_inventory(inventory_id, tenant_id)
    return [StockReservation.model_validate(r) for r in items]


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation(
    reservation_id: uuid.UUID,
    tenant_id: TenantId,
    db: DbSession,
) -> None:
    """Release (delete) a stock reservation."""
    reservation_repo = StockReservationRepository(db)
    await release_reservation(reservation_id, tenant_id, reservation_repo)
