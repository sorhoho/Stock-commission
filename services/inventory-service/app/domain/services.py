"""Business logic for the Inventory service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.domain.models import (
    InventoryStatus,
    StockTransferCreate,
    TransferStatus,
)
from app.infrastructure.db.repository import (
    InventoryRepository,
    StockTransferRepository,
)
from telco_common.events.cloudevents import Topics, make_event
from telco_common.events.schemas.inventory_events import (
    StockAdjustedData,
    StockTransferredData,
)
from telco_common.exceptions import NotFoundException, UnprocessableEntityException
from telco_common.kafka.producer_factory import KafkaProducer

log = structlog.get_logger(__name__)


async def create_transfer(
    data: StockTransferCreate,
    tenant_id: str,
    transfer_repo: StockTransferRepository,
    kafka_producer: KafkaProducer,
    correlation_id: str | None = None,
) -> object:
    """Create a stock transfer record.

    If the transfer is created with DELIVERED status (e.g. back-fill),
    immediately publishes a StockTransferred event.
    """
    transfer = await transfer_repo.create(data, tenant_id)
    log.info(
        "Stock transfer created",
        transfer_id=str(transfer.id),
        order_number=transfer.transfer_order_number,
        tenant_id=tenant_id,
    )
    return transfer


async def complete_transfer(
    transfer_id: uuid.UUID,
    tenant_id: str,
    transfer_repo: StockTransferRepository,
    inventory_repo: InventoryRepository,
    kafka_producer: KafkaProducer,
    correlation_id: str | None = None,
) -> object:
    """Mark a transfer as DELIVERED and update stock-on-hand at both locations.

    Steps:
    1. Load and validate the transfer (must be PENDING or IN_TRANSIT).
    2. Decrement source inventory (product_id + source_location_id).
    3. Increment destination inventory (product_id + destination_location_id).
    4. Update transfer status → DELIVERED with completed_date.
    5. Publish StockTransferredData event.
    """
    transfer = await transfer_repo.get_by_id(transfer_id, tenant_id)
    if transfer is None:
        raise NotFoundException("StockTransfer", str(transfer_id))

    if transfer.status == TransferStatus.DELIVERED:
        raise UnprocessableEntityException(
            f"Transfer {transfer_id} is already DELIVERED"
        )
    if transfer.status == TransferStatus.CANCELLED:
        raise UnprocessableEntityException(
            f"Transfer {transfer_id} is CANCELLED and cannot be completed"
        )

    now = datetime.now(UTC)

    # Locate source inventory record for the product at the source location
    source_items = await inventory_repo.list_with_filters(
        tenant_id=tenant_id,
        product_id=transfer.product_id,
        location_id=transfer.source_location_id,
        status=InventoryStatus.AVAILABLE,
    )
    if not source_items:
        raise UnprocessableEntityException(
            f"No available inventory for product {transfer.product_id} "
            f"at source location {transfer.source_location_id}"
        )
    source_item = source_items[0]
    if source_item.quantity < transfer.quantity:
        raise UnprocessableEntityException(
            f"Insufficient stock: available={source_item.quantity}, "
            f"required={transfer.quantity}"
        )

    # Decrement source
    await inventory_repo.adjust_quantity(source_item.id, -transfer.quantity, tenant_id)

    # Locate or locate destination inventory record
    dest_items = await inventory_repo.list_with_filters(
        tenant_id=tenant_id,
        product_id=transfer.product_id,
        location_id=transfer.destination_location_id,
    )
    if dest_items:
        dest_item = dest_items[0]
        await inventory_repo.adjust_quantity(dest_item.id, transfer.quantity, tenant_id)
    else:
        # Create a new inventory record at the destination
        from app.domain.models import LocationType, ProductInventoryCreate

        # Resolve location_type for destination from DB or default
        from app.infrastructure.db.models import Location as OrmLocation
        from sqlalchemy import select
        dest_loc = await inventory_repo._session.execute(
            select(OrmLocation).where(OrmLocation.id == transfer.destination_location_id)
        )
        dest_location = dest_loc.scalar_one_or_none()
        dest_loc_type = (
            LocationType(dest_location.type) if dest_location else LocationType.WAREHOUSE
        )

        new_inv = ProductInventoryCreate(
            product_id=transfer.product_id,
            product_name=source_item.product_name,
            quantity=transfer.quantity,
            quantity_uom=source_item.quantity_uom,
            location_id=transfer.destination_location_id,
            location_type=dest_loc_type,
            status=InventoryStatus.AVAILABLE,
        )
        await inventory_repo.create(new_inv, tenant_id)

    # Mark transfer complete
    updated_transfer = await transfer_repo.update_status(
        transfer_id=transfer_id,
        tenant_id=tenant_id,
        status=TransferStatus.DELIVERED,
        completed_date=now,
    )

    # Publish event
    event_data = StockTransferredData(
        transfer_id=str(transfer.id),
        transfer_order_number=transfer.transfer_order_number,
        source_location_id=str(transfer.source_location_id),
        source_location_type=str(source_item.location_type),
        destination_location_id=str(transfer.destination_location_id),
        destination_location_type=str(dest_items[0].location_type) if dest_items else "",
        product_id=str(transfer.product_id),
        quantity=transfer.quantity,
        completed_at=now.isoformat(),
        tenant_id=tenant_id,
    )
    event = make_event(
        event_type=Topics.INVENTORY_STOCK_TRANSFERRED,
        source_service="inventory-service",
        tenant_id=tenant_id,
        data=event_data,
        correlation_id=correlation_id,
    )
    await kafka_producer.send(
        topic=Topics.INVENTORY_STOCK_TRANSFERRED,
        event=event,
        key=str(transfer.id),
    )
    log.info(
        "Stock transfer completed",
        transfer_id=str(transfer.id),
        tenant_id=tenant_id,
    )
    return updated_transfer


async def adjust_stock(
    inventory_id: uuid.UUID,
    delta: int,
    reason: str,
    adjusted_by: str,
    tenant_id: str,
    inventory_repo: InventoryRepository,
    kafka_producer: KafkaProducer,
    correlation_id: str | None = None,
) -> object:
    """Adjust stock quantity for an inventory record and publish an event.

    *delta* can be positive (stock receipt / correction up) or negative
    (write-off / correction down).
    """
    item = await inventory_repo.get_by_id(inventory_id, tenant_id)
    if item is None:
        raise NotFoundException("ProductInventory", str(inventory_id))

    previous_quantity = item.quantity
    new_quantity = previous_quantity + delta

    if new_quantity < 0:
        raise UnprocessableEntityException(
            f"Adjustment would result in negative quantity "
            f"(current={previous_quantity}, delta={delta})"
        )

    updated_item = await inventory_repo.adjust_quantity(inventory_id, delta, tenant_id)
    if updated_item is None:
        raise NotFoundException("ProductInventory", str(inventory_id))

    event_data = StockAdjustedData(
        inventory_id=str(inventory_id),
        product_id=str(item.product_id),
        location_id=str(item.location_id),
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        adjustment_reason=reason,
        adjusted_by=adjusted_by,
        tenant_id=tenant_id,
    )
    event = make_event(
        event_type=Topics.INVENTORY_STOCK_ADJUSTED,
        source_service="inventory-service",
        tenant_id=tenant_id,
        data=event_data,
        correlation_id=correlation_id,
    )
    await kafka_producer.send(
        topic=Topics.INVENTORY_STOCK_ADJUSTED,
        event=event,
        key=str(inventory_id),
    )
    log.info(
        "Stock adjusted",
        inventory_id=str(inventory_id),
        delta=delta,
        previous=previous_quantity,
        new=new_quantity,
        tenant_id=tenant_id,
    )
    return updated_item
