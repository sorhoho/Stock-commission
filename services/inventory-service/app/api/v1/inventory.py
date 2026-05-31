"""TMF637 Product Inventory API endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    CorrelationId,
    DbSession,
    KafkaProducerDep,
    TenantId)
from app.domain.models import (
    InventoryStatus,
    ProductInventory,
    ProductInventoryCreate,
    ProductInventoryUpdate)
from app.infrastructure.db.repository import InventoryRepository
from telco_common.exceptions import NotFoundException
from telco_common.kafka.producer_factory import KafkaProducer

router = APIRouter(prefix="/productInventory", tags=["ProductInventory"])


@router.get("/", response_model=list[ProductInventory])
async def list_inventory(
    *,
    location_id: uuid.UUID | None = Query(default=None),
    product_id: uuid.UUID | None = Query(default=None),
    status: InventoryStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tenant_id: TenantId,
    db: DbSession,
) -> list[ProductInventory]:
    """List product inventory items with optional filters."""
    repo = InventoryRepository(db)
    items = await repo.list_with_filters(
        tenant_id=tenant_id,
        location_id=location_id,
        product_id=product_id,
        status=status,
        page=page,
        size=size)
    return [ProductInventory.model_validate(item) for item in items]


@router.get("/{inventory_id}", response_model=ProductInventory)
async def get_inventory_item(
    inventory_id: uuid.UUID,
    tenant_id: TenantId,
    db: DbSession) -> ProductInventory:
    """Get a product inventory item by ID."""
    repo = InventoryRepository(db)
    item = await repo.get_by_id(inventory_id=inventory_id, tenant_id=tenant_id)
    if item is None:
        raise NotFoundException("ProductInventory", str(inventory_id))
    return ProductInventory.model_validate(item)


@router.post("/", response_model=ProductInventory, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    body: ProductInventoryCreate,
    tenant_id: TenantId,
    db: DbSession) -> ProductInventory:
    """Create a new product inventory record."""
    repo = InventoryRepository(db)
    item = await repo.create(data=body, tenant_id=tenant_id)
    return ProductInventory.model_validate(item)


@router.patch("/{inventory_id}", response_model=ProductInventory)
async def update_inventory_item(
    inventory_id: uuid.UUID,
    body: ProductInventoryUpdate,
    tenant_id: TenantId,
    db: DbSession) -> ProductInventory:
    """Partially update a product inventory record."""
    repo = InventoryRepository(db)
    item = await repo.update(
        inventory_id=inventory_id, tenant_id=tenant_id, data=body
    )
    if item is None:
        raise NotFoundException("ProductInventory", str(inventory_id))
    return ProductInventory.model_validate(item)
