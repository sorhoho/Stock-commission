"""Multi-topic consumer routing events to notification handlers."""

from __future__ import annotations

import structlog

from app.config import settings
from app.domain.notification_handlers import (
    handle_commission_statement_confirmed,
    handle_dealer_onboarded,
    handle_payout_completed,
    handle_stock_transfer_completed,
)
from telco_common.events import Topics
from telco_common.kafka import KafkaConsumer

logger = structlog.get_logger(__name__)

TOPIC_HANDLERS = {
    Topics.PARTY_DEALER_ONBOARDED: handle_dealer_onboarded,
    Topics.PAYOUT_REQUEST_COMPLETED: handle_payout_completed,
    Topics.COMMISSION_STATEMENT_CONFIRMED: handle_commission_statement_confirmed,
    Topics.INVENTORY_STOCK_TRANSFERRED: handle_stock_transfer_completed,
}

NOTIFICATION_TOPICS = list(TOPIC_HANDLERS.keys())


async def start_notification_consumer() -> None:
    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="notification-service",
        topics=NOTIFICATION_TOPICS,
    )
    await consumer.start()
    logger.info("Notification consumer started", topics=NOTIFICATION_TOPICS)

    async def handler(event: dict) -> None:
        event_type = event.get("type", "")
        handle_fn = TOPIC_HANDLERS.get(event_type)
        if handle_fn:
            await handle_fn(event)
        else:
            logger.debug("No handler for event type", event_type=event_type)

    await consumer.consume(handler)
