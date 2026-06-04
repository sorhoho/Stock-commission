"""Pytest fixtures for commission-rules-service unit tests.

Mirrors the inventory-service pattern (in-memory SQLite + dependency_overrides)
and the sell-out-service pattern (bypassing auth for API tests).

Two auth styles are exercised:
  * Most endpoints use ``require_auth`` (JWT).  Because the routes capture the
    result of ``require_auth([...])`` at import time, we cannot reliably build a
    matching override key after the fact.  Instead we patch ``require_auth`` to a
    no-op dependency factory *before* the API modules are imported, so every
    route picks up a stub that injects a fake ``TokenPayload``.
  * The internal endpoint ``GET /agreement/party/{id}/active`` authenticates via
    the ``X-Tenant-ID`` header (``get_current_tenant_id`` -> ``request.state``),
    which is populated by the real ``TenantMiddleware``.  Those tests simply send
    the header.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

# ---------------------------------------------------------------------------
# SQLite compatibility shims for Postgres-specific column types.
#
# The ORM models use the postgres dialect ``JSONB`` and ``UUID`` types.  The
# in-memory SQLite engine used for unit tests cannot render those, so we teach
# the SQLite compiler to emit portable equivalents (TEXT-backed JSON / CHAR(36)
# for UUIDs).  This only affects DDL/value binding under SQLite — production
# Postgres behaviour is untouched.
# ---------------------------------------------------------------------------


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):  # pragma: no cover - DDL hook
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):  # pragma: no cover - DDL hook
    return "CHAR(36)"


# The postgres ``UUID`` bind processor assumes it always receives ``uuid.UUID``
# instances and calls ``value.hex``.  Application code (and FastAPI path params)
# legitimately pass UUID *strings* to the repositories, which works fine on real
# Postgres via asyncpg but blows up under SQLite.  Teach the SQLite dialect to
# store/return UUIDs as plain strings and to accept either form on the way in.
import json as _json  # noqa: E402

from sqlalchemy import String as _String  # noqa: E402
from sqlalchemy.types import TypeDecorator  # noqa: E402


class _SqliteUUID(TypeDecorator):
    impl = _String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(str(value))


class _SqliteJSON(TypeDecorator):
    impl = _String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        return _json.loads(value)


# Register the SQLite-only implementations on the postgres types so they take
# effect only when the active dialect is SQLite.
UUID.__visit_name__  # noqa: B018 - ensure imported symbol used
from sqlalchemy.dialects.sqlite.base import SQLiteDialect  # noqa: E402

_orig_colspecs = dict(SQLiteDialect.colspecs)
_orig_colspecs[UUID] = _SqliteUUID
_orig_colspecs[JSONB] = _SqliteJSON
SQLiteDialect.colspecs = _orig_colspecs

# ---------------------------------------------------------------------------
# Patch require_auth BEFORE importing the app / API routers.
# ---------------------------------------------------------------------------
import telco_common.auth.jwt_bearer as _jwt
from telco_common.auth.jwt_bearer import TokenPayload

TEST_TENANT_ID = "tenant-test-001"


def _stub_require_auth(required_scopes=None):
    """Replacement for require_auth: returns a dependency yielding a fake token."""

    async def _dep() -> TokenPayload:
        return TokenPayload(
            sub="test-user",
            tenant_id=TEST_TENANT_ID,
            preferred_username="tester",
            scope=" ".join(required_scopes or []),
        )

    return _dep


_jwt.require_auth = _stub_require_auth
# telco_common.auth re-exports it; patch there too in case of `from ... import`.
import telco_common.auth as _auth_pkg  # noqa: E402

_auth_pkg.require_auth = _stub_require_auth

# Now safe to import application modules (they call require_auth at import time).
from app.dependencies import get_db  # noqa: E402
from app.infrastructure.db.models import (  # noqa: E402
    Agreement as AgreementORM,
    AgreementSpec as AgreementSpecORM,
    CommissionRule as CommissionRuleORM,
)
from telco_common.db.base import Base  # noqa: E402

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Database fixtures
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
def tenant_id() -> str:
    return TEST_TENANT_ID


# ---------------------------------------------------------------------------
# ID fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def spec_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def party_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


# ---------------------------------------------------------------------------
# ORM object factories (persisted via fixtures where useful)
# ---------------------------------------------------------------------------

def make_spec_orm(tenant_id: str, **overrides) -> AgreementSpecORM:
    data = dict(
        name="Standard Dealer Scheme",
        version="1.0",
        description="Default commission scheme",
        applicable_party_roles=["DEALER"],
        effective_from=date(2024, 1, 1),
        effective_to=None,
        tenant_id=tenant_id,
    )
    data.update(overrides)
    return AgreementSpecORM(**data)


def make_agreement_orm(spec_id, party_id, tenant_id: str, **overrides) -> AgreementORM:
    data = dict(
        agreement_spec_id=spec_id,
        party_id=party_id,
        party_name="Acme Dealer",
        status="ACTIVE",
        signed_date=date(2024, 1, 15),
        tenant_id=tenant_id,
    )
    data.update(overrides)
    return AgreementORM(**data)


def make_rule_orm(spec_id, tenant_id: str, **overrides) -> CommissionRuleORM:
    data = dict(
        agreement_spec_id=spec_id,
        product_category="SIM",
        channel_type="RETAIL",
        tier_min_qty=0,
        tier_max_qty=None,
        commission_type="FLAT_AMOUNT",
        commission_value=5.0,
        currency="USD",
        conditions={},
        priority=100,
        tenant_id=tenant_id,
    )
    data.update(overrides)
    return CommissionRuleORM(**data)


# ---------------------------------------------------------------------------
# HTTP client fixture (shares the test db_session)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session):
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async def _override_get_db():
        # The endpoints rely on get_db committing; the test session commits fine
        # against SQLite. Reuse the single shared session so data persists.
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
