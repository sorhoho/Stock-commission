"""Pytest fixtures for inventory-service tests."""

from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import get_db, get_current_tenant_id, get_kafka_producer
from app.main import create_app
from telco_common.db.base import Base
from telco_common.kafka.producer_factory import KafkaProducer

# ---------------------------------------------------------------------------
# In-memory SQLite engine for unit tests (no real Postgres required)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session


@pytest.fixture
def mock_kafka_producer() -> AsyncMock:
    """Return a fully mocked KafkaProducer."""
    producer = AsyncMock(spec=KafkaProducer)
    producer.send = AsyncMock(return_value=None)
    return producer


@pytest.fixture
def sample_tenant_id() -> str:
    return "tenant-test-001"


@pytest.fixture
def sample_product_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def sample_location_id() -> uuid.UUID:
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def sample_dest_location_id() -> uuid.UUID:
    return uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session, mock_kafka_producer, sample_tenant_id) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with overridden dependencies."""
    app = create_app()

    # Override DB dependency
    async def _override_get_db():
        yield db_session

    def _override_tenant_id():
        return sample_tenant_id

    async def _override_kafka():
        return mock_kafka_producer

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_tenant_id] = _override_tenant_id
    app.dependency_overrides[get_kafka_producer] = _override_kafka

    # Set kafka_producer on app state so lifespan-dependent code is satisfied
    app.state.kafka_producer = mock_kafka_producer

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
