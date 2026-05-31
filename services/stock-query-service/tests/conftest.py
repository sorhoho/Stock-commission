"""Shared pytest fixtures for stock-query-service tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

# fakeredis provides an in-memory async Redis implementation
try:
    import fakeredis.aioredis as fakeredis_aioredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

from app.infrastructure.cache.stock_read_model import StockReadModel


@pytest_asyncio.fixture()
async def fake_redis():
    """Return an in-memory async Redis client (fakeredis)."""
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")
    server = fakeredis_aioredis.FakeRedis(decode_responses=True)
    yield server
    await server.aclose()


@pytest_asyncio.fixture()
async def stock_read_model(fake_redis):
    """Return a StockReadModel backed by fakeredis."""
    return StockReadModel(redis_client=fake_redis, key_ttl=3600)
