"""Goods Receipt API — stock receipt from SAP / supplier."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.config import settings
from app.dependencies import CorrelationId, DbSession, KafkaProducerDep, TenantId
from app.domain.models import GoodsReceipt, GoodsReceiptCreate
from app.domain.services import receive_stock
from app.infrastructure.db.repository import GoodsReceiptRepository, InventoryRepository, ResourceRepository
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/goodsReceipt", tags=["GoodsReceipt"])


@router.post("/", response_model=GoodsReceipt, status_code=status.HTTP_201_CREATED)
async def create_goods_receipt(
    body: GoodsReceiptCreate,
    tenant_id: TenantId,
    correlation_id: CorrelationId,
    db: DbSession,
    kafka_producer: KafkaProducerDep,
) -> GoodsReceipt:
    """Record a stock receipt (GRN) and increase inventory quantity."""
    grn_repo = GoodsReceiptRepository(db)
    inventory_repo = InventoryRepository(db)
    resource_repo = ResourceRepository(db)
    receipt = await receive_stock(
        data=body,
        tenant_id=tenant_id,
        grn_repo=grn_repo,
        inventory_repo=inventory_repo,
        kafka_producer=kafka_producer,
        correlation_id=correlation_id,
        catalog_url=settings.product_catalog_service_url,
        resource_repo=resource_repo,
    )
    return GoodsReceipt.model_validate(receipt)


@router.get("/", response_model=list[GoodsReceipt])
async def list_goods_receipts(
    product_id: uuid.UUID | None = Query(default=None),
    location_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tenant_id: TenantId = ...,
    db: DbSession = ...,
) -> list[GoodsReceipt]:
    """List goods receipts with optional filters."""
    repo = GoodsReceiptRepository(db)
    items = await repo.list_with_filters(
        tenant_id=tenant_id,
        product_id=product_id,
        location_id=location_id,
        page=page,
        size=size,
    )
    return [GoodsReceipt.model_validate(r) for r in items]


@router.get("/{receipt_id}", response_model=GoodsReceipt)
async def get_goods_receipt(
    receipt_id: uuid.UUID,
    tenant_id: TenantId,
    db: DbSession,
) -> GoodsReceipt:
    """Get a goods receipt by ID."""
    repo = GoodsReceiptRepository(db)
    receipt = await repo.get_by_id(receipt_id, tenant_id)
    if receipt is None:
        raise NotFoundException("GoodsReceipt", str(receipt_id))
    return GoodsReceipt.model_validate(receipt)
