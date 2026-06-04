"""Unit tests for inventory-service API handlers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.models import (
    InventoryStatus,
    Location,
    LocationCreate,
    LocationType,
    ProductInventory,
    ProductInventoryCreate,
    ProductInventoryUpdate,
    StockTransfer,
    StockTransferCreate,
    TransferStatus,
)
from telco_common.exceptions import NotFoundException

pytestmark = pytest.mark.asyncio

TENANT = "tenant-test-001"


def _make_inventory(**overrides) -> ProductInventory:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        href="/api/v1/productInventory/" + str(uuid.uuid4()),
        product_id=uuid.uuid4(),
        product_name="SIM Card",
        quantity=100,
        quantity_uom="EACH",
        location_id=uuid.uuid4(),
        location_type=LocationType.WAREHOUSE,
        status=InventoryStatus.AVAILABLE,
        tenant_id=TENANT,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return ProductInventory(**defaults)


def _make_location(**overrides) -> Location:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        name="Warehouse A",
        type=LocationType.WAREHOUSE,
        tenant_id=TENANT,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Location(**defaults)


def _make_transfer(**overrides) -> StockTransfer:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        transfer_order_number="TRF-20260101-0001",
        source_location_id=uuid.uuid4(),
        destination_location_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        quantity=10,
        status=TransferStatus.PENDING,
        initiated_by="admin",
        tenant_id=TENANT,
        requested_date=now,
    )
    defaults.update(overrides)
    return StockTransfer(**defaults)


# ── inventory API ─────────────────────────────────────────────────────────────


async def test_list_inventory_empty():
    from app.api.v1.inventory import list_inventory

    mock_db = AsyncMock()

    with patch("app.api.v1.inventory.InventoryRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = []
        MockRepo.return_value = instance

        result = await list_inventory(
            location_id=None, product_id=None, status=None,
            page=1, size=20, tenant_id=TENANT, db=mock_db,
        )

    assert result == []
    instance.list_with_filters.assert_awaited_once_with(
        tenant_id=TENANT, location_id=None, product_id=None,
        status=None, page=1, size=20,
    )


async def test_list_inventory_with_filters():
    from app.api.v1.inventory import list_inventory

    inv = _make_inventory()
    mock_db = AsyncMock()
    loc_id = uuid.uuid4()

    with patch("app.api.v1.inventory.InventoryRepository") as MockRepo:
        instance = AsyncMock()
        orm_mock = AsyncMock()
        # model_validate called on the ORM mock; return a real ProductInventory
        with patch("app.api.v1.inventory.ProductInventory") as MockModel:
            MockModel.model_validate.return_value = inv
            instance.list_with_filters.return_value = [orm_mock]
            MockRepo.return_value = instance

            result = await list_inventory(
                location_id=loc_id, product_id=None, status=InventoryStatus.AVAILABLE,
                page=1, size=20, tenant_id=TENANT, db=mock_db,
            )

    assert len(result) == 1
    kwargs = instance.list_with_filters.call_args.kwargs
    assert kwargs["location_id"] == loc_id
    assert kwargs["status"] == InventoryStatus.AVAILABLE


async def test_get_inventory_item_found():
    from app.api.v1.inventory import get_inventory_item

    inv = _make_inventory()
    mock_db = AsyncMock()

    with patch("app.api.v1.inventory.InventoryRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = inv
        MockRepo.return_value = instance

        with patch("app.api.v1.inventory.ProductInventory") as MockModel:
            MockModel.model_validate.return_value = inv

            result = await get_inventory_item(
                inventory_id=inv.id, tenant_id=TENANT, db=mock_db,
            )

    assert result.id == inv.id


async def test_get_inventory_item_not_found():
    from app.api.v1.inventory import get_inventory_item

    mock_db = AsyncMock()

    with patch("app.api.v1.inventory.InventoryRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_inventory_item(
                inventory_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db,
            )


async def test_create_inventory_item():
    from app.api.v1.inventory import create_inventory_item

    inv = _make_inventory()
    mock_db = AsyncMock()
    body = ProductInventoryCreate(
        product_id=inv.product_id,
        product_name="SIM Card",
        quantity=100,
        location_id=inv.location_id,
        location_type=LocationType.WAREHOUSE,
    )

    with patch("app.api.v1.inventory.InventoryRepository") as MockRepo:
        instance = AsyncMock()
        instance.create.return_value = inv
        MockRepo.return_value = instance

        with patch("app.api.v1.inventory.ProductInventory") as MockModel:
            MockModel.model_validate.return_value = inv

            result = await create_inventory_item(
                body=body, tenant_id=TENANT, db=mock_db,
            )

    assert result.product_name == "SIM Card"
    instance.create.assert_awaited_once_with(data=body, tenant_id=TENANT)


async def test_update_inventory_item_found():
    from app.api.v1.inventory import update_inventory_item

    inv = _make_inventory(quantity=50)
    mock_db = AsyncMock()
    body = ProductInventoryUpdate(quantity=50)

    with patch("app.api.v1.inventory.InventoryRepository") as MockRepo:
        instance = AsyncMock()
        instance.update.return_value = inv
        MockRepo.return_value = instance

        with patch("app.api.v1.inventory.ProductInventory") as MockModel:
            MockModel.model_validate.return_value = inv

            result = await update_inventory_item(
                inventory_id=inv.id, body=body, tenant_id=TENANT, db=mock_db,
            )

    assert result.quantity == 50


async def test_update_inventory_item_not_found():
    from app.api.v1.inventory import update_inventory_item

    mock_db = AsyncMock()
    body = ProductInventoryUpdate(quantity=10)

    with patch("app.api.v1.inventory.InventoryRepository") as MockRepo:
        instance = AsyncMock()
        instance.update.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await update_inventory_item(
                inventory_id=uuid.uuid4(), body=body, tenant_id=TENANT, db=mock_db,
            )


# ── location API ──────────────────────────────────────────────────────────────


async def test_list_locations_empty():
    from app.api.v1.location import list_locations

    mock_db = AsyncMock()

    with patch("app.api.v1.location.LocationRepository") as MockRepo:
        instance = AsyncMock()
        instance.list.return_value = []
        MockRepo.return_value = instance

        result = await list_locations(type=None, tenant_id=TENANT, db=mock_db)

    assert result == []


async def test_get_location_found():
    from app.api.v1.location import get_location

    loc = _make_location()
    mock_db = AsyncMock()

    with patch("app.api.v1.location.LocationRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = loc
        MockRepo.return_value = instance

        with patch("app.api.v1.location.Location") as MockModel:
            MockModel.model_validate.return_value = loc

            result = await get_location(location_id=loc.id, tenant_id=TENANT, db=mock_db)

    assert result.id == loc.id


async def test_get_location_not_found():
    from app.api.v1.location import get_location

    mock_db = AsyncMock()

    with patch("app.api.v1.location.LocationRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_location(location_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db)


async def test_create_location():
    from app.api.v1.location import create_location

    loc = _make_location(name="New Warehouse")
    body = LocationCreate(name="New Warehouse", type=LocationType.WAREHOUSE)
    mock_db = AsyncMock()

    with patch("app.api.v1.location.LocationRepository") as MockRepo:
        instance = AsyncMock()
        instance.create.return_value = loc
        MockRepo.return_value = instance

        with patch("app.api.v1.location.Location") as MockModel:
            MockModel.model_validate.return_value = loc

            result = await create_location(body=body, tenant_id=TENANT, db=mock_db)

    assert result.name == "New Warehouse"


# ── transfer API ──────────────────────────────────────────────────────────────


async def test_list_transfers_empty():
    from app.api.v1.transfer import list_transfers

    mock_db = AsyncMock()

    with patch("app.api.v1.transfer.StockTransferRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = []
        MockRepo.return_value = instance

        result = await list_transfers(
            status=None, product_id=None,
            source_location_id=None, destination_location_id=None,
            page=1, size=20, tenant_id=TENANT, db=mock_db,
        )

    assert result == []


async def test_create_transfer():
    from app.api.v1.transfer import create_transfer

    txr = _make_transfer()
    now = datetime.now(UTC)
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    corr = "corr-123"

    body = StockTransferCreate(
        transfer_order_number="TRF-20260101-0001",
        source_location_id=txr.source_location_id,
        destination_location_id=txr.destination_location_id,
        product_id=txr.product_id,
        quantity=10,
        initiated_by="admin",
        requested_date=now,
    )

    with patch("app.api.v1.transfer.services") as mock_svc_module:
        mock_svc_module.create_transfer = AsyncMock(return_value=txr)

        with patch("app.api.v1.transfer.StockTransfer") as MockModel:
            MockModel.model_validate.return_value = txr

            result = await create_transfer(
                body=body, tenant_id=TENANT, correlation_id=corr,
                db=mock_db, kafka_producer=mock_kafka,
            )

    assert result.id == txr.id
