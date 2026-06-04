"""Unit tests for PayoutRequestRepository against in-memory SQLite."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.infrastructure.db.models import PayoutRequest as PayoutRequestORM
from app.infrastructure.db.repository import PayoutRequestRepository

pytestmark = pytest.mark.asyncio


def _make_orm(
    *,
    tenant_id: str = "tenant-1",
    party_id: uuid.UUID | None = None,
    statement_id: uuid.UUID | None = None,
    amount: float = 100.0,
    status: str = "PENDING",
) -> PayoutRequestORM:
    return PayoutRequestORM(
        party_id=party_id or uuid.uuid4(),
        statement_id=statement_id or uuid.uuid4(),
        amount=amount,
        currency="USD",
        payment_method="BANK_TRANSFER",
        bank_account_ref="****1234",
        status=status,
        scheduled_date=date(2026, 1, 28),
        tenant_id=tenant_id,
    )


async def test_create_assigns_id_and_persists(db_session):
    repo = PayoutRequestRepository(db_session)
    orm = _make_orm()
    created = await repo.create(orm)

    assert created.id is not None
    fetched = await repo.get_by_id(str(created.id))
    assert fetched is not None
    assert fetched.amount == 100.0
    assert fetched.status == "PENDING"


async def test_get_by_id_missing_returns_none(db_session):
    repo = PayoutRequestRepository(db_session)
    assert await repo.get_by_id(str(uuid.uuid4())) is None


async def test_list_with_filters_tenant_isolation(db_session):
    repo = PayoutRequestRepository(db_session)
    await repo.create(_make_orm(tenant_id="tenant-A"))
    await repo.create(_make_orm(tenant_id="tenant-A"))
    await repo.create(_make_orm(tenant_id="tenant-B"))
    await db_session.flush()

    a_items = await repo.list_with_filters("tenant-A")
    b_items = await repo.list_with_filters("tenant-B")

    assert len(a_items) == 2
    assert len(b_items) == 1
    assert all(i.tenant_id == "tenant-A" for i in a_items)


async def test_list_with_filters_by_party_id(db_session):
    repo = PayoutRequestRepository(db_session)
    party = uuid.uuid4()
    await repo.create(_make_orm(tenant_id="t1", party_id=party))
    await repo.create(_make_orm(tenant_id="t1", party_id=uuid.uuid4()))
    await db_session.flush()

    items = await repo.list_with_filters("t1", party_id=str(party))
    assert len(items) == 1
    assert items[0].party_id == party


async def test_list_with_filters_by_status(db_session):
    repo = PayoutRequestRepository(db_session)
    await repo.create(_make_orm(tenant_id="t1", status="PENDING"))
    await repo.create(_make_orm(tenant_id="t1", status="COMPLETED"))
    await db_session.flush()

    completed = await repo.list_with_filters("t1", status="COMPLETED")
    assert len(completed) == 1
    assert completed[0].status == "COMPLETED"


async def test_list_with_filters_empty(db_session):
    repo = PayoutRequestRepository(db_session)
    assert await repo.list_with_filters("nobody") == []


async def test_update_status_transition(db_session):
    repo = PayoutRequestRepository(db_session)
    created = await repo.create(_make_orm(status="PENDING"))
    await db_session.flush()
    request_id = str(created.id)  # capture before expire_all triggers lazy load

    await repo.update_status(request_id, "COMPLETED", "EXT-REF-123")
    await db_session.flush()
    db_session.expire_all()

    refreshed = await repo.get_by_id(request_id)
    assert refreshed.status == "COMPLETED"
    assert refreshed.external_reference == "EXT-REF-123"


async def test_update_status_without_external_ref(db_session):
    repo = PayoutRequestRepository(db_session)
    created = await repo.create(_make_orm(status="PENDING"))
    await db_session.flush()
    request_id = str(created.id)  # capture before expire_all triggers lazy load

    await repo.update_status(request_id, "PROCESSING")
    await db_session.flush()
    db_session.expire_all()

    refreshed = await repo.get_by_id(request_id)
    assert refreshed.status == "PROCESSING"
    assert refreshed.external_reference is None
