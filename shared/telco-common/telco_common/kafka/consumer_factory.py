"""aiokafka consumer factory with DLQ support and at-least-once processing."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class KafkaConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        dlq_topic_prefix: str = "telco.dlq",
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._topics = topics
        self._dlq_topic_prefix = dlq_topic_prefix
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await self._consumer.start()
        logger.info("Kafka consumer started", extra={"group_id": self._group_id, "topics": self._topics})

    async def stop(self) -> None:
        if self._consumer:
            await self._consumer.stop()

    async def consume(
        self,
        handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
        dlq_producer: Any | None = None,
    ) -> None:
        if self._consumer is None:
            raise RuntimeError("Consumer not started")

        async for msg in self._consumer:
            event = msg.value
            event_id = event.get("id", "unknown")
            attempt = 0
            while attempt < MAX_RETRIES:
                try:
                    await handler(event)
                    await self._consumer.commit()
                    break
                except Exception as exc:
                    attempt += 1
                    logger.warning(
                        "Handler failed, attempt %d/%d",
                        attempt,
                        MAX_RETRIES,
                        extra={"event_id": event_id, "error": str(exc)},
                    )
                    if attempt >= MAX_RETRIES:
                        logger.error(
                            "Max retries exceeded, routing to DLQ",
                            extra={"event_id": event_id, "topic": msg.topic},
                        )
                        if dlq_producer:
                            dlq_topic = f"{self._dlq_topic_prefix}.{self._group_id}.{msg.topic}"
                            await dlq_producer.send(dlq_topic, event)
                        await self._consumer.commit()
                    else:
                        await asyncio.sleep(2**attempt)
