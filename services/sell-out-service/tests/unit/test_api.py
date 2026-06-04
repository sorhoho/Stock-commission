"""Unit tests for sell-out-service API handler functions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.models import (
    SaleChannel,
    SaleStatus,
    SaleTransaction,
    SaleTransactionCreate,
    SaleTransactionItem,
    SaleTransactionItemCreate,
    SaleTransactionSummary,
    SaleTransactionUpdate,
)
from telco_common.exceptions import NotFoundException

pytestmark = pytest.mark.asyncio

TENANT = "tenant-test-001"
DEALER = uuid.uuid4()
PRODUCT = uuid.uuid4()


def _make_transaction(**overrides) -> SaleTransaction:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        transaction_number="TXN-20260101-ABCD1234",
        dealer_party_id=DEALER,
        customer_party_id=None,
        channel=SaleChannel.RETAIL,
        items=[
            SaleTransactionItem(
                id=uuid.uuid4(),
                product_id=PRODUCT,
                product_name="SIM",
                quantity=5,
                unit_price=10.0,
                discount_amount=0.0,
                serial_numbers=[],
                commission_eligible=True,
            )
        ],
        total_amount=50.0,
        currency="USD",
        status=SaleStatus.COMPLETED,
        tenant_id=TENANT,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return SaleTransaction(**defaults)


def _make_create() -> SaleTransactionCreate:
    return SaleTransactionCreate(
        dealer_party_id=DEALER,
        channel=SaleChannel.RETAIL,
        items=[
            SaleTransactionItemCreate(
                product_id=PRODUCT,
                product_name="SIM",
                quantity=5,
                unit_price=10.0,
            )
        ],
    )


# ── create_transaction ────────────────────────────────────────────────────────


async def test_create_transaction_delegates_to_service():
    from app.api.v1.sale_transaction import create_transaction

    txn = _make_transaction()
    mock_repo = AsyncMock()
    mock_kafka = AsyncMock()

    with patch("app.api.v1.sale_transaction.create_sale_transaction", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = txn
        result = await create_transaction(
            body=_make_create(),
            tenant_id=TENANT,
            correlation_id="corr-1",
            repo=mock_repo,
            kafka_producer=mock_kafka,
        )

    assert result.id == txn.id
    mock_svc.assert_awaited_once()
    kwargs = mock_svc.call_args.kwargs
    assert kwargs["tenant_id"] == TENANT


async def test_create_transaction_passes_all_kwargs():
    from app.api.v1.sale_transaction import create_transaction

    txn = _make_transaction()
    mock_repo = AsyncMock()
    mock_kafka = AsyncMock()
    body = _make_create()

    with patch("app.api.v1.sale_transaction.create_sale_transaction", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = txn
        await create_transaction(
            body=body,
            tenant_id=TENANT,
            correlation_id="corr-2",
            repo=mock_repo,
            kafka_producer=mock_kafka,
        )

    kwargs = mock_svc.call_args.kwargs
    assert kwargs["data"] is body
    assert kwargs["repo"] is mock_repo
    assert kwargs["kafka_producer"] is mock_kafka


# ── list_transactions ─────────────────────────────────────────────────────────


async def test_list_transactions_empty():
    from app.api.v1.sale_transaction import list_transactions

    mock_repo = AsyncMock()
    mock_repo.list_with_filters.return_value = ([], 0)

    result = await list_transactions(
        tenant_id=TENANT, repo=mock_repo,
        dealer_party_id=None, from_date=None, to_date=None,
        sale_status=None, page=1, size=20,
    )

    assert result["total"] == 0
    assert result["items"] == []
    assert result["page"] == 1


async def test_list_transactions_with_filters():
    from app.api.v1.sale_transaction import list_transactions

    txn = _make_transaction()
    mock_repo = AsyncMock()
    mock_repo.list_with_filters.return_value = ([txn], 1)

    result = await list_transactions(
        tenant_id=TENANT, repo=mock_repo,
        dealer_party_id=DEALER, from_date=None, to_date=None,
        sale_status=SaleStatus.COMPLETED, page=1, size=20,
    )

    assert result["total"] == 1
    assert len(result["items"]) == 1
    kwargs = mock_repo.list_with_filters.call_args.kwargs
    assert kwargs["dealer_party_id"] == DEALER
    assert kwargs["status"] == SaleStatus.COMPLETED
    assert kwargs["tenant_id"] == TENANT


async def test_list_transactions_pagination():
    from app.api.v1.sale_transaction import list_transactions

    mock_repo = AsyncMock()
    mock_repo.list_with_filters.return_value = ([], 45)

    result = await list_transactions(
        tenant_id=TENANT, repo=mock_repo,
        dealer_party_id=None, from_date=None, to_date=None,
        sale_status=None, page=3, size=20,
    )

    assert result["pages"] == 3  # ceil(45/20)


# ── get_summary ───────────────────────────────────────────────────────────────


async def test_get_summary_delegates_to_repo():
    from app.api.v1.sale_transaction import get_summary

    summary = SaleTransactionSummary(
        dealer_party_id=DEALER,
        period="2026-01",
        total_transactions=10,
        total_units=50,
        total_amount=500.0,
        currency="USD",
    )
    mock_repo = AsyncMock()
    mock_repo.get_summary.return_value = summary

    result = await get_summary(
        tenant_id=TENANT, repo=mock_repo,
        dealer_party_id=DEALER, period="2026-01",
    )

    assert result.dealer_party_id == DEALER
    assert result.total_transactions == 10
    mock_repo.get_summary.assert_awaited_once_with(
        dealer_party_id=DEALER, period="2026-01", tenant_id=TENANT,
    )


# ── get_transaction ───────────────────────────────────────────────────────────


async def test_get_transaction_found():
    from app.api.v1.sale_transaction import get_transaction

    txn = _make_transaction()
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = txn

    result = await get_transaction(
        transaction_id=txn.id, tenant_id=TENANT, repo=mock_repo,
    )

    assert result.id == txn.id
    mock_repo.get_by_id.assert_awaited_once_with(txn.id, TENANT)


async def test_get_transaction_not_found():
    from app.api.v1.sale_transaction import get_transaction

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await get_transaction(
            transaction_id=uuid.uuid4(), tenant_id=TENANT, repo=mock_repo,
        )


# ── update_transaction ────────────────────────────────────────────────────────


async def test_update_transaction_reversal_path():
    from app.api.v1.sale_transaction import update_transaction

    txn_id = uuid.uuid4()
    reversed_txn = _make_transaction(id=txn_id, status=SaleStatus.REVERSED)
    mock_repo = AsyncMock()
    mock_kafka = AsyncMock()
    body = SaleTransactionUpdate(status=SaleStatus.REVERSED, reversal_reason="Error")

    with patch("app.api.v1.sale_transaction.reverse_transaction", new_callable=AsyncMock) as mock_rev:
        mock_rev.return_value = reversed_txn
        result = await update_transaction(
            transaction_id=txn_id, body=body,
            tenant_id=TENANT, repo=mock_repo, kafka_producer=mock_kafka,
        )

    assert result.status == SaleStatus.REVERSED
    mock_rev.assert_awaited_once_with(
        transaction_id=str(txn_id),
        reason="Error",
        tenant_id=TENANT,
        repo=mock_repo,
        kafka_producer=mock_kafka,
    )


async def test_update_transaction_status_update():
    from app.api.v1.sale_transaction import update_transaction

    txn_id = uuid.uuid4()
    updated = _make_transaction(id=txn_id, status=SaleStatus.COMPLETED)
    mock_repo = AsyncMock()
    mock_repo.update_status.return_value = updated
    mock_kafka = AsyncMock()
    body = SaleTransactionUpdate(status=SaleStatus.COMPLETED)

    result = await update_transaction(
        transaction_id=txn_id, body=body,
        tenant_id=TENANT, repo=mock_repo, kafka_producer=mock_kafka,
    )

    assert result.status == SaleStatus.COMPLETED
    mock_repo.update_status.assert_awaited_once_with(txn_id, SaleStatus.COMPLETED, TENANT)


async def test_update_transaction_status_not_found():
    from app.api.v1.sale_transaction import update_transaction

    mock_repo = AsyncMock()
    mock_repo.update_status.return_value = None
    mock_kafka = AsyncMock()
    body = SaleTransactionUpdate(status=SaleStatus.COMPLETED)

    with pytest.raises(NotFoundException):
        await update_transaction(
            transaction_id=uuid.uuid4(), body=body,
            tenant_id=TENANT, repo=mock_repo, kafka_producer=mock_kafka,
        )


async def test_update_transaction_no_status_returns_existing():
    from app.api.v1.sale_transaction import update_transaction

    txn = _make_transaction()
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = txn
    mock_kafka = AsyncMock()
    body = SaleTransactionUpdate()  # no status, no-op

    result = await update_transaction(
        transaction_id=txn.id, body=body,
        tenant_id=TENANT, repo=mock_repo, kafka_producer=mock_kafka,
    )

    assert result.id == txn.id
    mock_repo.get_by_id.assert_awaited_once_with(txn.id, TENANT)


async def test_update_transaction_no_status_not_found():
    from app.api.v1.sale_transaction import update_transaction

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = None
    mock_kafka = AsyncMock()
    body = SaleTransactionUpdate()

    with pytest.raises(NotFoundException):
        await update_transaction(
            transaction_id=uuid.uuid4(), body=body,
            tenant_id=TENANT, repo=mock_repo, kafka_producer=mock_kafka,
        )


# ── dependencies.py ───────────────────────────────────────────────────────────


def test_get_kafka_producer_returns_app_state():
    from app.dependencies import get_kafka_producer

    fake_producer = object()
    request = MagicMock()
    request.app.state.kafka_producer = fake_producer

    assert get_kafka_producer(request) is fake_producer


def test_get_repo_returns_repository_bound_to_session():
    from app.dependencies import get_repo
    from app.infrastructure.db.repository import SaleTransactionRepository
    from unittest.mock import MagicMock

    mock_session = MagicMock()
    repo = get_repo(mock_session)

    assert isinstance(repo, SaleTransactionRepository)
    assert repo._session is mock_session


def test_get_tenant_id_reads_request_state():
    from app.dependencies import get_tenant_id

    request = MagicMock()
    request.state.tenant_id = "my-tenant"

    assert get_tenant_id(request) == "my-tenant"


def test_get_correlation_id_reads_request_state():
    from app.dependencies import get_correlation_id

    request = MagicMock()
    request.state.correlation_id = "corr-123"

    assert get_correlation_id(request) == "corr-123"


def test_get_correlation_id_missing_returns_empty_string():
    from app.dependencies import get_correlation_id

    request = MagicMock(spec=[])  # no attributes at all
    request.state = MagicMock(spec=[])  # no correlation_id attribute

    assert get_correlation_id(request) == ""


# ── session.py (get_db_session) ───────────────────────────────────────────────


async def test_get_db_session_commits_on_success():
    """get_db_session should commit the session when no exception occurs."""
    from app.infrastructure.db.session import get_db_session

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.infrastructure.db.session.AsyncSessionFactory", return_value=mock_ctx):
        gen = get_db_session()
        session = await gen.__anext__()
        assert session is mock_session
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


async def test_get_db_session_rolls_back_on_exception():
    """get_db_session should rollback and re-raise when an exception occurs."""
    from app.infrastructure.db.session import get_db_session

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.infrastructure.db.session.AsyncSessionFactory", return_value=mock_ctx):
        gen = get_db_session()
        await gen.__anext__()
        with pytest.raises(ValueError, match="boom"):
            await gen.athrow(ValueError("boom"))

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
