"""Unit tests for inventory-service repositories (SQLite in-memory)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
    ResourceCharacteristicCreate,
    ResourceStatusType,
    ResourceType,
    StockReservationCreate,
    StockTransferCreate,
    TransferStatus,
)
from app.infrastructure.db.repository import (
    GoodsReceiptRepository,
    InventoryRepository,
    LocationRepository,
    ReconciliationRepository,
    ResourceRepository,
    StockReservationRepository,
    StockTransferRepository,
)
from telco_common.db.base import Base

pytestmark = pytest.mark.asyncio

TENANT = "tenant-repo-001"
OTHER_TENANT = "tenant-other"

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession,
        expire_on_commit=False, autocommit=False, autoflush=False,
    )
    async with factory() as session:
        yield session


# ── LocationRepository ────────────────────────────────────────────────────────


async def test_location_create_and_get(db_session):
    repo = LocationRepository(db_session)
    data = LocationCreate(name="Warehouse A", type=LocationType.WAREHOUSE)
    created = await repo.create(data=data, tenant_id=TENANT)
    await db_session.commit()

    found = await repo.get_by_id(location_id=created.id, tenant_id=TENANT)
    assert found is not None
    assert found.name == "Warehouse A"
    assert found.type == "WAREHOUSE"
    assert found.tenant_id == TENANT


async def test_location_get_not_found(db_session):
    repo = LocationRepository(db_session)
    result = await repo.get_by_id(location_id=uuid.uuid4(), tenant_id=TENANT)
    assert result is None


async def test_location_tenant_isolation(db_session):
    repo = LocationRepository(db_session)
    data = LocationCreate(name="Tenant A Warehouse", type=LocationType.WAREHOUSE)
    created = await repo.create(data=data, tenant_id=TENANT)
    await db_session.commit()

    result = await repo.get_by_id(location_id=created.id, tenant_id=OTHER_TENANT)
    assert result is None


async def test_location_list_empty(db_session):
    repo = LocationRepository(db_session)
    items = await repo.list(tenant_id=TENANT)
    assert items == []


async def test_location_list_with_type_filter(db_session):
    repo = LocationRepository(db_session)
    await repo.create(data=LocationCreate(name="WH1", type=LocationType.WAREHOUSE), tenant_id=TENANT)
    await repo.create(data=LocationCreate(name="DC1", type=LocationType.DISTRIBUTION_CENTER), tenant_id=TENANT)
    await db_session.commit()

    warehouses = await repo.list(tenant_id=TENANT, type_filter=LocationType.WAREHOUSE)
    assert len(warehouses) == 1
    assert warehouses[0].name == "WH1"


async def test_location_list_without_filter(db_session):
    repo = LocationRepository(db_session)
    await repo.create(data=LocationCreate(name="A", type=LocationType.WAREHOUSE), tenant_id=TENANT)
    await repo.create(data=LocationCreate(name="B", type=LocationType.DEALER_OUTLET), tenant_id=TENANT)
    await db_session.commit()

    items = await repo.list(tenant_id=TENANT)
    assert len(items) == 2


async def test_location_update_found(db_session):
    repo = LocationRepository(db_session)
    created = await repo.create(data=LocationCreate(name="Old Name", type=LocationType.WAREHOUSE), tenant_id=TENANT)
    await db_session.commit()

    updated = await repo.update(
        location_id=created.id, tenant_id=TENANT,
        data=LocationUpdate(name="New Name"),
    )
    assert updated is not None
    assert updated.name == "New Name"


async def test_location_update_not_found(db_session):
    repo = LocationRepository(db_session)
    result = await repo.update(
        location_id=uuid.uuid4(), tenant_id=TENANT,
        data=LocationUpdate(name="X"),
    )
    assert result is None


# ── InventoryRepository ───────────────────────────────────────────────────────


def _inv_create(location_id: uuid.UUID, product_id: uuid.UUID | None = None) -> ProductInventoryCreate:
    return ProductInventoryCreate(
        product_id=product_id or uuid.uuid4(),
        product_name="SIM Card",
        quantity=100,
        location_id=location_id,
        location_type=LocationType.WAREHOUSE,
    )


@pytest_asyncio.fixture
async def location_id(db_session) -> uuid.UUID:
    repo = LocationRepository(db_session)
    loc = await repo.create(data=LocationCreate(name="W", type=LocationType.WAREHOUSE), tenant_id=TENANT)
    await db_session.commit()
    return loc.id


async def test_inventory_create_and_get(db_session, location_id):
    repo = InventoryRepository(db_session)
    data = _inv_create(location_id)
    created = await repo.create(data=data, tenant_id=TENANT)
    await db_session.commit()

    found = await repo.get_by_id(inventory_id=created.id, tenant_id=TENANT)
    assert found is not None
    assert found.product_name == "SIM Card"
    assert found.quantity == 100


async def test_inventory_get_not_found(db_session):
    repo = InventoryRepository(db_session)
    result = await repo.get_by_id(inventory_id=uuid.uuid4(), tenant_id=TENANT)
    assert result is None


async def test_inventory_tenant_isolation(db_session, location_id):
    repo = InventoryRepository(db_session)
    created = await repo.create(data=_inv_create(location_id), tenant_id=TENANT)
    await db_session.commit()

    result = await repo.get_by_id(inventory_id=created.id, tenant_id=OTHER_TENANT)
    assert result is None


async def test_inventory_list_empty(db_session):
    repo = InventoryRepository(db_session)
    items = await repo.list_with_filters(tenant_id=TENANT)
    assert list(items) == []


async def test_inventory_list_with_status_filter(db_session, location_id):
    repo = InventoryRepository(db_session)
    prod_id = uuid.uuid4()
    await repo.create(data=ProductInventoryCreate(
        product_id=prod_id, product_name="SIM", quantity=5,
        location_id=location_id, location_type=LocationType.WAREHOUSE,
        status=InventoryStatus.AVAILABLE,
    ), tenant_id=TENANT)
    await repo.create(data=ProductInventoryCreate(
        product_id=uuid.uuid4(), product_name="Device", quantity=2,
        location_id=location_id, location_type=LocationType.WAREHOUSE,
        status=InventoryStatus.RESERVED,
    ), tenant_id=TENANT)
    await db_session.commit()

    avail = await repo.list_with_filters(tenant_id=TENANT, status=InventoryStatus.AVAILABLE)
    assert len(list(avail)) == 1

    reserved = await repo.list_with_filters(tenant_id=TENANT, status=InventoryStatus.RESERVED)
    assert len(list(reserved)) == 1


async def test_inventory_list_with_location_filter(db_session, location_id):
    repo = InventoryRepository(db_session)
    await repo.create(data=_inv_create(location_id), tenant_id=TENANT)
    await db_session.commit()

    items = await repo.list_with_filters(tenant_id=TENANT, location_id=location_id)
    assert len(list(items)) == 1

    items_other = await repo.list_with_filters(tenant_id=TENANT, location_id=uuid.uuid4())
    assert list(items_other) == []


async def test_inventory_list_with_product_filter(db_session, location_id):
    repo = InventoryRepository(db_session)
    prod_id = uuid.uuid4()
    await repo.create(data=_inv_create(location_id, product_id=prod_id), tenant_id=TENANT)
    await repo.create(data=_inv_create(location_id, product_id=uuid.uuid4()), tenant_id=TENANT)
    await db_session.commit()

    items = await repo.list_with_filters(tenant_id=TENANT, product_id=prod_id)
    assert len(list(items)) == 1


async def test_inventory_list_pagination(db_session, location_id):
    repo = InventoryRepository(db_session)
    for i in range(5):
        await repo.create(data=ProductInventoryCreate(
            product_id=uuid.uuid4(), product_name=f"SIM{i:02d}", quantity=1,
            location_id=location_id, location_type=LocationType.WAREHOUSE,
        ), tenant_id=TENANT)
    await db_session.commit()

    page1 = await repo.list_with_filters(tenant_id=TENANT, page=1, size=3)
    page2 = await repo.list_with_filters(tenant_id=TENANT, page=2, size=3)
    assert len(list(page1)) == 3
    assert len(list(page2)) == 2


async def test_inventory_update_found(db_session, location_id):
    repo = InventoryRepository(db_session)
    created = await repo.create(data=_inv_create(location_id), tenant_id=TENANT)
    await db_session.commit()

    updated = await repo.update(
        inventory_id=created.id, tenant_id=TENANT,
        data=ProductInventoryUpdate(quantity=50, product_name="Updated SIM"),
    )
    assert updated is not None
    assert updated.quantity == 50
    assert updated.product_name == "Updated SIM"


async def test_inventory_update_not_found(db_session):
    repo = InventoryRepository(db_session)
    result = await repo.update(
        inventory_id=uuid.uuid4(), tenant_id=TENANT,
        data=ProductInventoryUpdate(quantity=5),
    )
    assert result is None


async def test_inventory_adjust_quantity(db_session, location_id):
    repo = InventoryRepository(db_session)
    created = await repo.create(data=_inv_create(location_id), tenant_id=TENANT)
    await db_session.commit()

    updated = await repo.adjust_quantity(
        inventory_id=created.id, delta=-10, tenant_id=TENANT
    )
    assert updated is not None
    assert updated.quantity == 90


async def test_inventory_adjust_quantity_not_found(db_session):
    repo = InventoryRepository(db_session)
    result = await repo.adjust_quantity(
        inventory_id=uuid.uuid4(), delta=5, tenant_id=TENANT
    )
    assert result is None


# ── StockTransferRepository ───────────────────────────────────────────────────


def _transfer_create(src_id: uuid.UUID, dst_id: uuid.UUID, product_id: uuid.UUID | None = None) -> StockTransferCreate:
    return StockTransferCreate(
        transfer_order_number=f"TRF-{uuid.uuid4().hex[:8]}",
        source_location_id=src_id,
        destination_location_id=dst_id,
        product_id=product_id or uuid.uuid4(),
        quantity=10,
        initiated_by="admin",
        requested_date=datetime.now(UTC),
    )


@pytest_asyncio.fixture
async def two_location_ids(db_session):
    loc_repo = LocationRepository(db_session)
    src = await loc_repo.create(data=LocationCreate(name="Src", type=LocationType.WAREHOUSE), tenant_id=TENANT)
    dst = await loc_repo.create(data=LocationCreate(name="Dst", type=LocationType.DISTRIBUTION_CENTER), tenant_id=TENANT)
    await db_session.commit()
    return src.id, dst.id


async def test_transfer_create_and_get(db_session, two_location_ids):
    src_id, dst_id = two_location_ids
    repo = StockTransferRepository(db_session)
    data = _transfer_create(src_id, dst_id)
    created = await repo.create(data=data, tenant_id=TENANT)
    await db_session.commit()

    found = await repo.get_by_id(transfer_id=created.id, tenant_id=TENANT)
    assert found is not None
    assert found.quantity == 10
    assert found.status == "PENDING"


async def test_transfer_get_not_found(db_session):
    repo = StockTransferRepository(db_session)
    result = await repo.get_by_id(transfer_id=uuid.uuid4(), tenant_id=TENANT)
    assert result is None


async def test_transfer_tenant_isolation(db_session, two_location_ids):
    src_id, dst_id = two_location_ids
    repo = StockTransferRepository(db_session)
    created = await repo.create(data=_transfer_create(src_id, dst_id), tenant_id=TENANT)
    await db_session.commit()

    result = await repo.get_by_id(transfer_id=created.id, tenant_id=OTHER_TENANT)
    assert result is None


async def test_transfer_list_empty(db_session):
    repo = StockTransferRepository(db_session)
    items = await repo.list_with_filters(tenant_id=TENANT)
    assert list(items) == []


async def test_transfer_list_with_status_filter(db_session, two_location_ids):
    src_id, dst_id = two_location_ids
    repo = StockTransferRepository(db_session)
    created = await repo.create(data=_transfer_create(src_id, dst_id), tenant_id=TENANT)
    await db_session.commit()

    pending = await repo.list_with_filters(tenant_id=TENANT, status=TransferStatus.PENDING)
    assert len(list(pending)) == 1

    delivered = await repo.list_with_filters(tenant_id=TENANT, status=TransferStatus.DELIVERED)
    assert list(delivered) == []


async def test_transfer_list_with_source_filter(db_session, two_location_ids):
    src_id, dst_id = two_location_ids
    repo = StockTransferRepository(db_session)
    await repo.create(data=_transfer_create(src_id, dst_id), tenant_id=TENANT)
    await db_session.commit()

    items = await repo.list_with_filters(tenant_id=TENANT, source_location_id=src_id)
    assert len(list(items)) == 1

    items_other = await repo.list_with_filters(tenant_id=TENANT, source_location_id=uuid.uuid4())
    assert list(items_other) == []


async def test_transfer_list_with_destination_filter(db_session, two_location_ids):
    src_id, dst_id = two_location_ids
    repo = StockTransferRepository(db_session)
    await repo.create(data=_transfer_create(src_id, dst_id), tenant_id=TENANT)
    await db_session.commit()

    items = await repo.list_with_filters(tenant_id=TENANT, destination_location_id=dst_id)
    assert len(list(items)) == 1


async def test_transfer_list_with_product_filter(db_session, two_location_ids):
    src_id, dst_id = two_location_ids
    repo = StockTransferRepository(db_session)
    prod_id = uuid.uuid4()
    await repo.create(data=_transfer_create(src_id, dst_id, product_id=prod_id), tenant_id=TENANT)
    await repo.create(data=_transfer_create(src_id, dst_id, product_id=uuid.uuid4()), tenant_id=TENANT)
    await db_session.commit()

    items = await repo.list_with_filters(tenant_id=TENANT, product_id=prod_id)
    assert len(list(items)) == 1


async def test_transfer_update_status(db_session, two_location_ids):
    src_id, dst_id = two_location_ids
    repo = StockTransferRepository(db_session)
    created = await repo.create(data=_transfer_create(src_id, dst_id), tenant_id=TENANT)
    await db_session.commit()

    completed = datetime.now(UTC)
    updated = await repo.update_status(
        transfer_id=created.id, tenant_id=TENANT,
        status=TransferStatus.DELIVERED, completed_date=completed,
    )
    assert updated is not None
    assert updated.status == "DELIVERED"
    assert updated.completed_date is not None


async def test_transfer_update_status_not_found(db_session):
    repo = StockTransferRepository(db_session)
    result = await repo.update_status(
        transfer_id=uuid.uuid4(), tenant_id=TENANT,
        status=TransferStatus.DELIVERED,
    )
    assert result is None


# ── GoodsReceiptRepository ────────────────────────────────────────────────────


async def test_grn_create_and_get(db_session):
    loc_repo = LocationRepository(db_session)
    loc = await loc_repo.create(LocationCreate(name="WH", type=LocationType.WAREHOUSE), TENANT)
    await db_session.commit()

    repo = GoodsReceiptRepository(db_session)
    now = datetime.now(UTC)
    data = GoodsReceiptCreate(
        grn_number="GRN-001",
        supplier_reference="SAP-PO-001",
        product_id=uuid.uuid4(),
        location_id=loc.id,
        quantity_received=100,
        received_by="admin",
        received_date=now,
    )
    created = await repo.create(data, TENANT)
    await db_session.commit()

    found = await repo.get_by_id(created.id, TENANT)
    assert found is not None
    assert found.grn_number == "GRN-001"
    assert found.quantity_received == 100
    assert found.tenant_id == TENANT


async def test_grn_tenant_isolation(db_session):
    loc_repo = LocationRepository(db_session)
    loc = await loc_repo.create(LocationCreate(name="WH", type=LocationType.WAREHOUSE), TENANT)
    await db_session.commit()

    repo = GoodsReceiptRepository(db_session)
    now = datetime.now(UTC)
    data = GoodsReceiptCreate(
        grn_number="GRN-TI",
        product_id=uuid.uuid4(),
        location_id=loc.id,
        quantity_received=10,
        received_by="admin",
        received_date=now,
    )
    created = await repo.create(data, TENANT)
    await db_session.commit()

    result = await repo.get_by_id(created.id, OTHER_TENANT)
    assert result is None


async def test_grn_list_with_filters(db_session):
    loc_repo = LocationRepository(db_session)
    loc = await loc_repo.create(LocationCreate(name="WH", type=LocationType.WAREHOUSE), TENANT)
    await db_session.commit()

    repo = GoodsReceiptRepository(db_session)
    pid = uuid.uuid4()
    now = datetime.now(UTC)
    for i in range(3):
        await repo.create(GoodsReceiptCreate(
            grn_number=f"GRN-{i}",
            product_id=pid,
            location_id=loc.id,
            quantity_received=10,
            received_by="admin",
            received_date=now,
        ), TENANT)
    await db_session.commit()

    results = await repo.list_with_filters(TENANT, product_id=pid)
    assert len(results) == 3

    results_filtered = await repo.list_with_filters(TENANT, product_id=uuid.uuid4())
    assert results_filtered == []


# ── StockReservationRepository ────────────────────────────────────────────────


async def _make_inventory_item(db_session, tenant=TENANT, qty=100):
    loc_repo = LocationRepository(db_session)
    loc = await loc_repo.create(LocationCreate(name="WH-R", type=LocationType.WAREHOUSE), tenant)
    inv_repo = InventoryRepository(db_session)
    item = await inv_repo.create(ProductInventoryCreate(
        product_id=uuid.uuid4(),
        product_name="Test Product",
        quantity=qty,
        location_id=loc.id,
        location_type=LocationType.WAREHOUSE,
    ), tenant)
    await db_session.commit()
    return item


async def test_reservation_create_and_list(db_session):
    inv = await _make_inventory_item(db_session)

    repo = StockReservationRepository(db_session)
    data = StockReservationCreate(
        inventory_id=inv.id,
        reserved_quantity=20,
        reserved_by="order-svc",
        reservation_expiry=datetime.now(UTC),
    )
    created = await repo.create(data, TENANT)
    await db_session.commit()

    listings = await repo.list_for_inventory(inv.id, TENANT)
    assert len(listings) == 1
    assert listings[0].reserved_quantity == 20


async def test_reservation_total_reserved(db_session):
    inv = await _make_inventory_item(db_session)
    repo = StockReservationRepository(db_session)

    for qty in [10, 15]:
        await repo.create(StockReservationCreate(
            inventory_id=inv.id,
            reserved_quantity=qty,
            reserved_by="svc",
            reservation_expiry=datetime.now(UTC),
        ), TENANT)
    await db_session.commit()

    total = await repo.total_reserved(inv.id, TENANT)
    assert total == 25


async def test_reservation_delete(db_session):
    inv = await _make_inventory_item(db_session)
    repo = StockReservationRepository(db_session)
    created = await repo.create(StockReservationCreate(
        inventory_id=inv.id,
        reserved_quantity=5,
        reserved_by="svc",
        reservation_expiry=datetime.now(UTC),
    ), TENANT)
    await db_session.commit()

    deleted = await repo.delete(created.id, TENANT)
    assert deleted is True

    listings = await repo.list_for_inventory(inv.id, TENANT)
    assert len(listings) == 0


async def test_reservation_delete_wrong_tenant(db_session):
    inv = await _make_inventory_item(db_session)
    repo = StockReservationRepository(db_session)
    created = await repo.create(StockReservationCreate(
        inventory_id=inv.id,
        reserved_quantity=5,
        reserved_by="svc",
        reservation_expiry=datetime.now(UTC),
    ), TENANT)
    await db_session.commit()

    deleted = await repo.delete(created.id, OTHER_TENANT)
    assert deleted is False


# ── ResourceRepository ────────────────────────────────────────────────────────


async def test_resource_create_and_get(db_session):
    repo = ResourceRepository(db_session)
    pid = uuid.uuid4()
    data = ResourceCreate(
        resource_name="Samsung A15",
        resource_type=ResourceType.DEVICE,
        product_id=pid,
        characteristics=[ResourceCharacteristicCreate(name="IMEI", value="358240051111110")],
    )
    created = await repo.create(data, TENANT)
    await db_session.commit()

    found = await repo.get_by_id(created.id, TENANT)
    assert found is not None
    assert found.resource_name == "Samsung A15"
    assert len(found.characteristics) == 1
    assert found.characteristics[0].name == "IMEI"


async def test_resource_list_with_filters(db_session):
    repo = ResourceRepository(db_session)
    pid = uuid.uuid4()
    await repo.create(ResourceCreate(
        resource_name="Device A",
        resource_type=ResourceType.DEVICE,
        product_id=pid,
    ), TENANT)
    await repo.create(ResourceCreate(
        resource_name="SIM 1",
        resource_type=ResourceType.SIM,
        product_id=pid,
    ), TENANT)
    await db_session.commit()

    all_items = await repo.list_with_filters(TENANT, product_id=pid)
    assert len(all_items) == 2

    sims = await repo.list_with_filters(TENANT, status=ResourceStatusType.AVAILABLE)
    assert len(sims) == 2


async def test_resource_characteristic_lookup(db_session):
    repo = ResourceRepository(db_session)
    imei = "358240051111111"
    await repo.create(ResourceCreate(
        resource_name="Phone X",
        resource_type=ResourceType.DEVICE,
        product_id=uuid.uuid4(),
        characteristics=[ResourceCharacteristicCreate(name="IMEI", value=imei)],
    ), TENANT)
    await db_session.commit()

    results = await repo.list_with_filters(
        TENANT, characteristic_name="IMEI", characteristic_value=imei,
    )
    assert len(results) == 1
    assert results[0].resource_name == "Phone X"


async def test_resource_update_status(db_session):
    repo = ResourceRepository(db_session)
    created = await repo.create(ResourceCreate(
        resource_name="Device B",
        resource_type=ResourceType.DEVICE,
        product_id=uuid.uuid4(),
    ), TENANT)
    await db_session.commit()

    updated = await repo.update_status(
        created.id, TENANT, ResourceStatusType.SOLD, allocated_to="TXN-001"
    )
    assert updated is not None
    assert updated.status == "SOLD"
    assert updated.allocated_to == "TXN-001"


async def test_resource_tenant_isolation(db_session):
    repo = ResourceRepository(db_session)
    created = await repo.create(ResourceCreate(
        resource_name="Device C",
        resource_type=ResourceType.DEVICE,
        product_id=uuid.uuid4(),
    ), TENANT)
    await db_session.commit()

    found = await repo.get_by_id(created.id, OTHER_TENANT)
    assert found is None


# ── ReconciliationRepository ──────────────────────────────────────────────────


async def test_reconciliation_create_and_get(db_session):
    loc_repo = LocationRepository(db_session)
    loc = await loc_repo.create(LocationCreate(name="WH-Recon", type=LocationType.WAREHOUSE), TENANT)
    await db_session.commit()

    repo = ReconciliationRepository(db_session)
    pid = uuid.uuid4()
    recon = await repo.create(
        data_dict={
            "location_id": loc.id,
            "reconciliation_date": datetime.now(UTC),
            "counted_by": "manager",
            "notes": "Monthly check",
        },
        items=[{"product_id": pid, "system_quantity": 100, "physical_quantity": 98}],
        tenant_id=TENANT,
    )
    await db_session.commit()

    found = await repo.get_by_id(recon.id, TENANT)
    assert found is not None
    assert found.status == "DRAFT"
    assert len(found.items) == 1
    assert found.items[0].variance == -2


async def test_reconciliation_update_status(db_session):
    loc_repo = LocationRepository(db_session)
    loc = await loc_repo.create(LocationCreate(name="WH-RS", type=LocationType.WAREHOUSE), TENANT)
    await db_session.commit()

    repo = ReconciliationRepository(db_session)
    recon = await repo.create(
        data_dict={
            "location_id": loc.id,
            "reconciliation_date": datetime.now(UTC),
            "counted_by": "manager",
        },
        items=[],
        tenant_id=TENANT,
    )
    await db_session.commit()

    updated = await repo.update_status(
        recon.id, TENANT, ReconciliationStatus.SUBMITTED
    )
    assert updated is not None
    assert updated.status == "SUBMITTED"


async def test_reconciliation_get_not_found(db_session):
    repo = ReconciliationRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4(), TENANT)
    assert result is None
