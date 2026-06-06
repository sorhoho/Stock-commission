"""Kafka consumer for telco.sales.sellout.completed events.

On each sell-out event:
1. Deducts sold quantities from inventory at the dealer's location.
2. Marks any matching Resource (IMEI/serial) records as SOLD.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from telco_common.events.cloudevents import Topics
from telco_common.events.schemas.sales_events import SellOutCompletedData
from telco_common.kafka.consumer_factory import KafkaConsumer
from telco_common.kafka.producer_factory import KafkaProducer

log = structlog.get_logger(__name__)


async def _handle_sell_out_event(
    event: dict[str, Any],
    kafka_producer: KafkaProducer,
) -> None:
    from app.infrastructure.db.session import AsyncSessionLocal
    from app.infrastructure.db.repository import InventoryRepository, ResourceRepository
    from app.domain.models import ResourceStatusType

    raw_data = event.get("data", {})
    data = SellOutCompletedData.model_validate(raw_data)
    tenant_id = data.tenant_id

    async with AsyncSessionLocal() as session:
        inventory_repo = InventoryRepository(session)
        resource_repo = ResourceRepository(session)

        for item in data.items:
            product_id = uuid.UUID(item.product_id)
            qty = item.quantity

            # Find inventory records for this product (across all locations for the tenant)
            # In a real system, dealer_location_id would be looked up from party-service;
            # here we deduct from the first available inventory record for the product.
            inv_items = await inventory_repo.list_with_filters(
                tenant_id=tenant_id,
                product_id=product_id,
            )
            if not inv_items:
                log.warning(
                    "sell_out.no_inventory",
                    product_id=str(product_id),
                    transaction_id=data.transaction_id,
                )
                continue

            inv_item = inv_items[0]
            new_qty = inv_item.quantity - qty
            if new_qty < 0:
                log.warning(
                    "sell_out.insufficient_stock",
                    inventory_id=str(inv_item.id),
                    available=inv_item.quantity,
                    sold=qty,
                )
                new_qty = 0

            delta = new_qty - inv_item.quantity
            if delta != 0:
                from app.domain.services import adjust_stock
                await adjust_stock(
                    inventory_id=inv_item.id,
                    delta=delta,
                    reason=f"Sell-out deduction: {data.transaction_number}",
                    adjusted_by=data.dealer_party_id,
                    tenant_id=tenant_id,
                    inventory_repo=inventory_repo,
                    kafka_producer=kafka_producer,
                    correlation_id=event.get("correlationid"),
                )

            # Mark matching serial/IMEI resources as SOLD
            for serial in item.serial_numbers:
                resources = await resource_repo.list_with_filters(
                    tenant_id=tenant_id,
                    characteristic_name="IMEI",
                    characteristic_value=serial,
                )
                if not resources:
                    resources = await resource_repo.list_with_filters(
                        tenant_id=tenant_id,
                        characteristic_name="SERIAL",
                        characteristic_value=serial,
                    )
                for r in resources:
                    await resource_repo.update_status(
                        r.id, tenant_id, ResourceStatusType.SOLD,
                        allocated_to=data.transaction_id,
                    )

        await session.commit()

    log.info(
        "sell_out.inventory_deducted",
        transaction_id=data.transaction_id,
        item_count=len(data.items),
    )


async def start_consumer(
    bootstrap_servers: str,
    group_id: str,
    kafka_producer: KafkaProducer,
) -> None:
    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        topics=[Topics.SALES_SELLOUT_COMPLETED],
    )
    await consumer.start()
    log.info("inventory.sell_out_consumer.started", topic=Topics.SALES_SELLOUT_COMPLETED)

    async def handler(event: dict[str, Any]) -> None:
        await _handle_sell_out_event(event, kafka_producer)

    try:
        await consumer.consume(handler=handler, dlq_producer=kafka_producer)
    finally:
        await consumer.stop()
        log.info("inventory.sell_out_consumer.stopped")
