"""Repository layer for sell-in-service."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    OrderState,
    ProductOrder,
    ProductOrderCreate,
    ProductOrderItem,
    ProductOrderUpdate,
)
from app.infrastructure.db import models as orm

log = structlog.get_logger(__name__)


def _generate_order_number() -> str:
    """Generate a human-readable order number."""
    import datetime
    import random

    now = datetime.datetime.now(datetime.UTC)
    suffix = random.randint(1000, 9999)
    return f"SLI-{now.strftime('%Y%m%d')}-{suffix}"


def _to_pydantic(db_order: orm.ProductOrderDB) -> ProductOrder:
    items = [
        ProductOrderItem(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        for item in db_order.items
    ]
    return ProductOrder(
        id=db_order.id,
        order_number=db_order.order_number,
        requestor_party_id=db_order.requestor_party_id,
        supplier_party_id=db_order.supplier_party_id,
        items=items,
        state=OrderState(db_order.state),
        total_amount=db_order.total_amount,
        currency=db_order.currency,
        requested_delivery_date=db_order.requested_delivery_date,
        actual_delivery_date=db_order.actual_delivery_date,
        notes=db_order.notes,
        tenant_id=db_order.tenant_id,
        created_at=db_order.created_at,
        updated_at=db_order.updated_at,
    )


class ProductOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: ProductOrderCreate, tenant_id: str) -> ProductOrder:
        total = sum(item.quantity * item.unit_price for item in data.items)
        db_order = orm.ProductOrderDB(
            order_number=_generate_order_number(),
            requestor_party_id=data.requestor_party_id,
            supplier_party_id=data.supplier_party_id,
            state=OrderState.ACKNOWLEDGED,
            total_amount=total,
            currency="USD",
            requested_delivery_date=data.requested_delivery_date,
            notes=data.notes,
            tenant_id=tenant_id,
        )
        self._session.add(db_order)
        await self._session.flush()  # get db_order.id

        for item_data in data.items:
            db_item = orm.ProductOrderItemDB(
                order_id=db_order.id,
                product_id=item_data.product_id,
                product_name=item_data.product_name,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
            )
            self._session.add(db_item)

        await self._session.flush()
        await self._session.refresh(db_order)
        log.info("order.created", order_id=str(db_order.id), order_number=db_order.order_number)
        return _to_pydantic(db_order)

    async def get_by_id(self, order_id: uuid.UUID, tenant_id: str) -> ProductOrder | None:
        result = await self._session.execute(
            select(orm.ProductOrderDB).where(
                orm.ProductOrderDB.id == order_id,
                orm.ProductOrderDB.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_pydantic(row) if row else None

    async def list_with_filters(
        self,
        tenant_id: str,
        requestor_party_id: uuid.UUID | None = None,
        state: OrderState | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        size: int = 20,
    ) -> Sequence[ProductOrder]:
        query = select(orm.ProductOrderDB).where(
            orm.ProductOrderDB.tenant_id == tenant_id
        )
        if requestor_party_id is not None:
            query = query.where(
                orm.ProductOrderDB.requestor_party_id == requestor_party_id
            )
        if state is not None:
            query = query.where(orm.ProductOrderDB.state == state)
        if from_date is not None:
            query = query.where(orm.ProductOrderDB.requested_delivery_date >= from_date)
        if to_date is not None:
            query = query.where(orm.ProductOrderDB.requested_delivery_date <= to_date)
        offset = (page - 1) * size
        query = (
            query.order_by(orm.ProductOrderDB.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        result = await self._session.execute(query)
        return [_to_pydantic(r) for r in result.scalars().all()]

    async def update_state(
        self,
        order_id: uuid.UUID,
        tenant_id: str,
        state: OrderState,
        actual_delivery_date: date | None = None,
    ) -> ProductOrder | None:
        db_order = await self._get_db_by_id(order_id, tenant_id)
        if db_order is None:
            return None
        db_order.state = state
        if actual_delivery_date is not None:
            db_order.actual_delivery_date = actual_delivery_date
        await self._session.flush()
        await self._session.refresh(db_order)
        log.info("order.state_updated", order_id=str(order_id), state=state)
        return _to_pydantic(db_order)

    async def _get_db_by_id(
        self, order_id: uuid.UUID, tenant_id: str
    ) -> orm.ProductOrderDB | None:
        result = await self._session.execute(
            select(orm.ProductOrderDB).where(
                orm.ProductOrderDB.id == order_id,
                orm.ProductOrderDB.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()
