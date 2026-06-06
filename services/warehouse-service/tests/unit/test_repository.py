"""Unit tests for warehouse-service repository layer."""

from __future__ import annotations

import uuid

import pytest

from app.domain.models import (
    BinLocationCreate,
    OrderType,
    PackingSlipCreate,
    PackingSlipItemCreate,
    PackingSlipStatus,
    PickItemStatus,
    PickListAssign,
    PickListComplete,
    PickListCreate,
    PickListItemComplete,
    PickListItemCreate,
    PickListStatus,
)
from app.infrastructure.db.repository import (
    BinLocationRepository,
    PackingSlipRepository,
    PickListRepository,
)

pytestmark = pytest.mark.asyncio


class TestBinLocationRepository:
    async def test_create_and_get(self, db_session, tenant_id, location_id):
        repo = BinLocationRepository(db_session)
        data = BinLocationCreate(
            location_id=location_id, zone="A", aisle="01", rack="02", bin="03"
        )
        created = await repo.create(data, tenant_id)
        assert created.bin_code == "A-01-02-03"
        assert created.tenant_id == tenant_id

        fetched = await repo.get_by_id(created.id, tenant_id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_by_id_wrong_tenant_returns_none(self, db_session, tenant_id, location_id):
        repo = BinLocationRepository(db_session)
        data = BinLocationCreate(
            location_id=location_id, zone="B", aisle="01", rack="01", bin="01"
        )
        created = await repo.create(data, tenant_id)
        result = await repo.get_by_id(created.id, "other-tenant")
        assert result is None

    async def test_list_with_filters_by_zone(self, db_session, tenant_id, location_id):
        repo = BinLocationRepository(db_session)
        for i, zone in enumerate(("A", "A", "B")):
            await repo.create(
                BinLocationCreate(location_id=location_id, zone=zone, aisle="01", rack="01", bin=str(i + 1)),
                tenant_id,
            )
        results = await repo.list_with_filters(tenant_id, zone="A")
        assert len(results) == 2

    async def test_list_empty_other_tenant(self, db_session, tenant_id, location_id):
        repo = BinLocationRepository(db_session)
        await repo.create(
            BinLocationCreate(location_id=location_id, zone="C", aisle="01", rack="01", bin="01"),
            tenant_id,
        )
        results = await repo.list_with_filters("other-tenant")
        assert results == []


class TestPickListRepository:
    def _make_create(self, product_id: uuid.UUID) -> PickListCreate:
        return PickListCreate(
            reference_order_id="TXN-REF-001",
            order_type=OrderType.SELL_OUT,
            items=[PickListItemCreate(product_id=product_id, requested_quantity=10)],
        )

    async def test_create_pick_list(self, db_session, tenant_id, product_id):
        repo = PickListRepository(db_session)
        pl = await repo.create(self._make_create(product_id), tenant_id)
        assert pl.status == PickListStatus.PENDING
        assert len(pl.items) == 1
        assert pl.items[0].item_status == PickItemStatus.PENDING

    async def test_assign_pick_list(self, db_session, tenant_id, product_id):
        repo = PickListRepository(db_session)
        pl = await repo.create(self._make_create(product_id), tenant_id)
        updated = await repo.assign(pl.id, tenant_id, "worker-jane")
        assert updated.status == PickListStatus.ASSIGNED
        assert updated.assigned_to == "worker-jane"

    async def test_complete_pick_list_full(self, db_session, tenant_id, product_id):
        repo = PickListRepository(db_session)
        pl = await repo.create(self._make_create(product_id), tenant_id)
        item = pl.items[0]
        updated = await repo.complete(pl.id, tenant_id, {item.id: 10})
        assert updated.status == PickListStatus.COMPLETED
        assert updated.items[0].picked_quantity == 10
        assert updated.items[0].item_status == PickItemStatus.PICKED

    async def test_complete_pick_list_short(self, db_session, tenant_id, product_id):
        repo = PickListRepository(db_session)
        pl = await repo.create(self._make_create(product_id), tenant_id)
        item = pl.items[0]
        updated = await repo.complete(pl.id, tenant_id, {item.id: 3})
        assert updated.items[0].item_status == PickItemStatus.SHORT_PICK

    async def test_get_by_id_wrong_tenant(self, db_session, tenant_id, product_id):
        repo = PickListRepository(db_session)
        pl = await repo.create(self._make_create(product_id), tenant_id)
        result = await repo.get_by_id(pl.id, "other-tenant")
        assert result is None

    async def test_list_with_status_filter(self, db_session, tenant_id, product_id):
        repo = PickListRepository(db_session)
        pl = await repo.create(self._make_create(product_id), tenant_id)
        pending_lists = await repo.list_with_filters(tenant_id, status=PickListStatus.PENDING)
        assert any(p.id == pl.id for p in pending_lists)
        completed_lists = await repo.list_with_filters(tenant_id, status=PickListStatus.COMPLETED)
        assert not any(p.id == pl.id for p in completed_lists)


class TestPackingSlipRepository:
    async def test_create_packing_slip(self, db_session, tenant_id, product_id, location_id):
        pick_repo = PickListRepository(db_session)
        pl = await pick_repo.create(
            PickListCreate(
                reference_order_id="REF-002",
                order_type=OrderType.REPLENISHMENT,
                items=[PickListItemCreate(product_id=product_id, requested_quantity=5)],
            ),
            tenant_id,
        )
        slip_repo = PackingSlipRepository(db_session)
        slip = await slip_repo.create(
            PackingSlipCreate(
                pick_list_id=pl.id,
                packed_by="packer-bob",
                items=[PackingSlipItemCreate(product_id=product_id, quantity=5)],
            ),
            tenant_id,
        )
        assert slip.status == PackingSlipStatus.PACKED
        assert slip.packed_by == "packer-bob"
        assert len(slip.items) == 1

    async def test_dispatch_packing_slip(self, db_session, tenant_id, product_id, location_id):
        pick_repo = PickListRepository(db_session)
        pl = await pick_repo.create(
            PickListCreate(
                reference_order_id="REF-003",
                order_type=OrderType.SELL_OUT,
                items=[PickListItemCreate(product_id=product_id, requested_quantity=2)],
            ),
            tenant_id,
        )
        slip_repo = PackingSlipRepository(db_session)
        slip = await slip_repo.create(
            PackingSlipCreate(
                pick_list_id=pl.id,
                packed_by="packer-alice",
                items=[PackingSlipItemCreate(product_id=product_id, quantity=2)],
            ),
            tenant_id,
        )
        dispatched = await slip_repo.dispatch(slip.id, tenant_id, "DHL", "TRACK-123")
        assert dispatched.status == PackingSlipStatus.DISPATCHED
        assert dispatched.shipping_carrier == "DHL"
        assert dispatched.tracking_number == "TRACK-123"
