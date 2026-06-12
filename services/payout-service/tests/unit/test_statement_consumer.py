"""Tests for the commission.statement.confirmed consumer handler.

Uses an autospec mock repository (so create() call signatures are enforced)
and a mocked producer. Asserts a payout request is created from the confirmed
statement with correct fields, and that invalid events are skipped.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.db.repository import PayoutRequestRepository
from app.infrastructure.kafka.consumers import statement_consumer as consumer

pytestmark = pytest.mark.asyncio


def _event(**overrides) -> dict:
    data = {
        "statement_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "party_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "period_year": 2026,
        "period_month": 5,
        "total_commission": 543.21,
        "currency": "THB",
        "confirmed_at": "2026-05-15T10:00:00+00:00",
        "tenant_id": "tenant-test-001",
    }
    data.update(overrides)
    return {"tenantid": "tenant-test-001", "data": data}


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=PayoutRequestRepository)


async def test_confirmed_statement_creates_payout(repo, mock_kafka_producer):
    repo.create.side_effect = lambda orm: orm

    await consumer.handle_statement_confirmed(_event(), repo, mock_kafka_producer)

    repo.create.assert_awaited_once()
    orm = repo.create.await_args.args[0]
    assert str(orm.party_id) == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert str(orm.statement_id) == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert orm.amount == 543.21
    assert orm.currency == "THB"
    assert orm.payment_method == "BANK_TRANSFER"
    assert orm.status == "PENDING"
    # scheduled to the 28th of the statement period.
    assert orm.scheduled_date == date(2026, 5, 28)

    mock_kafka_producer.send.assert_awaited_once()


async def test_scheduled_date_derived_from_period(repo, mock_kafka_producer):
    repo.create.side_effect = lambda orm: orm
    await consumer.handle_statement_confirmed(
        _event(period_year=2025, period_month=12), repo, mock_kafka_producer
    )
    orm = repo.create.await_args.args[0]
    assert orm.scheduled_date == date(2025, 12, 28)


async def test_invalid_event_is_skipped(repo, mock_kafka_producer):
    # Missing required fields -> validation fails -> handler returns early.
    bad = {"data": {"party_id": "x"}}
    await consumer.handle_statement_confirmed(bad, repo, mock_kafka_producer)

    repo.create.assert_not_awaited()
    mock_kafka_producer.send.assert_not_awaited()


async def test_invalid_period_month_skipped(repo, mock_kafka_producer):
    # date(2026, 13, 28) raises ValueError inside the handler; nothing persisted.
    repo.create.side_effect = lambda orm: orm
    with pytest.raises(ValueError):
        await consumer.handle_statement_confirmed(
            _event(period_month=13), repo, mock_kafka_producer
        )
    repo.create.assert_not_awaited()
