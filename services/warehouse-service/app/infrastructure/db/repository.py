"""Repository classes for warehouse-service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    BinLocationCreate,
    PickItemStatus,
    PickListCreate,
    PickListStatus,
    PackingSlipCreate,
    PackingSlipStatus,
)
from app.infrastructure.db import models as orm


class BinLocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: BinLocationCreate, tenant_id: str) -> orm.BinLocation:
        bin_loc = orm.BinLocation(
            location_id=data.location_id,
            zone=data.zone,
            aisle=data.aisle,
            rack=data.rack,
            bin=data.bin,
            bin_code=f"{data.zone}-{data.aisle}-{data.rack}-{data.bin}",
            capacity=data.capacity,
            tenant_id=tenant_id,
            created_at=datetime.now(UTC),
        )
        self._session.add(bin_loc)
        await self._session.flush()
        await self._session.refresh(bin_loc)
        return bin_loc

    async def get_by_id(self, bin_id: uuid.UUID, tenant_id: str) -> orm.BinLocation | None:
        result = await self._session.execute(
            select(orm.BinLocation).where(
                orm.BinLocation.id == bin_id,
                orm.BinLocation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        tenant_id: str,
        location_id: uuid.UUID | None = None,
        zone: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> list[orm.BinLocation]:
        query = select(orm.BinLocation).where(orm.BinLocation.tenant_id == tenant_id)
        if location_id is not None:
            query = query.where(orm.BinLocation.location_id == location_id)
        if zone is not None:
            query = query.where(orm.BinLocation.zone == zone)
        offset = (page - 1) * size
        query = query.order_by(orm.BinLocation.bin_code).offset(offset).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().all())


class PickListRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: PickListCreate, tenant_id: str) -> orm.PickList:
        pick_list = orm.PickList(
            reference_order_id=data.reference_order_id,
            order_type=data.order_type,
            status=PickListStatus.PENDING,
            tenant_id=tenant_id,
        )
        self._session.add(pick_list)
        await self._session.flush()
        for item in data.items:
            pi = orm.PickListItem(
                pick_list_id=pick_list.id,
                product_id=item.product_id,
                bin_location_id=item.bin_location_id,
                requested_quantity=item.requested_quantity,
                picked_quantity=0,
                item_status=PickItemStatus.PENDING,
                tenant_id=tenant_id,
            )
            self._session.add(pi)
        await self._session.flush()
        return await self._load(pick_list.id)

    async def get_by_id(self, pick_list_id: uuid.UUID, tenant_id: str) -> orm.PickList | None:
        result = await self._session.execute(
            select(orm.PickList).where(
                orm.PickList.id == pick_list_id,
                orm.PickList.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        tenant_id: str,
        status: PickListStatus | None = None,
        assigned_to: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> list[orm.PickList]:
        query = (
            select(orm.PickList)
            .where(orm.PickList.tenant_id == tenant_id)
        )
        if status is not None:
            query = query.where(orm.PickList.status == status)
        if assigned_to is not None:
            query = query.where(orm.PickList.assigned_to == assigned_to)
        offset = (page - 1) * size
        query = query.order_by(orm.PickList.created_at.desc()).offset(offset).limit(size)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def assign(self, pick_list_id: uuid.UUID, tenant_id: str, assigned_to: str) -> orm.PickList | None:
        pl = await self.get_by_id(pick_list_id, tenant_id)
        if pl is None:
            return None
        pl.assigned_to = assigned_to
        pl.status = PickListStatus.ASSIGNED
        await self._session.flush()
        return await self._load(pick_list_id)

    async def complete(
        self,
        pick_list_id: uuid.UUID,
        tenant_id: str,
        item_picks: dict[uuid.UUID, int],
    ) -> orm.PickList | None:
        pl = await self.get_by_id(pick_list_id, tenant_id)
        if pl is None:
            return None
        for item in pl.items:
            picked = item_picks.get(item.id, 0)
            item.picked_quantity = picked
            if picked == 0:
                item.item_status = PickItemStatus.PENDING
            elif picked < item.requested_quantity:
                item.item_status = PickItemStatus.SHORT_PICK
            else:
                item.item_status = PickItemStatus.PICKED
        pl.status = PickListStatus.COMPLETED
        pl.completed_at = datetime.now(UTC)
        await self._session.flush()
        return await self._load(pick_list_id)

    async def _load(self, pick_list_id: uuid.UUID) -> orm.PickList:
        result = await self._session.execute(
            select(orm.PickList).where(orm.PickList.id == pick_list_id)
        )
        return result.scalar_one()


class PackingSlipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: PackingSlipCreate, tenant_id: str) -> orm.PackingSlip:
        slip_number = f"SLIP-{datetime.now(UTC).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        slip = orm.PackingSlip(
            slip_number=slip_number,
            pick_list_id=data.pick_list_id,
            packed_by=data.packed_by,
            packed_date=datetime.now(UTC),
            status=PackingSlipStatus.PACKED,
            tenant_id=tenant_id,
        )
        self._session.add(slip)
        await self._session.flush()
        for item in data.items:
            si = orm.PackingSlipItem(
                packing_slip_id=slip.id,
                product_id=item.product_id,
                quantity=item.quantity,
                serial_numbers=item.serial_numbers,
                tenant_id=tenant_id,
            )
            self._session.add(si)
        await self._session.flush()
        return await self._load(slip.id)

    async def get_by_id(self, slip_id: uuid.UUID, tenant_id: str) -> orm.PackingSlip | None:
        result = await self._session.execute(
            select(orm.PackingSlip).where(
                orm.PackingSlip.id == slip_id,
                orm.PackingSlip.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def dispatch(
        self,
        slip_id: uuid.UUID,
        tenant_id: str,
        shipping_carrier: str | None,
        tracking_number: str | None,
    ) -> orm.PackingSlip | None:
        slip = await self.get_by_id(slip_id, tenant_id)
        if slip is None:
            return None
        slip.status = PackingSlipStatus.DISPATCHED
        slip.shipping_carrier = shipping_carrier
        slip.tracking_number = tracking_number
        await self._session.flush()
        return await self._load(slip_id)

    async def _load(self, slip_id: uuid.UUID) -> orm.PackingSlip:
        result = await self._session.execute(
            select(orm.PackingSlip).where(orm.PackingSlip.id == slip_id)
        )
        return result.scalar_one()
