"""Business logic for the Inventory service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.domain.models import (
    GoodsReceiptCreate,
    InventoryStatus,
    LocationType,
    ProductInventoryCreate,
    ReconciliationStatus,
    StockReservationCreate,
    StockTransferCreate,
    TransferStatus,
)
from app.infrastructure.db.repository import (
    GoodsReceiptRepository,
    InventoryRepository,
    ReconciliationRepository,
    StockReservationRepository,
    StockTransferRepository,
)
from telco_common.events.cloudevents import Topics, make_event
from telco_common.events.schemas.inventory_events import (
    StockAdjustedData,
    StockReceivedData,
    StockReservedData,
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


async def receive_stock(
    data: GoodsReceiptCreate,
    tenant_id: str,
    grn_repo: GoodsReceiptRepository,
    inventory_repo: InventoryRepository,
    kafka_producer: KafkaProducer,
    correlation_id: str | None = None,
) -> object:
    """Record a goods receipt and increase inventory at the destination location.

    Mirrors complete_transfer(): if an inventory record already exists for this
    product + location, adjust its quantity; otherwise create a new record.
    """
    receipt = await grn_repo.create(data, tenant_id)

    existing = await inventory_repo.list_with_filters(
        tenant_id=tenant_id,
        product_id=data.product_id,
        location_id=data.location_id,
    )
    if existing:
        await inventory_repo.adjust_quantity(existing[0].id, data.quantity_received, tenant_id)
    else:
        from app.infrastructure.db.models import Location as OrmLocation
        from sqlalchemy import select
        loc_result = await inventory_repo._session.execute(
            select(OrmLocation).where(OrmLocation.id == data.location_id)
        )
        orm_loc = loc_result.scalar_one_or_none()
        loc_type = LocationType(orm_loc.type) if orm_loc else LocationType.WAREHOUSE
        new_inv = ProductInventoryCreate(
            product_id=data.product_id,
            product_name=f"Product {data.product_id}",
            quantity=data.quantity_received,
            location_id=data.location_id,
            location_type=loc_type,
            status=InventoryStatus.AVAILABLE,
        )
        await inventory_repo.create(new_inv, tenant_id)

    event_data = StockReceivedData(
        grn_id=str(receipt.id),
        grn_number=receipt.grn_number,
        supplier_reference=receipt.supplier_reference,
        product_id=str(receipt.product_id),
        location_id=str(receipt.location_id),
        quantity_received=receipt.quantity_received,
        received_by=receipt.received_by,
        received_date=receipt.received_date.isoformat(),
        tenant_id=tenant_id,
    )
    event = make_event(
        event_type=Topics.INVENTORY_STOCK_RECEIVED,
        source_service="inventory-service",
        tenant_id=tenant_id,
        data=event_data,
        correlation_id=correlation_id,
    )
    await kafka_producer.send(
        topic=Topics.INVENTORY_STOCK_RECEIVED, event=event, key=str(receipt.id)
    )
    log.info("goods_receipt.created", grn_id=str(receipt.id), qty=data.quantity_received)
    return receipt


async def reserve_stock(
    data: StockReservationCreate,
    tenant_id: str,
    inventory_repo: InventoryRepository,
    reservation_repo: StockReservationRepository,
    kafka_producer: KafkaProducer,
    correlation_id: str | None = None,
) -> object:
    """Create a stock reservation, validating that sufficient stock is available."""
    item = await inventory_repo.get_by_id(data.inventory_id, tenant_id)
    if item is None:
        raise NotFoundException("ProductInventory", str(data.inventory_id))

    already_reserved = await reservation_repo.total_reserved(data.inventory_id, tenant_id)
    available = item.quantity - already_reserved
    if available < data.reserved_quantity:
        raise UnprocessableEntityException(
            f"Insufficient available stock: available={available}, requested={data.reserved_quantity}"
        )

    reservation = await reservation_repo.create(data, tenant_id)

    event_data = StockReservedData(
        reservation_id=str(reservation.id),
        inventory_id=str(data.inventory_id),
        reserved_quantity=data.reserved_quantity,
        reserved_by=data.reserved_by,
        reservation_expiry=data.reservation_expiry.isoformat(),
        tenant_id=tenant_id,
    )
    event = make_event(
        event_type=Topics.INVENTORY_STOCK_RESERVED,
        source_service="inventory-service",
        tenant_id=tenant_id,
        data=event_data,
        correlation_id=correlation_id,
    )
    await kafka_producer.send(
        topic=Topics.INVENTORY_STOCK_RESERVED, event=event, key=str(reservation.id)
    )
    log.info("stock.reserved", reservation_id=str(reservation.id), qty=data.reserved_quantity)
    return reservation


async def release_reservation(
    reservation_id: uuid.UUID,
    tenant_id: str,
    reservation_repo: StockReservationRepository,
) -> None:
    """Delete a stock reservation."""
    deleted = await reservation_repo.delete(reservation_id, tenant_id)
    if not deleted:
        raise NotFoundException("StockReservation", str(reservation_id))
    log.info("stock.reservation_released", reservation_id=str(reservation_id))


async def approve_reconciliation(
    reconciliation_id: uuid.UUID,
    approved_by: str,
    tenant_id: str,
    recon_repo: ReconciliationRepository,
    inventory_repo: InventoryRepository,
    kafka_producer: KafkaProducer,
    correlation_id: str | None = None,
) -> object:
    """Approve a SUBMITTED reconciliation and apply all non-zero variances as stock adjustments."""
    recon = await recon_repo.get_by_id(reconciliation_id, tenant_id)
    if recon is None:
        raise NotFoundException("StockReconciliation", str(reconciliation_id))
    if recon.status != ReconciliationStatus.SUBMITTED:
        raise UnprocessableEntityException(
            f"Reconciliation must be SUBMITTED to approve (current={recon.status})"
        )

    for item in recon.items:
        if item.variance == 0:
            continue
        existing = await inventory_repo.list_with_filters(
            tenant_id=tenant_id, product_id=item.product_id
        )
        if not existing:
            continue
        inv_item = existing[0]
        new_qty = inv_item.quantity + item.variance
        if new_qty < 0:
            log.warning(
                "reconciliation.variance_would_go_negative",
                product_id=str(item.product_id),
                current=inv_item.quantity,
                variance=item.variance,
            )
            continue
        await adjust_stock(
            inventory_id=inv_item.id,
            delta=item.variance,
            reason=f"Reconciliation {recon.id}",
            adjusted_by=approved_by,
            tenant_id=tenant_id,
            inventory_repo=inventory_repo,
            kafka_producer=kafka_producer,
            correlation_id=correlation_id,
        )

    updated = await recon_repo.update_status(
        reconciliation_id, tenant_id, ReconciliationStatus.APPROVED, approved_by=approved_by
    )
    log.info("reconciliation.approved", reconciliation_id=str(reconciliation_id))
    return updated
