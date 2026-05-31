"""Async repository classes for the Inventory service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    InventoryStatus,
    LocationCreate,
    LocationType,
    LocationUpdate,
    ProductInventoryCreate,
    ProductInventoryUpdate,
    StockTransferCreate,
    TransferStatus,
)
from app.infrastructure.db import models as orm


class LocationRepository:
    """Data-access layer for Location entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: LocationCreate, tenant_id: str) -> orm.Location:
        location = orm.Location(
            name=data.name,
            type=data.type,
            address=data.address,
            tenant_id=tenant_id,
        )
        self._session.add(location)
        await self._session.flush()
        await self._session.refresh(location)
        return location

    async def get_by_id(self, location_id: uuid.UUID, tenant_id: str) -> orm.Location | None:
        result = await self._session.execute(
            select(orm.Location).where(
                orm.Location.id == location_id,
                orm.Location.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str,
        type_filter: LocationType | None = None,
    ) -> Sequence[orm.Location]:
        query = select(orm.Location).where(orm.Location.tenant_id == tenant_id)
        if type_filter is not None:
            query = query.where(orm.Location.type == type_filter)
        query = query.order_by(orm.Location.name)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update(
        self, location_id: uuid.UUID, tenant_id: str, data: LocationUpdate
    ) -> orm.Location | None:
        location = await self.get_by_id(location_id, tenant_id)
        if location is None:
            return None
        patch = data.model_dump(exclude_none=True)
        for field, value in patch.items():
            setattr(location, field, value)
        await self._session.flush()
        await self._session.refresh(location)
        return location


class InventoryRepository:
    """Data-access layer for ProductInventory entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, data: ProductInventoryCreate, tenant_id: str
    ) -> orm.ProductInventory:
        item = orm.ProductInventory(
            product_id=data.product_id,
            product_name=data.product_name,
            quantity=data.quantity,
            quantity_uom=data.quantity_uom,
            location_id=data.location_id,
            location_type=data.location_type,
            serial_number_range_start=data.serial_number_range_start,
            serial_number_range_end=data.serial_number_range_end,
            status=data.status,
            tenant_id=tenant_id,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def get_by_id(
        self, inventory_id: uuid.UUID, tenant_id: str
    ) -> orm.ProductInventory | None:
        result = await self._session.execute(
            select(orm.ProductInventory).where(
                orm.ProductInventory.id == inventory_id,
                orm.ProductInventory.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        tenant_id: str,
        location_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        status: InventoryStatus | None = None,
        page: int = 1,
        size: int = 20,
    ) -> Sequence[orm.ProductInventory]:
        query = select(orm.ProductInventory).where(
            orm.ProductInventory.tenant_id == tenant_id
        )
        if location_id is not None:
            query = query.where(orm.ProductInventory.location_id == location_id)
        if product_id is not None:
            query = query.where(orm.ProductInventory.product_id == product_id)
        if status is not None:
            query = query.where(orm.ProductInventory.status == status)
        offset = (page - 1) * size
        query = query.order_by(orm.ProductInventory.product_name).offset(offset).limit(size)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update(
        self,
        inventory_id: uuid.UUID,
        tenant_id: str,
        data: ProductInventoryUpdate,
    ) -> orm.ProductInventory | None:
        item = await self.get_by_id(inventory_id, tenant_id)
        if item is None:
            return None
        patch = data.model_dump(exclude_none=True)
        for field, value in patch.items():
            setattr(item, field, value)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def adjust_quantity(
        self, inventory_id: uuid.UUID, delta: int, tenant_id: str
    ) -> orm.ProductInventory | None:
        """Atomically adjust quantity by *delta* (positive = add, negative = subtract)."""
        # Use an UPDATE … RETURNING pattern for atomicity
        stmt = (
            update(orm.ProductInventory)
            .where(
                orm.ProductInventory.id == inventory_id,
                orm.ProductInventory.tenant_id == tenant_id,
            )
            .values(quantity=orm.ProductInventory.quantity + delta)
            .returning(orm.ProductInventory)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row


class StockTransferRepository:
    """Data-access layer for StockTransfer entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, data: StockTransferCreate, tenant_id: str
    ) -> orm.StockTransfer:
        transfer = orm.StockTransfer(
            transfer_order_number=data.transfer_order_number,
            source_location_id=data.source_location_id,
            destination_location_id=data.destination_location_id,
            product_id=data.product_id,
            quantity=data.quantity,
            status=TransferStatus.PENDING,
            initiated_by=data.initiated_by,
            tenant_id=tenant_id,
            requested_date=data.requested_date,
        )
        self._session.add(transfer)
        await self._session.flush()
        await self._session.refresh(transfer)
        return transfer

    async def get_by_id(
        self, transfer_id: uuid.UUID, tenant_id: str
    ) -> orm.StockTransfer | None:
        result = await self._session.execute(
            select(orm.StockTransfer).where(
                orm.StockTransfer.id == transfer_id,
                orm.StockTransfer.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        tenant_id: str,
        status: TransferStatus | None = None,
        product_id: uuid.UUID | None = None,
        source_location_id: uuid.UUID | None = None,
        destination_location_id: uuid.UUID | None = None,
        page: int = 1,
        size: int = 20,
    ) -> Sequence[orm.StockTransfer]:
        query = select(orm.StockTransfer).where(
            orm.StockTransfer.tenant_id == tenant_id
        )
        if status is not None:
            query = query.where(orm.StockTransfer.status == status)
        if product_id is not None:
            query = query.where(orm.StockTransfer.product_id == product_id)
        if source_location_id is not None:
            query = query.where(
                orm.StockTransfer.source_location_id == source_location_id
            )
        if destination_location_id is not None:
            query = query.where(
                orm.StockTransfer.destination_location_id == destination_location_id
            )
        offset = (page - 1) * size
        query = (
            query.order_by(orm.StockTransfer.requested_date.desc())
            .offset(offset)
            .limit(size)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update_status(
        self,
        transfer_id: uuid.UUID,
        tenant_id: str,
        status: TransferStatus,
        completed_date: datetime | None = None,
    ) -> orm.StockTransfer | None:
        transfer = await self.get_by_id(transfer_id, tenant_id)
        if transfer is None:
            return None
        transfer.status = status
        if completed_date is not None:
            transfer.completed_date = completed_date
        await self._session.flush()
        await self._session.refresh(transfer)
        return transfer
