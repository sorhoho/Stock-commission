"""Starts the Kafka consumer loop for sell-out events."""

from __future__ import annotations

import structlog

from app.config import settings
from app.infrastructure.db.session import async_session_factory
from app.infrastructure.kafka.consumers.sell_out_consumer import handle_sell_out_completed
from telco_common.events import Topics
from telco_common.kafka import KafkaConsumer, KafkaProducer

logger = structlog.get_logger(__name__)

_producer: KafkaProducer | None = None


async def start_consumer() -> None:
    global _producer
    _producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await _producer.start()

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="commission-calculation-service",
        topics=[Topics.SALES_SELLOUT_COMPLETED],
    )
    await consumer.start()
    logger.info("Commission calculation consumer started")

    async def handler(event: dict) -> None:
        async with async_session_factory() as session:
            try:
                await handle_sell_out_completed(
                    event=event,
                    session=session,
                    kafka_producer=_producer,
                    rules_service_url=settings.commission_rules_service_url,
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    await consumer.consume(handler, dlq_producer=_producer)
