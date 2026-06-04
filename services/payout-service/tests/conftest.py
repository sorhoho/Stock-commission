"""Shared pytest fixtures for payout-service unit tests.

Mirrors inventory-service's in-memory SQLite + dependency_overrides pattern.
The payout-service exposes a module-level ``app`` (no ``create_app`` factory),
so the API fixtures override dependencies on that singleton and clean up after.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from telco_common.auth.jwt_bearer import TokenPayload
from telco_common.db.base import Base

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
    producer = AsyncMock()
    producer.send = AsyncMock(return_value=None)
    return producer


@pytest.fixture
def sample_tenant_id() -> str:
    return "tenant-test-001"


@pytest.fixture
def sample_party_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def sample_statement_id() -> uuid.UUID:
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def sample_scheduled_date() -> date:
    return date(2026, 1, 28)


def _collect_auth_dependencies(app) -> set:
    """Find the `require_auth` `_dependency` callables wired into routes.

    `require_auth([...])` returns a fresh closure per route, so the only way to
    override it is to grab the exact callable FastAPI stored on each route's
    dependant tree.
    """
    deps: set = set()

    def _walk(dependant):
        for sub in dependant.dependencies:
            if getattr(sub.call, "__qualname__", "").startswith("require_auth"):
                deps.add(sub.call)
            _walk(sub)

    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is not None:
            _walk(dependant)
    return deps


@pytest_asyncio.fixture(scope="function")
async def async_client(
    db_session, mock_kafka_producer, sample_tenant_id
) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with overridden DB, kafka, and auth dependencies."""
    from app.dependencies import get_db, get_kafka_producer
    from app.main import app

    async def _override_get_db():
        yield db_session

    def _override_kafka():
        return mock_kafka_producer

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_kafka_producer] = _override_kafka

    fake_token = TokenPayload(
        sub="test-user",
        tenant_id=sample_tenant_id,
        scope="payout:admin payout:create",
    )
    for auth_dep in _collect_auth_dependencies(app):
        app.dependency_overrides[auth_dep] = lambda: fake_token

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
