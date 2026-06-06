"""Unit tests for warehouse-service API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.models import (
    BinLocation,
    BinLocationCreate,
    OrderType,
    PackingSlip,
    PackingSlipCreate,
    PackingSlipItem,
    PackingSlipItemCreate,
    PackingSlipStatus,
    PickItemStatus,
    PickList,
    PickListCreate,
    PickListItem,
    PickListItemCreate,
    PickListStatus,
)

pytestmark = pytest.mark.asyncio

TENANT = "tenant-wh-001"
LOC_ID = uuid.uuid4()
PROD_ID = uuid.uuid4()


def _make_bin(**overrides) -> BinLocation:
    defaults = dict(
        id=uuid.uuid4(),
        location_id=LOC_ID,
        zone="A",
        aisle="01",
        rack="02",
        bin="03",
        bin_code="A-01-02-03",
        capacity=100,
        tenant_id=TENANT,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return BinLocation(**defaults)


def _make_pick_list(**overrides) -> PickList:
    defaults = dict(
        id=uuid.uuid4(),
        reference_order_id="TXN-REF-001",
        order_type=OrderType.SELL_OUT,
        status=PickListStatus.PENDING,
        assigned_to=None,
        tenant_id=TENANT,
        created_at=datetime.now(UTC),
        completed_at=None,
        items=[
            PickListItem(
                id=uuid.uuid4(),
                pick_list_id=uuid.uuid4(),
                product_id=PROD_ID,
                bin_location_id=None,
                requested_quantity=10,
                picked_quantity=0,
                item_status=PickItemStatus.PENDING,
            )
        ],
    )
    defaults.update(overrides)
    return PickList(**defaults)


def _make_packing_slip(**overrides) -> PackingSlip:
    defaults = dict(
        id=uuid.uuid4(),
        slip_number="SLIP-20260101-ABCD1234",
        pick_list_id=uuid.uuid4(),
        packed_by="packer-bob",
        packed_date=datetime.now(UTC),
        shipping_carrier=None,
        tracking_number=None,
        status=PackingSlipStatus.PACKED,
        tenant_id=TENANT,
        items=[
            PackingSlipItem(
                id=uuid.uuid4(),
                packing_slip_id=uuid.uuid4(),
                product_id=PROD_ID,
                quantity=5,
                serial_numbers=[],
            )
        ],
    )
    defaults.update(overrides)
    return PackingSlip(**defaults)


class TestBinLocationAPI:
    async def test_create_bin_location(self):
        from app.api.v1.bin_location import create_bin_location

        repo = MagicMock()
        bin_loc = _make_bin()
        repo.create = AsyncMock(return_value=MagicMock(**bin_loc.model_dump(), items=None))

        with patch("app.api.v1.bin_location.BinLocationRepository", return_value=repo):
            result = await create_bin_location(
                BinLocationCreate(
                    location_id=LOC_ID, zone="A", aisle="01", rack="02", bin="03"
                ),
                TENANT,
                MagicMock(),
            )
        assert result.bin_code == "A-01-02-03"

    async def test_get_bin_location_not_found(self):
        from app.api.v1.bin_location import get_bin_location
        from telco_common.exceptions import NotFoundException

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)

        with patch("app.api.v1.bin_location.BinLocationRepository", return_value=repo):
            with pytest.raises(NotFoundException):
                await get_bin_location(uuid.uuid4(), TENANT, MagicMock())


class TestPickListAPI:
    async def test_create_pick_list(self):
        from app.api.v1.pick_list import create_pick_list

        pl = _make_pick_list()
        orm_mock = MagicMock(
            **{k: v for k, v in pl.model_dump().items() if k != "items"},
            items=[
                MagicMock(**item.model_dump()) for item in pl.items
            ],
        )
        repo = MagicMock()
        repo.create = AsyncMock(return_value=orm_mock)

        with patch("app.api.v1.pick_list.PickListRepository", return_value=repo):
            result = await create_pick_list(
                PickListCreate(
                    reference_order_id="TXN-REF-001",
                    order_type=OrderType.SELL_OUT,
                    items=[PickListItemCreate(product_id=PROD_ID, requested_quantity=10)],
                ),
                TENANT,
                MagicMock(),
            )
        assert result.status == PickListStatus.PENDING

    async def test_get_pick_list_not_found(self):
        from app.api.v1.pick_list import get_pick_list
        from telco_common.exceptions import NotFoundException

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)

        with patch("app.api.v1.pick_list.PickListRepository", return_value=repo):
            with pytest.raises(NotFoundException):
                await get_pick_list(uuid.uuid4(), TENANT, MagicMock())

    async def test_assign_pick_list_wrong_status_raises(self):
        from app.api.v1.pick_list import assign_pick_list
        from app.domain.models import PickListAssign
        from telco_common.exceptions import UnprocessableEntityException

        pl = _make_pick_list(status=PickListStatus.COMPLETED)
        orm_mock = MagicMock(**{k: v for k, v in pl.model_dump().items() if k != "items"}, items=[])
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=orm_mock)

        with patch("app.api.v1.pick_list.PickListRepository", return_value=repo):
            with pytest.raises(UnprocessableEntityException):
                await assign_pick_list(
                    pl.id, PickListAssign(assigned_to="worker"), TENANT, MagicMock()
                )

    async def test_complete_already_completed_raises(self):
        from app.api.v1.pick_list import complete_pick_list
        from app.domain.models import PickListComplete
        from telco_common.exceptions import UnprocessableEntityException

        pl = _make_pick_list(status=PickListStatus.COMPLETED)
        orm_mock = MagicMock(**{k: v for k, v in pl.model_dump().items() if k != "items"}, items=[])
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=orm_mock)

        with patch("app.api.v1.pick_list.PickListRepository", return_value=repo):
            with pytest.raises(UnprocessableEntityException):
                await complete_pick_list(
                    pl.id, PickListComplete(items=[]), TENANT, MagicMock()
                )


class TestPackingSlipAPI:
    async def test_dispatch_not_packed_raises(self):
        from app.api.v1.packing_slip import dispatch_packing_slip
        from app.domain.models import PackingSlipDispatch
        from telco_common.exceptions import UnprocessableEntityException

        slip = _make_packing_slip(status=PackingSlipStatus.DISPATCHED)
        orm_mock = MagicMock(
            **{k: v for k, v in slip.model_dump().items() if k != "items"}, items=[]
        )
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=orm_mock)

        with patch("app.api.v1.packing_slip.PackingSlipRepository", return_value=repo):
            with pytest.raises(UnprocessableEntityException):
                await dispatch_packing_slip(
                    slip.id,
                    PackingSlipDispatch(shipping_carrier="DHL", tracking_number="T123"),
                    TENANT,
                    MagicMock(),
                )

    async def test_get_packing_slip_not_found(self):
        from app.api.v1.packing_slip import get_packing_slip
        from telco_common.exceptions import NotFoundException

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)

        with patch("app.api.v1.packing_slip.PackingSlipRepository", return_value=repo):
            with pytest.raises(NotFoundException):
                await get_packing_slip(uuid.uuid4(), TENANT, MagicMock())
