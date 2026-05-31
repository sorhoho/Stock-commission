"""Unit tests for inventory-service domain services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.models import (
    InventoryStatus,
    LocationType,
    ProductInventoryCreate,
    StockTransferCreate,
    TransferStatus,
)
from app.domain import services
from app.infrastructure.db.repository import InventoryRepository, StockTransferRepository
from telco_common.events.cloudevents import Topics
from telco_common.exceptions import NotFoundException, UnprocessableEntityException


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_orm_inventory(
    inventory_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    quantity: int = 100,
    tenant_id: str = "tenant-test",
    status: str = "AVAILABLE",
    location_type: str = "WAREHOUSE",
) -> MagicMock:
    item = MagicMock()
    item.id = inventory_id or uuid.uuid4()
    item.product_id = product_id or uuid.uuid4()
    item.product_name = "Test SIM Card"
    item.quantity = quantity
    item.quantity_uom = "EACH"
    item.location_id = location_id or uuid.uuid4()
    item.location_type = location_type
    item.status = status
    item.tenant_id = tenant_id
    item.serial_number_range_start = None
    item.serial_number_range_end = None
    return item


def _make_orm_transfer(
    transfer_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    source_location_id: uuid.UUID | None = None,
    destination_location_id: uuid.UUID | None = None,
    quantity: int = 10,
    status: str = "PENDING",
    tenant_id: str = "tenant-test",
) -> MagicMock:
    transfer = MagicMock()
    transfer.id = transfer_id or uuid.uuid4()
    transfer.transfer_order_number = "TRF-001"
    transfer.product_id = product_id or uuid.uuid4()
    transfer.source_location_id = source_location_id or uuid.uuid4()
    transfer.destination_location_id = destination_location_id or uuid.uuid4()
    transfer.quantity = quantity
    transfer.status = TransferStatus(status)
    transfer.tenant_id = tenant_id
    transfer.requested_date = datetime.now(UTC)
    transfer.completed_date = None
    return transfer


# ---------------------------------------------------------------------------
# Tests: complete_transfer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_transfer_publishes_correct_kafka_event():
    """complete_transfer should publish a StockTransferred event on the correct topic."""
    tenant_id = "tenant-abc"
    product_id = uuid.uuid4()
    source_loc_id = uuid.uuid4()
    dest_loc_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    inv_id = uuid.uuid4()

    # Build mock ORM objects
    mock_transfer = _make_orm_transfer(
        transfer_id=transfer_id,
        product_id=product_id,
        source_location_id=source_loc_id,
        destination_location_id=dest_loc_id,
        quantity=5,
        status="PENDING",
        tenant_id=tenant_id,
    )
    mock_source_inv = _make_orm_inventory(
        inventory_id=inv_id,
        product_id=product_id,
        location_id=source_loc_id,
        quantity=50,
        tenant_id=tenant_id,
    )
    mock_dest_inv = _make_orm_inventory(
        product_id=product_id,
        location_id=dest_loc_id,
        quantity=0,
        tenant_id=tenant_id,
    )
    mock_completed_transfer = _make_orm_transfer(
        transfer_id=transfer_id,
        product_id=product_id,
        status="DELIVERED",
        tenant_id=tenant_id,
    )
    mock_completed_transfer.status = TransferStatus.DELIVERED

    # Mock repositories
    transfer_repo = AsyncMock(spec=StockTransferRepository)
    transfer_repo.get_by_id.return_value = mock_transfer
    transfer_repo.update_status.return_value = mock_completed_transfer

    inventory_repo = AsyncMock(spec=InventoryRepository)
    # First call returns source items, second returns dest items
    inventory_repo.list_with_filters.side_effect = [
        [mock_source_inv],  # source lookup
        [mock_dest_inv],    # dest lookup
    ]
    inventory_repo.adjust_quantity.return_value = mock_source_inv

    # Mock Kafka producer
    kafka_producer = AsyncMock()
    kafka_producer.send = AsyncMock(return_value=None)

    result = await services.complete_transfer(
        transfer_id=transfer_id,
        tenant_id=tenant_id,
        transfer_repo=transfer_repo,
        inventory_repo=inventory_repo,
        kafka_producer=kafka_producer,
        correlation_id="corr-123",
    )

    # Assert Kafka was called with the right topic
    kafka_producer.send.assert_called_once()
    call_kwargs = kafka_producer.send.call_args

    # Positional and keyword arg handling
    sent_topic = call_kwargs.kwargs.get("topic") or call_kwargs.args[0]
    sent_event = call_kwargs.kwargs.get("event") or call_kwargs.args[1]

    assert sent_topic == Topics.INVENTORY_STOCK_TRANSFERRED
    assert sent_event["type"] == Topics.INVENTORY_STOCK_TRANSFERRED
    assert sent_event["data"]["product_id"] == str(product_id)
    assert sent_event["data"]["quantity"] == 5
    assert sent_event["data"]["tenant_id"] == tenant_id
    assert sent_event["tenantid"] == tenant_id


@pytest.mark.asyncio
async def test_complete_transfer_raises_not_found_when_transfer_missing():
    transfer_repo = AsyncMock(spec=StockTransferRepository)
    transfer_repo.get_by_id.return_value = None

    inventory_repo = AsyncMock(spec=InventoryRepository)
    kafka_producer = AsyncMock()

    with pytest.raises(NotFoundException):
        await services.complete_transfer(
            transfer_id=uuid.uuid4(),
            tenant_id="tenant-x",
            transfer_repo=transfer_repo,
            inventory_repo=inventory_repo,
            kafka_producer=kafka_producer,
        )


@pytest.mark.asyncio
async def test_complete_transfer_raises_if_already_delivered():
    tenant_id = "tenant-abc"
    mock_transfer = _make_orm_transfer(status="DELIVERED", tenant_id=tenant_id)

    transfer_repo = AsyncMock(spec=StockTransferRepository)
    transfer_repo.get_by_id.return_value = mock_transfer

    inventory_repo = AsyncMock(spec=InventoryRepository)
    kafka_producer = AsyncMock()

    with pytest.raises(UnprocessableEntityException, match="already DELIVERED"):
        await services.complete_transfer(
            transfer_id=mock_transfer.id,
            tenant_id=tenant_id,
            transfer_repo=transfer_repo,
            inventory_repo=inventory_repo,
            kafka_producer=kafka_producer,
        )


@pytest.mark.asyncio
async def test_complete_transfer_raises_if_insufficient_stock():
    tenant_id = "tenant-abc"
    product_id = uuid.uuid4()
    source_loc_id = uuid.uuid4()

    mock_transfer = _make_orm_transfer(
        product_id=product_id,
        source_location_id=source_loc_id,
        quantity=100,  # Requesting 100
        status="PENDING",
        tenant_id=tenant_id,
    )
    mock_source_inv = _make_orm_inventory(
        product_id=product_id,
        location_id=source_loc_id,
        quantity=10,  # Only 10 available
        tenant_id=tenant_id,
    )

    transfer_repo = AsyncMock(spec=StockTransferRepository)
    transfer_repo.get_by_id.return_value = mock_transfer

    inventory_repo = AsyncMock(spec=InventoryRepository)
    inventory_repo.list_with_filters.return_value = [mock_source_inv]

    kafka_producer = AsyncMock()

    with pytest.raises(UnprocessableEntityException, match="Insufficient stock"):
        await services.complete_transfer(
            transfer_id=mock_transfer.id,
            tenant_id=tenant_id,
            transfer_repo=transfer_repo,
            inventory_repo=inventory_repo,
            kafka_producer=kafka_producer,
        )


# ---------------------------------------------------------------------------
# Tests: adjust_stock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adjust_stock_updates_quantity_and_publishes_event():
    """adjust_stock should persist the adjustment and publish StockAdjustedData event."""
    tenant_id = "tenant-abc"
    inv_id = uuid.uuid4()
    product_id = uuid.uuid4()
    location_id = uuid.uuid4()

    mock_item = _make_orm_inventory(
        inventory_id=inv_id,
        product_id=product_id,
        location_id=location_id,
        quantity=50,
        tenant_id=tenant_id,
    )
    mock_updated = _make_orm_inventory(
        inventory_id=inv_id,
        product_id=product_id,
        location_id=location_id,
        quantity=60,
        tenant_id=tenant_id,
    )

    inventory_repo = AsyncMock(spec=InventoryRepository)
    inventory_repo.get_by_id.return_value = mock_item
    inventory_repo.adjust_quantity.return_value = mock_updated

    kafka_producer = AsyncMock()
    kafka_producer.send = AsyncMock(return_value=None)

    result = await services.adjust_stock(
        inventory_id=inv_id,
        delta=10,
        reason="Stock receipt",
        adjusted_by="warehouse-user",
        tenant_id=tenant_id,
        inventory_repo=inventory_repo,
        kafka_producer=kafka_producer,
        correlation_id="corr-456",
    )

    # Verify quantity adjustment was called with correct delta
    inventory_repo.adjust_quantity.assert_called_once_with(inv_id, 10, tenant_id)

    # Verify Kafka publish
    kafka_producer.send.assert_called_once()
    call_kwargs = kafka_producer.send.call_args
    sent_topic = call_kwargs.kwargs.get("topic") or call_kwargs.args[0]
    sent_event = call_kwargs.kwargs.get("event") or call_kwargs.args[1]

    assert sent_topic == Topics.INVENTORY_STOCK_ADJUSTED
    assert sent_event["type"] == Topics.INVENTORY_STOCK_ADJUSTED
    assert sent_event["data"]["inventory_id"] == str(inv_id)
    assert sent_event["data"]["previous_quantity"] == 50
    assert sent_event["data"]["new_quantity"] == 60
    assert sent_event["data"]["adjustment_reason"] == "Stock receipt"
    assert sent_event["data"]["adjusted_by"] == "warehouse-user"


@pytest.mark.asyncio
async def test_adjust_stock_raises_when_would_go_negative():
    """adjust_stock should raise UnprocessableEntityException if resulting qty < 0."""
    tenant_id = "tenant-abc"
    inv_id = uuid.uuid4()

    mock_item = _make_orm_inventory(
        inventory_id=inv_id,
        quantity=5,
        tenant_id=tenant_id,
    )

    inventory_repo = AsyncMock(spec=InventoryRepository)
    inventory_repo.get_by_id.return_value = mock_item

    kafka_producer = AsyncMock()

    with pytest.raises(UnprocessableEntityException, match="negative quantity"):
        await services.adjust_stock(
            inventory_id=inv_id,
            delta=-10,  # Would result in -5
            reason="Write-off",
            adjusted_by="manager",
            tenant_id=tenant_id,
            inventory_repo=inventory_repo,
            kafka_producer=kafka_producer,
        )

    # Ensure no DB write or Kafka publish happened
    inventory_repo.adjust_quantity.assert_not_called()
    kafka_producer.send.assert_not_called()


@pytest.mark.asyncio
async def test_adjust_stock_raises_not_found():
    """adjust_stock should raise NotFoundException when inventory item does not exist."""
    inventory_repo = AsyncMock(spec=InventoryRepository)
    inventory_repo.get_by_id.return_value = None

    kafka_producer = AsyncMock()

    with pytest.raises(NotFoundException):
        await services.adjust_stock(
            inventory_id=uuid.uuid4(),
            delta=5,
            reason="Test",
            adjusted_by="tester",
            tenant_id="tenant-x",
            inventory_repo=inventory_repo,
            kafka_producer=kafka_producer,
        )


# ---------------------------------------------------------------------------
# Tests: domain validation
# ---------------------------------------------------------------------------


def test_stock_transfer_create_validates_positive_quantity():
    """StockTransferCreate should reject quantity <= 0."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        StockTransferCreate(
            transfer_order_number="TRF-BAD",
            source_location_id=uuid.uuid4(),
            destination_location_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            quantity=0,  # Must be gt=0
            initiated_by="user",
            requested_date=datetime.now(UTC),
        )


def test_product_inventory_create_validates_non_negative_quantity():
    """ProductInventoryCreate should reject negative quantity."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProductInventoryCreate(
            product_id=uuid.uuid4(),
            product_name="Test",
            quantity=-1,  # Must be ge=0
            location_id=uuid.uuid4(),
            location_type=LocationType.WAREHOUSE,
        )


def test_inventory_status_enum_values():
    """InventoryStatus should have expected string values."""
    assert InventoryStatus.AVAILABLE == "AVAILABLE"
    assert InventoryStatus.RESERVED == "RESERVED"
    assert InventoryStatus.DAMAGED == "DAMAGED"
    assert InventoryStatus.IN_TRANSIT == "IN_TRANSIT"


def test_transfer_status_enum_values():
    """TransferStatus should have expected string values."""
    assert TransferStatus.PENDING == "PENDING"
    assert TransferStatus.DELIVERED == "DELIVERED"
    assert TransferStatus.CANCELLED == "CANCELLED"
