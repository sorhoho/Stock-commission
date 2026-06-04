"""Unit tests for the audit Kafka consumer handler.

``handle_any_event`` turns an arbitrary incoming CloudEvent (the audit service
subscribes to *every* domain topic) into one immutable ``audit_log`` row.

Two complementary strategies are used, mirroring the patterns requested:

* ``test_*_persists_*`` — drive the handler against a real in-memory SQLite
  session and assert the persisted row's fields. This catches real ORM/column
  mismatches, not just mock interactions.
* ``test_*_repo_mock_*`` — autospec the ``AuditLogRepository`` so the handler's
  call into ``repo.insert(entry)`` is enforced against the real repository
  signature; a drift in the repo API fails the test instead of production.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import func, select

from app.infrastructure.db.models import AuditLog
from app.infrastructure.kafka.consumers import audit_consumer
from app.infrastructure.kafka.consumers.audit_consumer import handle_any_event


# ---------------------------------------------------------------------------
# Representative CloudEvents for a few of the topics the audit service consumes.
# ---------------------------------------------------------------------------
def _sellout_completed_event() -> dict:
    return {
        "id": "evt-sellout-1",
        "type": "telco.sales.sellout.completed",
        "source": "sell-out-service",
        "tenantid": "tenant-test-001",
        "correlationid": "corr-abc",
        "time": "2026-01-15T10:00:00+00:00",
        "data": {
            "transaction_id": "11111111-1111-1111-1111-111111111111",
            "total_amount": 100.0,
            "currency": "USD",
        },
    }


def _stock_transferred_event() -> dict:
    return {
        "id": "evt-transfer-1",
        "type": "telco.inventory.stock.transferred",
        "source": "inventory-service",
        "tenantid": "tenant-test-001",
        "correlationid": "corr-def",
        "time": "2026-02-01T08:30:00+00:00",
        "data": {
            "product_id": "33333333-3333-3333-3333-333333333333",
            "from_location": "WH-1",
            "to_location": "WH-2",
            "quantity": 25,
        },
    }


def _dealer_onboarded_event() -> dict:
    return {
        "id": "evt-dealer-1",
        "type": "telco.party.dealer.onboarded",
        "source": "party-service",
        "tenantid": "tenant-other-999",
        "correlationid": "corr-ghi",
        "time": "2026-03-10T12:00:00+00:00",
        "data": {"dealer_id": "44444444-4444-4444-4444-444444444444", "name": "Dealer A"},
    }


# ---------------------------------------------------------------------------
# In-memory SQLite: assert real persisted rows.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "event_factory",
    [_sellout_completed_event, _stock_transferred_event, _dealer_onboarded_event],
    ids=["sellout_completed", "stock_transferred", "dealer_onboarded"],
)
async def test_handle_event_persists_row_with_correct_fields(db_session, event_factory):
    event = event_factory()
    await handle_any_event(event, db_session)
    await db_session.commit()

    row = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.event_id == event["id"])
        )
    ).scalar_one()

    assert row.event_id == event["id"]
    assert row.event_type == event["type"]
    assert row.event_source == event["source"]
    assert row.tenant_id == event["tenantid"]
    assert row.correlation_id == event["correlationid"]
    assert row.event_time == event["time"]
    # The *entire* CloudEvent is stored as the immutable payload.
    assert row.payload == event
    assert row.payload["data"] == event["data"]


async def test_handle_event_is_idempotent_on_redelivery(db_session):
    """Kafka at-least-once delivery: the same event_id must yield one row."""
    event = _sellout_completed_event()
    await handle_any_event(event, db_session)
    await db_session.commit()

    # Redeliver the identical event.
    await handle_any_event(event, db_session)
    await db_session.commit()

    count = (
        await db_session.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.event_id == event["id"])
        )
    ).scalar_one()
    assert count == 1


async def test_handle_event_with_missing_optional_fields_uses_defaults(db_session):
    """A sparse event (no id/type/source/tenant/time) must still produce a row.

    The handler defaults: type/source -> "unknown", tenant/correlation -> "",
    event_id -> a generated uuid, event_time -> now(UTC).
    """
    sparse = {"data": {"something": True}}
    await handle_any_event(sparse, db_session)
    await db_session.commit()

    rows = (await db_session.execute(select(AuditLog))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.event_type == "unknown"
    assert row.event_source == "unknown"
    assert row.tenant_id == ""
    assert row.correlation_id == ""
    # event_id was generated and is a valid uuid string.
    uuid.UUID(row.event_id)
    # event_time defaulted to an ISO timestamp string.
    assert isinstance(row.event_time, str) and "T" in row.event_time
    assert row.payload == sparse


async def test_handle_event_preserves_tenant_for_isolation(db_session):
    """Different events carry their own tenant; the row tenant must match the event."""
    await handle_any_event(_sellout_completed_event(), db_session)  # tenant-test-001
    await handle_any_event(_dealer_onboarded_event(), db_session)  # tenant-other-999
    await db_session.commit()

    rows = {
        r.event_id: r.tenant_id
        for r in (await db_session.execute(select(AuditLog))).scalars().all()
    }
    assert rows["evt-sellout-1"] == "tenant-test-001"
    assert rows["evt-dealer-1"] == "tenant-other-999"


# ---------------------------------------------------------------------------
# Autospec repository mock: enforce the handler -> repo call contract.
# ---------------------------------------------------------------------------
async def test_handle_event_calls_repo_insert_with_audit_log_entry():
    """Autospec AuditLogRepository so repo.insert's signature is enforced.

    A regression that changes the repo's insert signature (or how the handler
    calls it) fails here instead of crashing at runtime.
    """
    event = _sellout_completed_event()
    fake_session = MagicMock()

    with patch.object(audit_consumer, "AuditLogRepository", autospec=True) as repo_cls:
        repo_inst = repo_cls.return_value
        repo_inst.insert = AsyncMock()

        await handle_any_event(event, fake_session)

        # Repo constructed with the session that was passed in.
        repo_cls.assert_called_once_with(fake_session)
        repo_inst.insert.assert_awaited_once()

        (entry,) = repo_inst.insert.await_args.args
        assert isinstance(entry, AuditLog)
        assert entry.event_id == event["id"]
        assert entry.event_type == event["type"]
        assert entry.event_source == event["source"]
        assert entry.tenant_id == event["tenantid"]
        assert entry.correlation_id == event["correlationid"]
        assert entry.event_time == event["time"]
        assert entry.payload == event
