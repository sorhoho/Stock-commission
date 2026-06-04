"""Pytest fixtures for audit-service tests.

Mirrors inventory-service/tests/conftest.py: in-memory SQLite + FastAPI
dependency_overrides for repository and API tests.

audit-service models use the PostgreSQL ``JSONB`` type for ``payload``. SQLite
has no native JSONB, so we register a compilation rule that renders it as plain
JSON for the SQLite dialect *only in tests*. This touches no application code.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles


# ---------------------------------------------------------------------------
# SQLite compatibility shim for the PostgreSQL JSONB column type.
# ---------------------------------------------------------------------------
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):  # pragma: no cover - DDL hook
    return compiler.visit_JSON(JSON(), **kw)


from app.infrastructure.db.models import AuditLog  # noqa: E402
from telco_common.db.base import Base  # noqa: E402


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# In-memory SQLite engine / session
# ---------------------------------------------------------------------------
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
def sample_tenant_id() -> str:
    return "tenant-test-001"


@pytest.fixture
def other_tenant_id() -> str:
    return "tenant-other-999"


# ---------------------------------------------------------------------------
# Factory for building AuditLog ORM rows in tests.
# ---------------------------------------------------------------------------
@pytest.fixture
def make_audit_log():
    def _make(
        *,
        event_id: str | None = None,
        event_type: str = "telco.sales.sellout.completed",
        event_source: str = "sell-out-service",
        tenant_id: str = "tenant-test-001",
        correlation_id: str = "corr-1",
        event_time: str = "2026-01-15T10:00:00+00:00",
        payload: dict | None = None,
        received_at: datetime | None = None,
    ) -> AuditLog:
        kwargs = dict(
            id=uuid.uuid4(),
            event_id=event_id or f"evt-{uuid.uuid4()}",
            event_type=event_type,
            event_source=event_source,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            event_time=event_time,
            payload=payload if payload is not None else {"foo": "bar"},
        )
        if received_at is not None:
            kwargs["received_at"] = received_at
        return AuditLog(**kwargs)

    return _make


# ---------------------------------------------------------------------------
# Async HTTP client with overridden auth + DB dependencies.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def async_client(db_session, sample_tenant_id):
    from httpx import ASGITransport, AsyncClient

    from app.api.v1.audit_log import router as audit_router
    from app.dependencies import get_db
    from app.main import app
    from telco_common.auth.jwt_bearer import TokenPayload

    async def _override_get_db():
        yield db_session

    def _make_token():
        return TokenPayload(sub="user-1", tenant_id=sample_tenant_id, scope="audit:read")

    # require_auth([...]) is evaluated once at import time, producing a single
    # dependency object stored on the route. Grab that exact object so the
    # override matches by identity (FastAPI keys overrides by object identity).
    auth_dep = None
    for route in audit_router.routes:
        for dep in route.dependant.dependencies:
            if dep.call.__qualname__.startswith("require_auth"):
                auth_dep = dep.call
                break

    app.dependency_overrides[get_db] = _override_get_db
    if auth_dep is not None:
        app.dependency_overrides[auth_dep] = _make_token

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
