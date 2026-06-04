"""Unit tests for payout domain services (create_payout_request, process_payout).

Repositories are autospec-mocked so call signatures are enforced; the Kafka
producer is mocked and assertions check real event payload data.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain import services
from app.infrastructure.db.repository import PayoutRequestRepository

pytestmark = pytest.mark.asyncio

PARTY = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
STMT = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


@pytest.fixture
def repo() -> AsyncMock:
    r = AsyncMock(spec=PayoutRequestRepository)
    return r


async def test_create_payout_request_persists_and_publishes(repo, mock_kafka_producer):
    created_id = uuid.uuid4()

    async def _create(orm):
        orm.id = created_id
        return orm

    repo.create.side_effect = _create

    result = await services.create_payout_request(
        party_id=PARTY,
        statement_id=STMT,
        amount=123.45,
        currency="USD",
        payment_method="BANK_TRANSFER",
        bank_account_ref="9876543210",
        scheduled_date=date(2026, 1, 28),
        tenant_id="tenant-1",
        repo=repo,
        kafka_producer=mock_kafka_producer,
    )

    # Repo create called with a single ORM positional arg.
    repo.create.assert_awaited_once()
    orm_arg = repo.create.await_args.args[0]
    assert orm_arg.amount == 123.45
    assert orm_arg.party_id == uuid.UUID(PARTY)
    assert orm_arg.statement_id == uuid.UUID(STMT)
    assert orm_arg.status == "PENDING"
    # Bank account ref is masked to last 4 digits.
    assert orm_arg.bank_account_ref == "****3210"

    # Event published to the created topic with correct payload + party key.
    mock_kafka_producer.send.assert_awaited_once()
    topic, event = mock_kafka_producer.send.await_args.args
    key = mock_kafka_producer.send.await_args.kwargs["key"]
    assert key == PARTY
    assert event["data"]["payout_request_id"] == str(created_id)
    assert event["data"]["amount"] == 123.45
    assert event["data"]["scheduled_date"] == "2026-01-28"
    assert result is orm_arg


async def test_create_payout_request_masks_short_ref(repo, mock_kafka_producer):
    repo.create.side_effect = lambda orm: orm
    await services.create_payout_request(
        party_id=PARTY,
        statement_id=STMT,
        amount=10.0,
        currency="USD",
        payment_method="WALLET",
        bank_account_ref="12",
        scheduled_date=date(2026, 1, 28),
        tenant_id="tenant-1",
        repo=repo,
        kafka_producer=mock_kafka_producer,
    )
    orm_arg = repo.create.await_args.args[0]
    assert orm_arg.bank_account_ref == "****"


async def test_process_payout_success_path(repo, mock_kafka_producer):
    pid = str(uuid.uuid4())
    record = MagicMock()
    record.party_id = uuid.UUID(PARTY)
    record.amount = 200.0
    record.currency = "USD"
    repo.get_by_id.return_value = record

    with patch.object(services.random, "random", return_value=0.99):
        await services.process_payout(pid, "tenant-1", repo, mock_kafka_producer)

    repo.update_status.assert_awaited_once()
    args = repo.update_status.await_args.args
    assert args[0] == pid
    assert args[1] == "COMPLETED"
    assert args[2].startswith("MOCK-")

    mock_kafka_producer.send.assert_awaited_once()
    _, event = mock_kafka_producer.send.await_args.args
    assert event["data"]["party_id"] == PARTY
    assert event["data"]["amount"] == 200.0
    assert event["data"]["external_reference"] == args[2]


async def test_process_payout_failure_path(repo, mock_kafka_producer):
    pid = str(uuid.uuid4())
    record = MagicMock()
    record.party_id = uuid.UUID(PARTY)
    record.amount = 200.0
    record.currency = "USD"
    repo.get_by_id.return_value = record

    with patch.object(services.random, "random", return_value=0.01):
        await services.process_payout(pid, "tenant-1", repo, mock_kafka_producer)

    assert repo.update_status.await_args.args[1] == "FAILED"


async def test_process_payout_not_found_raises(repo, mock_kafka_producer):
    from telco_common.exceptions import NotFoundException

    repo.get_by_id.return_value = None
    with pytest.raises(NotFoundException):
        await services.process_payout(str(uuid.uuid4()), "tenant-1", repo, mock_kafka_producer)

    repo.update_status.assert_not_awaited()
    mock_kafka_producer.send.assert_not_awaited()
