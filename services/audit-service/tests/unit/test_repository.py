"""Unit tests for AuditLogRepository against in-memory SQLite.

Covers the append (insert) path and the read query path with filters:
by event_type, tenant isolation, idempotent inserts, and pagination.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.infrastructure.db.models import AuditLog
from app.infrastructure.db.repository import AuditLogRepository


async def test_insert_persists_all_fields(db_session, make_audit_log):
    repo = AuditLogRepository(db_session)
    entry = make_audit_log(
        event_id="evt-100",
        event_type="telco.sales.sellout.completed",
        event_source="sell-out-service",
        tenant_id="tenant-a",
        correlation_id="corr-xyz",
        event_time="2026-01-15T10:00:00+00:00",
        payload={"data": {"amount": 100}, "type": "telco.sales.sellout.completed"},
    )
    await repo.insert(entry)
    await db_session.commit()

    row = (
        await db_session.execute(select(AuditLog).where(AuditLog.event_id == "evt-100"))
    ).scalar_one()
    assert row.event_id == "evt-100"
    assert row.event_type == "telco.sales.sellout.completed"
    assert row.event_source == "sell-out-service"
    assert row.tenant_id == "tenant-a"
    assert row.correlation_id == "corr-xyz"
    assert row.event_time == "2026-01-15T10:00:00+00:00"
    assert row.payload == {"data": {"amount": 100}, "type": "telco.sales.sellout.completed"}
    # received_at is populated by the DB server default.
    assert row.received_at is not None


async def test_insert_is_idempotent_on_duplicate_event_id(db_session, make_audit_log):
    """on_conflict_do_nothing means a re-delivered event must not create a second row."""
    repo = AuditLogRepository(db_session)
    first = make_audit_log(event_id="evt-dup", tenant_id="tenant-a", payload={"v": 1})
    await repo.insert(first)
    await db_session.commit()

    # Re-deliver same event_id with a different payload — should be ignored.
    second = make_audit_log(event_id="evt-dup", tenant_id="tenant-a", payload={"v": 2})
    await repo.insert(second)
    await db_session.commit()

    rows = (
        await db_session.execute(select(AuditLog).where(AuditLog.event_id == "evt-dup"))
    ).scalars().all()
    assert len(rows) == 1
    # The original row wins (DO NOTHING), payload is unchanged.
    assert rows[0].payload == {"v": 1}


async def test_query_returns_only_matching_tenant(db_session, make_audit_log):
    """Tenant isolation: a tenant must never see another tenant's audit rows."""
    repo = AuditLogRepository(db_session)
    await repo.insert(make_audit_log(event_id="a1", tenant_id="tenant-a"))
    await repo.insert(make_audit_log(event_id="a2", tenant_id="tenant-a"))
    await repo.insert(make_audit_log(event_id="b1", tenant_id="tenant-b"))
    await db_session.commit()

    items, total = await repo.query("tenant-a")
    assert total == 2
    assert {i.event_id for i in items} == {"a1", "a2"}
    assert all(i.tenant_id == "tenant-a" for i in items)

    items_b, total_b = await repo.query("tenant-b")
    assert total_b == 1
    assert items_b[0].event_id == "b1"


async def test_query_filters_by_event_type(db_session, make_audit_log):
    repo = AuditLogRepository(db_session)
    await repo.insert(
        make_audit_log(event_id="s1", tenant_id="t", event_type="telco.sales.sellout.completed")
    )
    await repo.insert(
        make_audit_log(event_id="s2", tenant_id="t", event_type="telco.sales.sellout.completed")
    )
    await repo.insert(
        make_audit_log(event_id="i1", tenant_id="t", event_type="telco.inventory.stock.adjusted")
    )
    await db_session.commit()

    items, total = await repo.query("t", event_type="telco.inventory.stock.adjusted")
    assert total == 1
    assert items[0].event_id == "i1"

    items2, total2 = await repo.query("t", event_type="telco.sales.sellout.completed")
    assert total2 == 2
    assert {i.event_id for i in items2} == {"s1", "s2"}


async def test_query_unknown_event_type_returns_empty(db_session, make_audit_log):
    repo = AuditLogRepository(db_session)
    await repo.insert(make_audit_log(event_id="x1", tenant_id="t", event_type="known"))
    await db_session.commit()

    items, total = await repo.query("t", event_type="does-not-exist")
    assert total == 0
    assert items == []


async def test_query_pagination(db_session, make_audit_log):
    repo = AuditLogRepository(db_session)
    for n in range(5):
        await repo.insert(make_audit_log(event_id=f"p{n}", tenant_id="t"))
    await db_session.commit()

    page1, total = await repo.query("t", page=1, size=2)
    page2, _ = await repo.query("t", page=2, size=2)
    page3, _ = await repo.query("t", page=3, size=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
    # No overlap across pages.
    seen = {i.event_id for i in page1} | {i.event_id for i in page2} | {i.event_id for i in page3}
    assert len(seen) == 5


async def test_query_empty_tenant(db_session):
    repo = AuditLogRepository(db_session)
    items, total = await repo.query("nobody")
    assert items == []
    assert total == 0


async def test_query_accepts_date_range_args(db_session, make_audit_log):
    """from_date/to_date are accepted in the signature; exercise that they don't break the query.

    NOTE: see test_repository_bugs.py — these arguments are currently ignored by
    the repository implementation.
    """
    repo = AuditLogRepository(db_session)
    await repo.insert(make_audit_log(event_id="d1", tenant_id="t"))
    await db_session.commit()

    items, total = await repo.query(
        "t", from_date="2026-01-01", to_date="2026-12-31"
    )
    assert total == 1
    assert items[0].event_id == "d1"
