"""Kafka consumer for SALES_SELLIN_DELIVERED events.

When a sell-in order is marked delivered, auto-creates a GoodsReceipt in inventory-service
for each delivered item, triggering stock receipt at the destination location.
"""

from __future__ import annotations

import structlog
from typing import Any

import httpx

from telco_common.events.cloudevents import Topics
from telco_common.events.schemas.sales_events import SellInDeliveredData
from telco_common.kafka.consumer_factory import KafkaConsumer
from telco_common.kafka.producer_factory import KafkaProducer

log = structlog.get_logger(__name__)


async def _handle_sellin_delivered(
    event: dict[str, Any],
    inventory_service_url: str,
) -> None:
    raw_data = event.get("data", {})
    data = SellInDeliveredData.model_validate(raw_data)
    tenant_id = data.tenant_id

    async with httpx.AsyncClient(timeout=10.0) as client:
        for item in data.delivered_items:
            payload = {
                "grn_number": f"GRN-{data.order_number}-{item.get('product_id', 'UNKNOWN')[:8]}",
                "supplier_reference": data.order_id,
                "product_id": item.get("product_id"),
                "location_id": data.destination_location_id,
                "quantity_received": item.get("quantity", 0),
                "received_by": "system",
                "received_date": data.delivered_at,
            }
            try:
                resp = await client.post(
                    f"{inventory_service_url}/api/v1/goodsReceipt/",
                    json=payload,
                    headers={"X-Tenant-ID": tenant_id, "X-Correlation-ID": event.get("correlationid", "")},
                )
                resp.raise_for_status()
                log.info(
                    "sellin.grn_created",
                    order_id=data.order_id,
                    product_id=item.get("product_id"),
                    quantity=item.get("quantity"),
                )
            except httpx.HTTPError as exc:
                log.error("sellin.grn_creation_failed", error=str(exc), order_id=data.order_id)
                raise


async def start_consumer(
    bootstrap_servers: str,
    group_id: str,
    kafka_producer: KafkaProducer,
    inventory_service_url: str,
) -> None:
    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        topics=[Topics.SALES_SELLIN_DELIVERED],
    )
    await consumer.start()
    log.info("sellin_consumer.started", topic=Topics.SALES_SELLIN_DELIVERED)

    async def handler(event: dict[str, Any]) -> None:
        await _handle_sellin_delivered(event, inventory_service_url)

    try:
        await consumer.consume(handler=handler, dlq_producer=kafka_producer)
    finally:
        await consumer.stop()
        log.info("sellin_consumer.stopped")
