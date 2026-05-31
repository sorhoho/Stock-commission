from __future__ import annotations
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.session import async_session_factory
from telco_common.kafka import KafkaProducer

_producer: KafkaProducer | None = None


def set_kafka_producer(p: KafkaProducer) -> None:
    global _producer
    _producer = p


async def get_kafka_producer() -> KafkaProducer:
    if _producer is None:
        raise RuntimeError("Kafka producer not initialised")
    return _producer


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
