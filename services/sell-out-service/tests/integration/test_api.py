"""Integration tests for sell-out-service API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.models import (
    SaleChannel,
    SaleStatus,
    SaleTransaction,
    SaleTransactionItem,
    SaleTransactionItemCreate,
)
from app.domain.services import create_sale_transaction


# ─── App fixture with all deps mocked ─────────────────────────────────────────

def _make_sample_transaction(
    dealer_party_id: uuid.UUID | None = None,
    status: SaleStatus = SaleStatus.COMPLETED,
) -> SaleTransaction:
    now = datetime.now(UTC)
    _dealer = dealer_party_id or uuid.uuid4()
    return SaleTransaction(
        id=uuid.uuid4(),
        transaction_number="TXN-20240301-ABCDEF12",
        dealer_party_id=_dealer,
        customer_party_id=None,
        channel=SaleChannel.RETAIL,
        items=[
            SaleTransactionItem(
                id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                product_name="SIM Premium",
                quantity=2,
                unit_price=25.00,
                discount_amount=0.00,
                serial_numbers=["SN-ALPHA"],
                commission_eligible=True,
            )
        ],
        total_amount=50.00,
        currency="USD",
        status=status,
        tenant_id="test-tenant-001",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_transaction() -> SaleTransaction:
    return _make_sample_transaction()


@pytest.fixture
async def test_client(sample_transaction: SaleTransaction):
    """
    Async HTTP client with all external dependencies overridden.
    Yields (client, mock_repo, mock_producer).
    """
    from app.main import create_app
    from app.dependencies import (
        get_kafka_producer,
        get_repo,
        get_tenant_id,
        get_correlation_id,
    )
    from telco_common.auth.jwt_bearer import require_auth
    from telco_common.auth.scopes import Scopes

    test_app = create_app()

    mock_producer = AsyncMock()
    mock_producer.send = AsyncMock()

    mock_repo = MagicMock()
    mock_repo.create = AsyncMock(return_value=sample_transaction)
    mock_repo.get_by_id = AsyncMock(return_value=sample_transaction)
    mock_repo.list_with_filters = AsyncMock(return_value=([sample_transaction], 1))
    mock_repo.update_status = AsyncMock(return_value=sample_transaction)
    mock_repo.get_summary = AsyncMock()

    # Override dependencies
    test_app.dependency_overrides[get_kafka_producer] = lambda: mock_producer
    test_app.dependency_overrides[get_repo] = lambda: mock_repo
    test_app.dependency_overrides[get_tenant_id] = lambda: "test-tenant-001"
    test_app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

    # Bypass JWT auth
    from fastapi import Depends
    for scope in [Scopes.SELL_OUT_CREATE, Scopes.SELL_OUT_READ, Scopes.SELL_OUT_REVERSE]:
        test_app.dependency_overrides[require_auth([scope])] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as client:
        yield client, mock_repo, mock_producer


# ─── POST /api/v1/salesManagement/saleTransaction ─────────────────────────────

class TestCreateSaleTransactionEndpoint:
    @pytest.mark.asyncio
    async def test_create_returns_201(
        self, test_client, sample_transaction: SaleTransaction
    ):
        """POST /saleTransaction returns 201 with the created transaction."""
        client, mock_repo, mock_producer = test_client
        payload = {
            "dealer_party_id": str(uuid.uuid4()),
            "channel": "RETAIL",
            "items": [
                {
                    "product_id": str(uuid.uuid4()),
                    "product_name": "SIM Card",
                    "quantity": 2,
                    "unit_price": 25.00,
                    "discount_amount": 0.00,
                    "serial_numbers": ["SN001"],
                    "commission_eligible": True,
                }
            ],
        }

        response = await client.post(
            "/api/v1/salesManagement/saleTransaction",
            json=payload,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(sample_transaction.id)
        assert data["transaction_number"] == sample_transaction.transaction_number
        assert data["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_create_calls_repo_and_kafka(
        self, test_client, sample_transaction: SaleTransaction
    ):
        """POST /saleTransaction triggers repo.create and kafka_producer.send."""
        client, mock_repo, mock_producer = test_client
        payload = {
            "dealer_party_id": str(uuid.uuid4()),
            "channel": "ONLINE",
            "items": [
                {
                    "product_id": str(uuid.uuid4()),
                    "product_name": "Data Bundle",
                    "quantity": 1,
                    "unit_price": 50.00,
                    "discount_amount": 5.00,
                }
            ],
        }

        await client.post(
            "/api/v1/salesManagement/saleTransaction",
            json=payload,
        )

        mock_repo.create.assert_awaited_once()
        mock_producer.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_rejects_empty_items(self, test_client):
        """POST /saleTransaction with empty items list returns 422."""
        client, _, _ = test_client
        payload = {
            "dealer_party_id": str(uuid.uuid4()),
            "channel": "RETAIL",
            "items": [],
        }

        response = await client.post(
            "/api/v1/salesManagement/saleTransaction",
            json=payload,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_rejects_invalid_quantity(self, test_client):
        """POST /saleTransaction with quantity=0 returns 422."""
        client, _, _ = test_client
        payload = {
            "dealer_party_id": str(uuid.uuid4()),
            "channel": "RETAIL",
            "items": [
                {
                    "product_id": str(uuid.uuid4()),
                    "product_name": "Test",
                    "quantity": 0,  # invalid: must be > 0
                    "unit_price": 10.00,
                }
            ],
        }

        response = await client.post(
            "/api/v1/salesManagement/saleTransaction",
            json=payload,
        )

        assert response.status_code == 422


# ─── GET /api/v1/salesManagement/saleTransaction/{id} ─────────────────────────

class TestGetSaleTransactionEndpoint:
    @pytest.mark.asyncio
    async def test_get_existing_transaction(
        self, test_client, sample_transaction: SaleTransaction
    ):
        """GET /saleTransaction/{id} returns 200 with correct transaction data."""
        client, mock_repo, _ = test_client

        response = await client.get(
            f"/api/v1/salesManagement/saleTransaction/{sample_transaction.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_transaction.id)
        assert data["channel"] == "RETAIL"
        assert data["total_amount"] == 50.00
        assert data["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_get_nonexistent_transaction_returns_404(self, test_client):
        """GET /saleTransaction/{id} for unknown ID returns 404."""
        client, mock_repo, _ = test_client
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = await client.get(
            f"/api/v1/salesManagement/saleTransaction/{uuid.uuid4()}"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_returns_items_list(
        self, test_client, sample_transaction: SaleTransaction
    ):
        """GET /saleTransaction/{id} response includes the items array."""
        client, _, _ = test_client

        response = await client.get(
            f"/api/v1/salesManagement/saleTransaction/{sample_transaction.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == len(sample_transaction.items)
        first_item = data["items"][0]
        assert first_item["product_name"] == "SIM Premium"
        assert first_item["quantity"] == 2

    @pytest.mark.asyncio
    async def test_get_invalid_uuid_returns_422(self, test_client):
        """GET /saleTransaction/not-a-uuid returns 422."""
        client, _, _ = test_client

        response = await client.get(
            "/api/v1/salesManagement/saleTransaction/not-a-uuid"
        )

        assert response.status_code == 422


# ─── GET /api/v1/salesManagement/saleTransaction (list) ──────────────────────

class TestListSaleTransactionsEndpoint:
    @pytest.mark.asyncio
    async def test_list_returns_paginated_response(
        self, test_client, sample_transaction: SaleTransaction
    ):
        """GET /saleTransaction returns paginated response with total."""
        client, mock_repo, _ = test_client
        mock_repo.list_with_filters = AsyncMock(
            return_value=([sample_transaction], 1)
        )

        response = await client.get("/api/v1/salesManagement/saleTransaction")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 1
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_passes_filters_to_repo(self, test_client):
        """GET /saleTransaction with query params passes them to repo."""
        client, mock_repo, _ = test_client
        mock_repo.list_with_filters = AsyncMock(return_value=([], 0))

        dealer_id = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/salesManagement/saleTransaction?dealer_party_id={dealer_id}&page=2&size=5"
        )

        assert response.status_code == 200
        mock_repo.list_with_filters.assert_awaited_once()
        call_kwargs = mock_repo.list_with_filters.call_args.kwargs
        assert call_kwargs["page"] == 2
        assert call_kwargs["size"] == 5
