"""Kafka consumer for inventory events — feeds the Redis stock read model.

Subscribes to:
  - telco.inventory.stock.adjusted
  - telco.inventory.stock.transferred

All offsets are committed only after successful model update (at-least-once).
Failed messages are routed to DLQ after MAX_RETRIES via KafkaConsumer base.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import structlog

from telco_common.events.cloudevents import Topics
from telco_common.kafka.consumer_factory import KafkaConsumer

from app.infrastructure.cache.stock_read_model import StockReadModel

logger = structlog.get_logger(__name__)


class InventoryConsumer:
    """Wraps KafkaConsumer and routes inventory events to the Redis read model.

    Exposes ``run()`` so callers can start it as an ``asyncio.create_task``.
    ``stop()`` must be called during application shutdown to cleanly close the
    underlying aiokafka consumer.
    """

    TOPICS = [
        Topics.INVENTORY_STOCK_ADJUSTED,
        Topics.INVENTORY_STOCK_TRANSFERRED,
    ]

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        read_model: StockReadModel,
    ) -> None:
        self._read_model = read_model
        self._consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            topics=self.TOPICS,
        )
        self._started = False

    async def stop(self) -> None:
        await self._consumer.stop()
        logger.info("InventoryConsumer stopped")

    async def run(self) -> None:
        """Start the consumer then enter the consume loop (background-task entry point)."""
        await self._consumer.start()
        self._started = True
        logger.info("InventoryConsumer started", topics=self.TOPICS)
        await self._consumer.consume(handler=self._dispatch)

    # ------------------------------------------------------------------
    # Internal routing
    # ------------------------------------------------------------------

    async def _dispatch(self, event: dict[str, Any]) -> None:
        event_type: str = event.get("type", "")
        data: dict[str, Any] = event.get("data", {})
        event_id: str = event.get("id", "unknown")
        tenant_id: str = event.get("tenantid", "")

        # Inject tenant_id into data if not already present (from envelope)
        if tenant_id and "tenant_id" not in data:
            data = {**data, "tenant_id": tenant_id}

        log = logger.bind(event_id=event_id, event_type=event_type, tenant_id=tenant_id)

        if event_type == Topics.INVENTORY_STOCK_ADJUSTED:
            log.debug("Routing to update_from_adjustment")
            await self._read_model.update_from_adjustment(data)

        elif event_type == Topics.INVENTORY_STOCK_TRANSFERRED:
            log.debug("Routing to update_from_transfer")
            await self._read_model.update_from_transfer(data)

        else:
            log.warning("Received unknown event type — skipping")
