"""Async repository classes for the Inventory service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import (
    GoodsReceiptCreate,
    InventoryStatus,
    LocationCreate,
    LocationType,
    LocationUpdate,
    ProductInventoryCreate,
    ProductInventoryUpdate,
    ReconciliationStatus,
    ResourceCreate,
    ResourceStatusType,
    StockReservationCreate,
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


class GoodsReceiptRepository:
    """Data-access layer for GoodsReceipt entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: GoodsReceiptCreate, tenant_id: str) -> orm.GoodsReceipt:
        receipt = orm.GoodsReceipt(
            grn_number=data.grn_number,
            supplier_reference=data.supplier_reference,
            product_id=data.product_id,
            location_id=data.location_id,
            quantity_received=data.quantity_received,
            unit_cost=data.unit_cost,
            received_by=data.received_by,
            received_date=data.received_date,
            tenant_id=tenant_id,
        )
        self._session.add(receipt)
        await self._session.flush()
        await self._session.refresh(receipt)
        return receipt

    async def get_by_id(self, receipt_id: uuid.UUID, tenant_id: str) -> orm.GoodsReceipt | None:
        result = await self._session.execute(
            select(orm.GoodsReceipt).where(
                orm.GoodsReceipt.id == receipt_id,
                orm.GoodsReceipt.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        tenant_id: str,
        product_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        page: int = 1,
        size: int = 20,
    ) -> list[orm.GoodsReceipt]:
        query = select(orm.GoodsReceipt).where(orm.GoodsReceipt.tenant_id == tenant_id)
        if product_id is not None:
            query = query.where(orm.GoodsReceipt.product_id == product_id)
        if location_id is not None:
            query = query.where(orm.GoodsReceipt.location_id == location_id)
        offset = (page - 1) * size
        query = query.order_by(orm.GoodsReceipt.received_date.desc()).offset(offset).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().all())


class StockReservationRepository:
    """Data-access layer for StockReservation entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: StockReservationCreate, tenant_id: str) -> orm.StockReservation:
        reservation = orm.StockReservation(
            inventory_id=data.inventory_id,
            reserved_quantity=data.reserved_quantity,
            reserved_by=data.reserved_by,
            reservation_expiry=data.reservation_expiry,
            reason=data.reason,
            tenant_id=tenant_id,
        )
        self._session.add(reservation)
        await self._session.flush()
        await self._session.refresh(reservation)
        return reservation

    async def get_by_id(self, reservation_id: uuid.UUID, tenant_id: str) -> orm.StockReservation | None:
        result = await self._session.execute(
            select(orm.StockReservation).where(
                orm.StockReservation.id == reservation_id,
                orm.StockReservation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_inventory(
        self, inventory_id: uuid.UUID, tenant_id: str
    ) -> list[orm.StockReservation]:
        result = await self._session.execute(
            select(orm.StockReservation).where(
                orm.StockReservation.inventory_id == inventory_id,
                orm.StockReservation.tenant_id == tenant_id,
            )
        )
        return list(result.scalars().all())

    async def total_reserved(self, inventory_id: uuid.UUID, tenant_id: str) -> int:
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.coalesce(func.sum(orm.StockReservation.reserved_quantity), 0)).where(
                orm.StockReservation.inventory_id == inventory_id,
                orm.StockReservation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one()

    async def delete(self, reservation_id: uuid.UUID, tenant_id: str) -> bool:
        result = await self._session.execute(
            delete(orm.StockReservation).where(
                orm.StockReservation.id == reservation_id,
                orm.StockReservation.tenant_id == tenant_id,
            )
        )
        return result.rowcount > 0


class ResourceRepository:
    """Data-access layer for TMF 639 Resource entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: ResourceCreate, tenant_id: str) -> orm.Resource:
        resource = orm.Resource(
            resource_name=data.resource_name,
            resource_type=data.resource_type,
            product_id=data.product_id,
            inventory_id=data.inventory_id,
            location_id=data.location_id,
            status=data.status,
            batch_reference=data.batch_reference,
            supplier_reference=data.supplier_reference,
            tenant_id=tenant_id,
        )
        self._session.add(resource)
        await self._session.flush()
        for char in data.characteristics:
            rc = orm.ResourceCharacteristic(
                resource_id=resource.id,
                name=char.name,
                value=char.value,
                tenant_id=tenant_id,
            )
            self._session.add(rc)
        await self._session.flush()
        result = await self._session.execute(
            select(orm.Resource)
            .options(selectinload(orm.Resource.characteristics))
            .where(orm.Resource.id == resource.id)
        )
        return result.scalar_one()

    async def get_by_id(self, resource_id: uuid.UUID, tenant_id: str) -> orm.Resource | None:
        result = await self._session.execute(
            select(orm.Resource)
            .options(selectinload(orm.Resource.characteristics))
            .execution_options(populate_existing=True)
            .where(
                orm.Resource.id == resource_id,
                orm.Resource.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        tenant_id: str,
        product_id: uuid.UUID | None = None,
        status: ResourceStatusType | None = None,
        inventory_id: uuid.UUID | None = None,
        characteristic_name: str | None = None,
        characteristic_value: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> list[orm.Resource]:
        query = (
            select(orm.Resource)
            .options(selectinload(orm.Resource.characteristics))
            .where(orm.Resource.tenant_id == tenant_id)
        )
        if product_id is not None:
            query = query.where(orm.Resource.product_id == product_id)
        if status is not None:
            query = query.where(orm.Resource.status == status)
        if inventory_id is not None:
            query = query.where(orm.Resource.inventory_id == inventory_id)
        if characteristic_name is not None and characteristic_value is not None:
            query = query.join(
                orm.ResourceCharacteristic,
                orm.ResourceCharacteristic.resource_id == orm.Resource.id,
            ).where(
                orm.ResourceCharacteristic.name == characteristic_name,
                orm.ResourceCharacteristic.value == characteristic_value,
                orm.ResourceCharacteristic.tenant_id == tenant_id,
            )
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def update_status(
        self,
        resource_id: uuid.UUID,
        tenant_id: str,
        status: ResourceStatusType,
        allocated_to: str | None = None,
    ) -> orm.Resource | None:
        resource = await self.get_by_id(resource_id, tenant_id)
        if resource is None:
            return None
        resource.status = status
        if allocated_to is not None:
            resource.allocated_to = allocated_to
        await self._session.flush()
        await self._session.refresh(resource)
        return resource


class ReconciliationRepository:
    """Data-access layer for StockReconciliation entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        data_dict: dict,
        items: list[dict],
        tenant_id: str,
    ) -> orm.StockReconciliation:
        recon = orm.StockReconciliation(
            location_id=data_dict["location_id"],
            reconciliation_date=data_dict["reconciliation_date"],
            status=ReconciliationStatus.DRAFT,
            counted_by=data_dict["counted_by"],
            notes=data_dict.get("notes"),
            tenant_id=tenant_id,
        )
        self._session.add(recon)
        await self._session.flush()
        for item in items:
            ri = orm.StockReconciliationItem(
                reconciliation_id=recon.id,
                product_id=item["product_id"],
                system_quantity=item["system_quantity"],
                physical_quantity=item["physical_quantity"],
                variance=item["physical_quantity"] - item["system_quantity"],
                tenant_id=tenant_id,
            )
            self._session.add(ri)
        await self._session.flush()
        result = await self._session.execute(
            select(orm.StockReconciliation)
            .options(selectinload(orm.StockReconciliation.items))
            .where(orm.StockReconciliation.id == recon.id)
        )
        return result.scalar_one()

    async def get_by_id(
        self, reconciliation_id: uuid.UUID, tenant_id: str
    ) -> orm.StockReconciliation | None:
        result = await self._session.execute(
            select(orm.StockReconciliation)
            .options(selectinload(orm.StockReconciliation.items))
            .where(
                orm.StockReconciliation.id == reconciliation_id,
                orm.StockReconciliation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        reconciliation_id: uuid.UUID,
        tenant_id: str,
        status: ReconciliationStatus,
        approved_by: str | None = None,
    ) -> orm.StockReconciliation | None:
        recon = await self.get_by_id(reconciliation_id, tenant_id)
        if recon is None:
            return None
        recon.status = status
        if approved_by is not None:
            recon.approved_by = approved_by
        await self._session.flush()
        result = await self._session.execute(
            select(orm.StockReconciliation)
            .options(selectinload(orm.StockReconciliation.items))
            .where(orm.StockReconciliation.id == reconciliation_id)
        )
        return result.scalar_one()
