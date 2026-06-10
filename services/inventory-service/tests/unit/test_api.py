"""Unit tests for inventory-service API handlers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.models import (
    GoodsReceipt,
    GoodsReceiptCreate,
    InventoryStatus,
    Location,
    LocationCreate,
    LocationType,
    ProductInventory,
    ProductInventoryCreate,
    ProductInventoryUpdate,
    ReconciliationStatus,
    Resource,
    ResourceCharacteristic,
    ResourceCreate,
    ResourceStatusType,
    ResourceType,
    StockAdjustmentCreate,
    StockReconciliation,
    StockReconciliationCreate,
    StockReconciliationItemCreate,
    StockReservation,
    StockReservationCreate,
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


# ── helpers for new models ────────────────────────────────────────────────────


def _make_grn(**overrides) -> GoodsReceipt:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        grn_number="GRN-001",
        supplier_reference="SAP-PO-001",
        product_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        quantity_received=50,
        unit_cost=10.0,
        received_by="admin",
        received_date=now,
        tenant_id=TENANT,
        created_at=now,
    )
    defaults.update(overrides)
    return GoodsReceipt(**defaults)


def _make_reservation(**overrides) -> StockReservation:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        inventory_id=uuid.uuid4(),
        reserved_quantity=10,
        reserved_by="order-svc",
        reservation_expiry=now,
        tenant_id=TENANT,
        created_at=now,
    )
    defaults.update(overrides)
    return StockReservation(**defaults)


def _make_resource(**overrides) -> Resource:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        resource_name="Samsung Galaxy A15",
        resource_type=ResourceType.HANDSET,
        product_id=uuid.uuid4(),
        status=ResourceStatusType.AVAILABLE,
        tenant_id=TENANT,
        created_at=now,
        characteristics=[],
    )
    defaults.update(overrides)
    return Resource(**defaults)


def _make_reconciliation(**overrides) -> StockReconciliation:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        reconciliation_date=now,
        status=ReconciliationStatus.DRAFT,
        counted_by="manager",
        tenant_id=TENANT,
        created_at=now,
        items=[],
    )
    defaults.update(overrides)
    return StockReconciliation(**defaults)


# ── goods_receipt API ─────────────────────────────────────────────────────────


async def test_create_goods_receipt_delegates_to_service():
    from app.api.v1.goods_receipt import create_goods_receipt

    grn = _make_grn()
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = GoodsReceiptCreate(
        grn_number="GRN-001",
        product_id=grn.product_id,
        location_id=grn.location_id,
        quantity_received=50,
        received_by="admin",
        received_date=grn.received_date,
    )

    with patch("app.api.v1.goods_receipt.receive_stock", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = grn
        with patch("app.api.v1.goods_receipt.GoodsReceipt") as MockModel:
            MockModel.model_validate.return_value = grn
            result = await create_goods_receipt(
                body=body, tenant_id=TENANT, correlation_id="corr-1",
                db=mock_db, kafka_producer=mock_kafka,
            )

    assert result.grn_number == "GRN-001"
    mock_svc.assert_awaited_once()


async def test_list_goods_receipts_empty():
    from app.api.v1.goods_receipt import list_goods_receipts

    mock_db = AsyncMock()

    with patch("app.api.v1.goods_receipt.GoodsReceiptRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = []
        MockRepo.return_value = instance

        result = await list_goods_receipts(
            product_id=None, location_id=None,
            page=1, size=20, tenant_id=TENANT, db=mock_db,
        )

    assert result == []


async def test_get_goods_receipt_found():
    from app.api.v1.goods_receipt import get_goods_receipt

    grn = _make_grn()
    mock_db = AsyncMock()

    with patch("app.api.v1.goods_receipt.GoodsReceiptRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = grn
        MockRepo.return_value = instance

        with patch("app.api.v1.goods_receipt.GoodsReceipt") as MockModel:
            MockModel.model_validate.return_value = grn
            result = await get_goods_receipt(receipt_id=grn.id, tenant_id=TENANT, db=mock_db)

    assert result.id == grn.id


async def test_get_goods_receipt_not_found():
    from app.api.v1.goods_receipt import get_goods_receipt

    mock_db = AsyncMock()

    with patch("app.api.v1.goods_receipt.GoodsReceiptRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_goods_receipt(receipt_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db)


# ── stock_reservation API ─────────────────────────────────────────────────────


async def test_create_reservation_delegates_to_service():
    from app.api.v1.stock_reservation import create_reservation

    res = _make_reservation()
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = StockReservationCreate(
        inventory_id=res.inventory_id,
        reserved_quantity=10,
        reserved_by="order-svc",
        reservation_expiry=res.reservation_expiry,
    )

    with patch("app.api.v1.stock_reservation.reserve_stock", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = res
        with patch("app.api.v1.stock_reservation.StockReservation") as MockModel:
            MockModel.model_validate.return_value = res
            result = await create_reservation(
                body=body, tenant_id=TENANT, correlation_id="corr-1",
                db=mock_db, kafka_producer=mock_kafka,
            )

    assert result.id == res.id
    mock_svc.assert_awaited_once()


async def test_list_reservations():
    from app.api.v1.stock_reservation import list_reservations

    res = _make_reservation()
    mock_db = AsyncMock()

    with patch("app.api.v1.stock_reservation.StockReservationRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_for_inventory.return_value = [res]
        MockRepo.return_value = instance

        with patch("app.api.v1.stock_reservation.StockReservation") as MockModel:
            MockModel.model_validate.return_value = res
            result = await list_reservations(
                inventory_id=res.inventory_id, tenant_id=TENANT, db=mock_db,
            )

    assert len(result) == 1


async def test_delete_reservation_found():
    from app.api.v1.stock_reservation import delete_reservation

    mock_db = AsyncMock()

    with patch("app.api.v1.stock_reservation.release_reservation", new_callable=AsyncMock) as mock_svc:
        result = await delete_reservation(
            reservation_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db,
        )

    assert result is None
    mock_svc.assert_awaited_once()


# ── stock_adjustment API ──────────────────────────────────────────────────────


async def test_create_stock_adjustment_delegates_to_service():
    from app.api.v1.stock_adjustment import create_stock_adjustment

    inv = _make_inventory(quantity=90)
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = StockAdjustmentCreate(
        inventory_id=inv.id,
        delta=-10,
        reason="write-off",
        adjusted_by="admin",
    )

    with patch("app.api.v1.stock_adjustment.adjust_stock", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = inv
        with patch("app.api.v1.stock_adjustment.ProductInventory") as MockModel:
            MockModel.model_validate.return_value = inv
            result = await create_stock_adjustment(
                body=body, tenant_id=TENANT, correlation_id="corr-1",
                db=mock_db, kafka_producer=mock_kafka,
            )

    assert result.id == inv.id
    mock_svc.assert_awaited_once()
    kwargs = mock_svc.call_args.kwargs
    assert kwargs["delta"] == -10
    assert kwargs["reason"] == "write-off"


# ── resource_inventory API ────────────────────────────────────────────────────


async def test_register_resources():
    from app.api.v1.resource_inventory import register_resources

    r = _make_resource()
    mock_db = AsyncMock()
    body = [ResourceCreate(
        resource_name="Samsung A15",
        resource_type=ResourceType.HANDSET,
        product_id=r.product_id,
        characteristics=[],
    )]

    with patch("app.api.v1.resource_inventory.ResourceRepository") as MockRepo:
        instance = AsyncMock()
        instance.create.return_value = r
        MockRepo.return_value = instance

        with patch("app.api.v1.resource_inventory.Resource") as MockModel:
            MockModel.model_validate.return_value = r
            result = await register_resources(body=body, tenant_id=TENANT, db=mock_db)

    assert len(result) == 1
    instance.create.assert_awaited_once()


async def test_list_resources_empty():
    from app.api.v1.resource_inventory import list_resources

    mock_db = AsyncMock()

    with patch("app.api.v1.resource_inventory.ResourceRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = []
        MockRepo.return_value = instance

        result = await list_resources(
            product_id=None, status=None, inventory_id=None,
            characteristic_name=None, characteristic_value=None,
            page=1, size=20, tenant_id=TENANT, db=mock_db,
        )

    assert result == []


async def test_get_resource_found():
    from app.api.v1.resource_inventory import get_resource

    r = _make_resource()
    mock_db = AsyncMock()

    with patch("app.api.v1.resource_inventory.ResourceRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = r
        MockRepo.return_value = instance

        with patch("app.api.v1.resource_inventory.Resource") as MockModel:
            MockModel.model_validate.return_value = r
            result = await get_resource(resource_id=r.id, tenant_id=TENANT, db=mock_db)

    assert result.id == r.id


async def test_get_resource_not_found():
    from app.api.v1.resource_inventory import get_resource

    mock_db = AsyncMock()

    with patch("app.api.v1.resource_inventory.ResourceRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_resource(resource_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db)


# ── reconciliation API ────────────────────────────────────────────────────────


async def test_create_reconciliation():
    from app.api.v1.reconciliation import create_reconciliation

    recon = _make_reconciliation()
    mock_db = AsyncMock()
    body = StockReconciliationCreate(
        location_id=recon.location_id,
        reconciliation_date=recon.reconciliation_date,
        counted_by="manager",
        items=[StockReconciliationItemCreate(
            product_id=uuid.uuid4(), system_quantity=100, physical_quantity=98,
        )],
    )

    with patch("app.api.v1.reconciliation.ReconciliationRepository") as MockRepo:
        instance = AsyncMock()
        orm_recon = AsyncMock()
        orm_recon.items = []
        instance.create.return_value = orm_recon
        MockRepo.return_value = instance

        with patch("app.api.v1.reconciliation.StockReconciliation") as MockModel:
            MockModel.model_validate.return_value = recon
            result = await create_reconciliation(body=body, tenant_id=TENANT, db=mock_db)

    assert result.status == ReconciliationStatus.DRAFT


async def test_get_reconciliation_not_found():
    from app.api.v1.reconciliation import get_reconciliation

    mock_db = AsyncMock()

    with patch("app.api.v1.reconciliation.ReconciliationRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_reconciliation(reconciliation_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db)


async def test_submit_reconciliation():
    from app.api.v1.reconciliation import submit_reconciliation

    recon = _make_reconciliation(status=ReconciliationStatus.SUBMITTED)
    mock_db = AsyncMock()

    with patch("app.api.v1.reconciliation.ReconciliationRepository") as MockRepo:
        instance = AsyncMock()
        orm_recon = AsyncMock()
        orm_recon.status = ReconciliationStatus.DRAFT
        orm_recon.items = []
        instance.get_by_id.return_value = orm_recon
        instance.update_status.return_value = orm_recon
        MockRepo.return_value = instance

        with patch("app.api.v1.reconciliation.StockReconciliation") as MockModel:
            MockModel.model_validate.return_value = recon
            result = await submit_reconciliation(
                reconciliation_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db,
            )

    assert result.status == ReconciliationStatus.SUBMITTED


async def test_submit_reconciliation_not_found():
    from app.api.v1.reconciliation import submit_reconciliation

    mock_db = AsyncMock()

    with patch("app.api.v1.reconciliation.ReconciliationRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await submit_reconciliation(
                reconciliation_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db,
            )


async def test_approve_reconciliation_endpoint():
    from app.api.v1.reconciliation import approve_reconciliation_endpoint

    recon = _make_reconciliation(status=ReconciliationStatus.APPROVED, approved_by="boss")
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()

    with patch(
        "app.api.v1.reconciliation.approve_reconciliation", new_callable=AsyncMock
    ) as mock_svc:
        orm_recon = AsyncMock()
        orm_recon.items = []
        mock_svc.return_value = orm_recon

        with patch("app.api.v1.reconciliation.StockReconciliation") as MockModel:
            MockModel.model_validate.return_value = recon
            result = await approve_reconciliation_endpoint(
                reconciliation_id=uuid.uuid4(),
                approved_by="boss",
                tenant_id=TENANT,
                correlation_id="corr-1",
                db=mock_db,
                kafka_producer=mock_kafka,
            )

    assert result.status == ReconciliationStatus.APPROVED
    mock_svc.assert_awaited_once()


# ── OWN_SHOP location type ────────────────────────────────────────────────────


def test_own_shop_location_type_exists():
    assert LocationType.OWN_SHOP == "OWN_SHOP"


async def test_create_own_shop_location():
    from app.api.v1.location import create_location

    loc = _make_location(type=LocationType.OWN_SHOP, name="Main Street Shop")
    body = LocationCreate(name="Main Street Shop", type=LocationType.OWN_SHOP)
    mock_db = AsyncMock()

    with patch("app.api.v1.location.LocationRepository") as MockRepo:
        instance = AsyncMock()
        instance.create.return_value = loc
        MockRepo.return_value = instance

        with patch("app.api.v1.location.Location") as MockModel:
            MockModel.model_validate.return_value = loc

            result = await create_location(body=body, tenant_id=TENANT, db=mock_db)

    assert result.type == LocationType.OWN_SHOP


# ── dependencies ──────────────────────────────────────────────────────────────


async def test_get_db_commit_path():
    from app.dependencies import get_db

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.dependencies.AsyncSessionLocal", return_value=mock_ctx):
        gen = get_db()
        await gen.__anext__()
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    mock_session.commit.assert_awaited_once()


async def test_get_db_rollback_on_exception():
    from app.dependencies import get_db

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.dependencies.AsyncSessionLocal", return_value=mock_ctx):
        gen = get_db()
        await gen.__anext__()
        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("db error"))

    mock_session.rollback.assert_awaited_once()
