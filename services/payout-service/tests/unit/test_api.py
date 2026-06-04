"""Unit tests for payout-service API handler functions."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.models import PayoutRequest, PayoutRequestCreate
from app.infrastructure.db.models import PayoutRequest as PayoutRequestORM
from telco_common.auth.jwt_bearer import TokenPayload
from telco_common.exceptions import NotFoundException

pytestmark = pytest.mark.asyncio

TENANT = "tenant-test-001"
PARTY = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
STMT = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _fake_token(tenant_id: str = TENANT) -> TokenPayload:
    return TokenPayload(sub="tester", tenant_id=tenant_id, scope="payout:admin")


def _make_orm(
    *,
    id: uuid.UUID | None = None,
    tenant_id: str = TENANT,
    status: str = "PENDING",
    party_id: uuid.UUID | None = None,
) -> PayoutRequestORM:
    orm = PayoutRequestORM(
        id=id or uuid.uuid4(),
        party_id=party_id or PARTY,
        statement_id=STMT,
        amount=100.0,
        currency="USD",
        payment_method="BANK_TRANSFER",
        bank_account_ref="****1234",
        status=status,
        scheduled_date=date(2026, 1, 28),
        tenant_id=tenant_id,
    )
    orm.created_at = datetime.now(UTC)
    orm.updated_at = datetime.now(UTC)
    return orm


def _make_pydantic(**kwargs) -> PayoutRequest:
    defaults = dict(
        id=uuid.uuid4(),
        party_id=PARTY,
        statement_id=STMT,
        amount=100.0,
        currency="USD",
        payment_method="BANK_TRANSFER",
        bank_account_ref="****1234",
        status="PENDING",
        scheduled_date=date(2026, 1, 28),
        tenant_id=TENANT,
    )
    defaults.update(kwargs)
    return PayoutRequest(**defaults)


# ── list_payout_requests ──────────────────────────────────────────────────────


async def test_list_payout_requests_empty():
    from app.api.v1.payout_request import list_payout_requests

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.payout_request.PayoutRequestRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = []
        MockRepo.return_value = instance

        result = await list_payout_requests(party_id=None, status=None, db=mock_db, token=token)

    assert result == []
    instance.list_with_filters.assert_awaited_once_with(TENANT, party_id=None, status=None)


async def test_list_payout_requests_with_filters():
    from app.api.v1.payout_request import list_payout_requests

    orm = _make_orm()
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.payout_request.PayoutRequestRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = [orm]
        MockRepo.return_value = instance

        result = await list_payout_requests(party_id=PARTY, status="PENDING", db=mock_db, token=token)

    assert len(result) == 1
    kwargs = instance.list_with_filters.call_args.kwargs
    assert kwargs["party_id"] == str(PARTY)
    assert kwargs["status"] == "PENDING"


# ── create_request ────────────────────────────────────────────────────────────


async def test_create_request_delegates_to_service():
    from app.api.v1.payout_request import create_request

    orm = _make_orm(id=uuid.uuid4())
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    token = _fake_token()

    data = PayoutRequestCreate(
        party_id=PARTY,
        statement_id=STMT,
        amount=200.0,
        currency="USD",
        payment_method="BANK_TRANSFER",
        bank_account_ref="12345678",
        scheduled_date=date(2026, 1, 28),
        tenant_id=TENANT,
    )

    with patch("app.api.v1.payout_request.create_payout_request", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = orm
        result = await create_request(data=data, db=mock_db, kafka_producer=mock_kafka, _token=token)

    mock_svc.assert_awaited_once()
    kwargs = mock_svc.call_args.kwargs
    assert kwargs["party_id"] == str(PARTY)
    assert kwargs["amount"] == 200.0


# ── get_request ───────────────────────────────────────────────────────────────


async def test_get_request_found():
    from app.api.v1.payout_request import get_request

    rid = uuid.uuid4()
    orm = _make_orm(id=rid)
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.payout_request.PayoutRequestRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = orm
        MockRepo.return_value = instance

        result = await get_request(request_id=rid, db=mock_db, _token=token)

    assert result.id == rid
    instance.get_by_id.assert_awaited_once_with(str(rid))


async def test_get_request_not_found():
    from app.api.v1.payout_request import get_request

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.payout_request.PayoutRequestRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_request(request_id=uuid.uuid4(), db=mock_db, _token=token)


# ── process_request ───────────────────────────────────────────────────────────


async def test_process_request_delegates_to_service():
    from app.api.v1.payout_request import process_request

    rid = uuid.uuid4()
    orm = _make_orm(id=rid, status="COMPLETED")
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.payout_request.process_payout", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = orm
        result = await process_request(request_id=rid, db=mock_db, kafka_producer=mock_kafka, token=token)

    mock_svc.assert_awaited_once()
    args = mock_svc.call_args[0]
    assert args[0] == str(rid)
    assert args[1] == TENANT


async def test_process_request_calls_correct_args():
    from app.api.v1.payout_request import process_request

    rid = uuid.uuid4()
    orm = _make_orm(id=rid)
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.payout_request.PayoutRequestRepository") as MockRepo, \
         patch("app.api.v1.payout_request.process_payout", new_callable=AsyncMock) as mock_svc:
        instance = AsyncMock()
        MockRepo.return_value = instance
        mock_svc.return_value = orm

        await process_request(request_id=rid, db=mock_db, kafka_producer=mock_kafka, token=token)

    call_args = mock_svc.call_args
    assert call_args[0][0] == str(rid)
    assert call_args[0][1] == TENANT


# ── get_receipt ───────────────────────────────────────────────────────────────


async def test_get_receipt_found():
    from app.api.v1.payout_request import get_receipt

    rid = uuid.uuid4()
    orm = _make_orm(id=rid, status="COMPLETED")
    orm.processed_date = datetime.now(UTC)
    orm.external_reference = "EXT-123"
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.payout_request.PayoutRequestRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = orm
        MockRepo.return_value = instance

        result = await get_receipt(request_id=rid, db=mock_db, _token=token)

    assert result["payout_id"] == str(rid)
    assert result["amount"] == 100.0
    assert result["status"] == "COMPLETED"
    assert result["external_reference"] == "EXT-123"
    assert "receipt_number" in result


async def test_get_receipt_not_found():
    from app.api.v1.payout_request import get_receipt

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.payout_request.PayoutRequestRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_receipt(request_id=uuid.uuid4(), db=mock_db, _token=token)


# ── scheduler ─────────────────────────────────────────────────────────────────


def test_scheduler_creates_with_job():
    from app.domain.scheduler import create_scheduler

    async def _noop():
        pass

    scheduler = create_scheduler(_noop, "0 1 1 * *")
    assert scheduler is not None
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "monthly_payout_cycle"


# ── router ────────────────────────────────────────────────────────────────────


def test_router_import():
    from app.api.v1.router import router
    assert router.prefix == "/api/v1/payout"


# ── dependencies ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_kafka_producer_returns_value():
    from app.dependencies import get_kafka_producer, set_kafka_producer

    mock_producer = MagicMock()
    set_kafka_producer(mock_producer)
    result = await get_kafka_producer()
    assert result is mock_producer
    set_kafka_producer(None)  # cleanup


@pytest.mark.asyncio
async def test_get_kafka_producer_raises_when_none():
    from app.dependencies import get_kafka_producer, set_kafka_producer

    set_kafka_producer(None)
    with pytest.raises(RuntimeError):
        await get_kafka_producer()


@pytest.mark.asyncio
async def test_get_db_commit_path():
    from unittest.mock import AsyncMock, patch
    from app.dependencies import get_db

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.dependencies.async_session_factory", return_value=mock_ctx):
        gen = get_db()
        await gen.__anext__()
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_rollback_on_exception():
    from unittest.mock import AsyncMock, patch
    from app.dependencies import get_db

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.dependencies.async_session_factory", return_value=mock_ctx):
        gen = get_db()
        await gen.__anext__()
        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("db error"))

    mock_session.rollback.assert_awaited_once()
