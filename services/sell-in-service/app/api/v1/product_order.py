"""TMF622 Product Order endpoints for sell-in-service."""

from __future__ import annotations

import uuid
from datetime import date

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession, KafkaProducerDep, TenantId
from app.domain.models import OrderState, ProductOrder, ProductOrderCreate, ProductOrderUpdate
from app.domain.services import cancel_order, complete_order, create_order
from app.infrastructure.db.repository import ProductOrderRepository

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/productOrder", tags=["ProductOrder"])


@router.post("", response_model=ProductOrder, status_code=status.HTTP_201_CREATED)
async def create_product_order(
    body: ProductOrderCreate,
    db: DbSession,
    tenant_id: TenantId,
    kafka_producer: KafkaProducerDep,
) -> ProductOrder:
    repo = ProductOrderRepository(db)
    return await create_order(body, tenant_id, repo, kafka_producer)


@router.get("", response_model=list[ProductOrder])
async def list_product_orders(
    db: DbSession,
    tenant_id: TenantId,
    requestor_party_id: uuid.UUID | None = Query(default=None),
    state: OrderState | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> list[ProductOrder]:
    repo = ProductOrderRepository(db)
    results = await repo.list_with_filters(
        tenant_id=tenant_id,
        requestor_party_id=requestor_party_id,
        state=state,
        from_date=from_date,
        to_date=to_date,
        page=page,
        size=size,
    )
    return list(results)


@router.get("/{order_id}", response_model=ProductOrder)
async def get_product_order(
    order_id: uuid.UUID,
    db: DbSession,
    tenant_id: TenantId,
) -> ProductOrder:
    repo = ProductOrderRepository(db)
    order = await repo.get_by_id(order_id, tenant_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ProductOrder '{order_id}' not found",
        )
    return order


@router.patch("/{order_id}", response_model=ProductOrder)
async def update_product_order(
    order_id: uuid.UUID,
    body: ProductOrderUpdate,
    db: DbSession,
    tenant_id: TenantId,
    kafka_producer: KafkaProducerDep,
) -> ProductOrder:
    """Update order state. Completing an order via PATCH publishes a delivered event."""
    repo = ProductOrderRepository(db)

    if body.state == OrderState.COMPLETED:
        if body.actual_delivery_date is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="actual_delivery_date required when completing an order",
            )
        return await complete_order(
            order_id=order_id,
            actual_delivery_date=body.actual_delivery_date,
            tenant_id=tenant_id,
            repo=repo,
            kafka_producer=kafka_producer,
        )

    if body.state == OrderState.CANCELLED:
        return await cancel_order(
            order_id=order_id,
            tenant_id=tenant_id,
            repo=repo,
            kafka_producer=kafka_producer,
        )

    # Generic patch for other allowed transitions
    order = await repo.get_by_id(order_id, tenant_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ProductOrder '{order_id}' not found",
        )
    if body.state is not None:
        updated = await repo.update_state(
            order_id=order_id,
            tenant_id=tenant_id,
            state=body.state,
            actual_delivery_date=body.actual_delivery_date,
        )
        return updated  # type: ignore[return-value]
    return order


@router.post(
    "/{order_id}/cancel",
    response_model=ProductOrder,
    status_code=status.HTTP_200_OK,
)
async def cancel_product_order(
    order_id: uuid.UUID,
    db: DbSession,
    tenant_id: TenantId,
    kafka_producer: KafkaProducerDep,
) -> ProductOrder:
    repo = ProductOrderRepository(db)
    return await cancel_order(
        order_id=order_id,
        tenant_id=tenant_id,
        repo=repo,
        kafka_producer=kafka_producer,
    )
