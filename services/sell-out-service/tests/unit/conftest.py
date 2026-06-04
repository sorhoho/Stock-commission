"""Unit-test fixtures — in-memory SQLite DB session.

The postgresql ARRAY type is not supported by SQLite, so we patch it to JSON
before importing any models that reference ARRAY.
"""

from __future__ import annotations

# ── Patch postgresql.ARRAY → JSON before any model import ────────────────────
from sqlalchemy import JSON
from sqlalchemy.dialects import postgresql as _pg

_pg.ARRAY = lambda *a, **kw: JSON()  # type: ignore[assignment]
# ─────────────────────────────────────────────────────────────────────────────

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from telco_common.db.base import Base

# Import models so they register with Base.metadata
import app.infrastructure.db.models  # noqa: F401

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


# ── Common value fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def sample_tenant_id() -> str:
    return "tenant-test-001"


@pytest.fixture
def other_tenant_id() -> str:
    return "tenant-test-002"


@pytest.fixture
def dealer_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def product_id() -> uuid.UUID:
    return uuid.UUID("11111111-2222-3333-4444-555555555555")
