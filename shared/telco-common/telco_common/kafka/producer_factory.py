"""aiokafka producer factory with retry and CloudEvents serialisation."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            enable_idempotence=True,
            acks="all",
            compression_type="gzip",
        )
        await self._producer.start()
        logger.info("Kafka producer started", extra={"servers": self._bootstrap_servers})

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def send(
        self,
        topic: str,
        event: dict[str, Any],
        key: str | None = None,
    ) -> None:
        if self._producer is None:
            raise RuntimeError("Producer not started")
        await self._producer.send_and_wait(topic, value=event, key=key)
        logger.info("Event sent", extra={"topic": topic, "event_id": event.get("id")})
