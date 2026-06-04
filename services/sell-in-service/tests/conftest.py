"""Shared pytest fixtures for sell-in-service tests.

Mirrors the in-memory SQLite + dependency_overrides pattern used by
inventory-service, adapted to the sell-in-service (TMF622 product ordering)
which exposes a module-level FastAPI ``app`` rather than a ``create_app`` factory.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.router import router
from app.dependencies import get_current_tenant_id, get_db, get_kafka_producer
from app.domain.models import ProductOrderCreate, ProductOrderItemCreate
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


# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_tenant_id() -> str:
    return "tenant-test-001"


@pytest.fixture
def other_tenant_id() -> str:
    return "tenant-test-002"


@pytest.fixture
def requestor_party_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def supplier_party_id() -> uuid.UUID:
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def product_id() -> uuid.UUID:
    return uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


@pytest.fixture
def sample_item_create(product_id: uuid.UUID) -> ProductOrderItemCreate:
    return ProductOrderItemCreate(
        product_id=product_id,
        product_name="Router X100",
        quantity=10,
        unit_price=25.50,
    )


@pytest.fixture
def sample_order_create(
    requestor_party_id: uuid.UUID,
    supplier_party_id: uuid.UUID,
    sample_item_create: ProductOrderItemCreate,
) -> ProductOrderCreate:
    return ProductOrderCreate(
        requestor_party_id=requestor_party_id,
        supplier_party_id=supplier_party_id,
        items=[sample_item_create],
        requested_delivery_date=date(2026, 7, 1),
        notes="Urgent restock",
    )


@pytest.fixture
def mock_kafka_producer() -> AsyncMock:
    """Return a fully mocked KafkaProducer."""
    producer = AsyncMock(spec=KafkaProducer)
    producer.send = AsyncMock(return_value=None)
    return producer


# ---------------------------------------------------------------------------
# HTTP test client (async) with overridden dependencies
# ---------------------------------------------------------------------------


def _build_test_app() -> FastAPI:
    """Build a minimal FastAPI app wired to the real router.

    We avoid importing the module-level ``app`` so that the production
    lifespan (which touches the real Postgres engine and Kafka) never runs.
    The router and dependency wiring are the real production objects.
    """
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest_asyncio.fixture(scope="function")
async def async_client(
    db_session: AsyncSession,
    mock_kafka_producer: AsyncMock,
    sample_tenant_id: str,
) -> AsyncGenerator[AsyncClient, None]:
    app = _build_test_app()

    async def _override_get_db():
        yield db_session

    def _override_tenant_id():
        return sample_tenant_id

    async def _override_kafka():
        return mock_kafka_producer

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_tenant_id] = _override_tenant_id
    app.dependency_overrides[get_kafka_producer] = _override_kafka

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
