"""Shared pytest fixtures for sell-out-service tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.models import (
    SaleChannel,
    SaleStatus,
    SaleTransaction,
    SaleTransactionCreate,
    SaleTransactionItem,
    SaleTransactionItemCreate,
)


# ─── Domain fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-001"


@pytest.fixture
def correlation_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def dealer_party_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def sample_item_create() -> SaleTransactionItemCreate:
    return SaleTransactionItemCreate(
        product_id=uuid.uuid4(),
        product_name="SIM Card Premium",
        quantity=5,
        unit_price=10.00,
        discount_amount=1.00,
        serial_numbers=["SN001", "SN002"],
        commission_eligible=True,
    )


@pytest.fixture
def sample_transaction_create(
    dealer_party_id: uuid.UUID,
    sample_item_create: SaleTransactionItemCreate,
) -> SaleTransactionCreate:
    return SaleTransactionCreate(
        dealer_party_id=dealer_party_id,
        customer_party_id=None,
        channel=SaleChannel.RETAIL,
        items=[sample_item_create],
        sale_date=datetime.now(UTC),
    )


@pytest.fixture
def sample_transaction(
    dealer_party_id: uuid.UUID,
    sample_item_create: SaleTransactionItemCreate,
    tenant_id: str,
) -> SaleTransaction:
    txn_id = uuid.uuid4()
    now = datetime.now(UTC)
    return SaleTransaction(
        id=txn_id,
        transaction_number="TXN-20240101-ABCD1234",
        dealer_party_id=dealer_party_id,
        customer_party_id=None,
        channel=SaleChannel.RETAIL,
        items=[
            SaleTransactionItem(
                id=uuid.uuid4(),
                product_id=sample_item_create.product_id,
                product_name=sample_item_create.product_name,
                quantity=sample_item_create.quantity,
                unit_price=sample_item_create.unit_price,
                discount_amount=sample_item_create.discount_amount,
                serial_numbers=sample_item_create.serial_numbers,
                commission_eligible=sample_item_create.commission_eligible,
            )
        ],
        total_amount=45.00,  # (10.00 - 1.00) * 5
        currency="USD",
        status=SaleStatus.COMPLETED,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )


# ─── Infrastructure mocks ─────────────────────────────────────────────────────

@pytest.fixture
def mock_kafka_producer() -> AsyncMock:
    producer = AsyncMock()
    producer.send = AsyncMock()
    return producer


@pytest.fixture
def mock_repo(sample_transaction: SaleTransaction) -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock(return_value=sample_transaction)
    repo.get_by_id = AsyncMock(return_value=sample_transaction)
    repo.list_with_filters = AsyncMock(return_value=([sample_transaction], 1))
    repo.update_status = AsyncMock(return_value=sample_transaction)
    repo.get_summary = AsyncMock()
    return repo


# ─── HTTP test client ─────────────────────────────────────────────────────────

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the FastAPI app with mocked dependencies."""
    from app.main import create_app
    from app.dependencies import (
        get_kafka_producer,
        get_repo,
        get_tenant_id,
        get_correlation_id,
    )

    test_app = create_app()

    # Override kafka producer and repo with mocks
    mock_producer = AsyncMock()
    mock_producer.send = AsyncMock()

    mock_repository = MagicMock()
    mock_repository.create = AsyncMock()
    mock_repository.get_by_id = AsyncMock()
    mock_repository.list_with_filters = AsyncMock(return_value=([], 0))
    mock_repository.update_status = AsyncMock()
    mock_repository.get_summary = AsyncMock()

    test_app.dependency_overrides[get_kafka_producer] = lambda: mock_producer
    test_app.dependency_overrides[get_repo] = lambda: mock_repository
    test_app.dependency_overrides[get_tenant_id] = lambda: "test-tenant-001"
    test_app.dependency_overrides[get_correlation_id] = lambda: str(uuid.uuid4())

    # Bypass JWT auth for integration tests
    from telco_common.auth.jwt_bearer import require_auth
    from telco_common.auth.scopes import Scopes

    for scope in [Scopes.SELL_OUT_CREATE, Scopes.SELL_OUT_READ, Scopes.SELL_OUT_REVERSE]:
        test_app.dependency_overrides[require_auth([scope])] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as client:
        yield client, mock_repository, mock_producer
