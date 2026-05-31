"""Unit tests for sell-out-service domain services."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.domain.models import (
    SaleChannel,
    SaleStatus,
    SaleTransaction,
    SaleTransactionCreate,
    SaleTransactionItem,
    SaleTransactionItemCreate,
)
from app.domain.services import create_sale_transaction, reverse_transaction
from telco_common.events.cloudevents import Topics
from telco_common.exceptions import ConflictException, NotFoundException


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_transaction(
    status: SaleStatus = SaleStatus.COMPLETED,
    dealer_party_id: uuid.UUID | None = None,
    total_amount: float = 45.00,
) -> SaleTransaction:
    now = datetime.now(UTC)
    _dealer = dealer_party_id or uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    return SaleTransaction(
        id=uuid.uuid4(),
        transaction_number="TXN-20240301-ABCD1234",
        dealer_party_id=_dealer,
        customer_party_id=None,
        channel=SaleChannel.RETAIL,
        items=[
            SaleTransactionItem(
                id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                product_name="SIM Premium",
                quantity=5,
                unit_price=10.00,
                discount_amount=1.00,
                serial_numbers=["SN001"],
                commission_eligible=True,
            )
        ],
        total_amount=total_amount,
        currency="USD",
        status=status,
        tenant_id="tenant-001",
        created_at=now,
        updated_at=now,
    )


def _make_create_data(
    quantity: int = 5,
    unit_price: float = 10.00,
    discount_amount: float = 1.00,
    extra_items: list[SaleTransactionItemCreate] | None = None,
) -> SaleTransactionCreate:
    items = [
        SaleTransactionItemCreate(
            product_id=uuid.uuid4(),
            product_name="SIM Premium",
            quantity=quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            serial_numbers=["SN001"],
            commission_eligible=True,
        )
    ]
    if extra_items:
        items.extend(extra_items)
    return SaleTransactionCreate(
        dealer_party_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        customer_party_id=None,
        channel=SaleChannel.RETAIL,
        items=items,
    )


# ─── create_sale_transaction tests ────────────────────────────────────────────

class TestCreateSaleTransaction:
    @pytest.mark.asyncio
    async def test_correct_total_amount_calculation(self):
        """total_amount = sum((unit_price - discount) * quantity) across all items."""
        data = _make_create_data(quantity=5, unit_price=10.00, discount_amount=1.00)
        # expected = (10.00 - 1.00) * 5 = 45.00
        expected_total = 45.00

        created_txn = _make_transaction(total_amount=expected_total)
        repo = MagicMock()
        repo.create = AsyncMock(return_value=created_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        result = await create_sale_transaction(
            data=data,
            tenant_id="tenant-001",
            correlation_id=str(uuid.uuid4()),
            repo=repo,
            kafka_producer=producer,
        )

        # Verify repo.create was called with the correct total_amount
        repo.create.assert_awaited_once()
        call_kwargs = repo.create.call_args
        assert call_kwargs.kwargs["total_amount"] == expected_total

    @pytest.mark.asyncio
    async def test_correct_total_amount_multi_item(self):
        """Multi-item total_amount is the sum of all line item sub-totals."""
        item1 = SaleTransactionItemCreate(
            product_id=uuid.uuid4(),
            product_name="SIM A",
            quantity=2,
            unit_price=20.00,
            discount_amount=2.00,
        )
        item2 = SaleTransactionItemCreate(
            product_id=uuid.uuid4(),
            product_name="SIM B",
            quantity=3,
            unit_price=15.00,
            discount_amount=0.00,
        )
        # item1: (20-2)*2 = 36.00, item2: (15-0)*3 = 45.00 → total = 81.00
        data = SaleTransactionCreate(
            dealer_party_id=uuid.uuid4(),
            channel=SaleChannel.ONLINE,
            items=[item1, item2],
        )

        created_txn = _make_transaction(total_amount=81.00)
        repo = MagicMock()
        repo.create = AsyncMock(return_value=created_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        await create_sale_transaction(
            data=data,
            tenant_id="tenant-001",
            correlation_id=str(uuid.uuid4()),
            repo=repo,
            kafka_producer=producer,
        )

        call_kwargs = repo.create.call_args
        assert call_kwargs.kwargs["total_amount"] == 81.00

    @pytest.mark.asyncio
    async def test_transaction_number_format_starts_with_txn(self):
        """transaction_number must start with 'TXN-'."""
        data = _make_create_data()
        created_txn = _make_transaction()
        repo = MagicMock()
        repo.create = AsyncMock(return_value=created_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        await create_sale_transaction(
            data=data,
            tenant_id="tenant-001",
            correlation_id=str(uuid.uuid4()),
            repo=repo,
            kafka_producer=producer,
        )

        call_kwargs = repo.create.call_args
        txn_number = call_kwargs.kwargs["transaction_number"]
        assert txn_number.startswith("TXN-"), f"Expected TXN- prefix, got: {txn_number}"

    @pytest.mark.asyncio
    async def test_transaction_number_format_matches_pattern(self):
        """transaction_number matches TXN-YYYYMMDD-XXXXXXXX."""
        data = _make_create_data()
        created_txn = _make_transaction()
        repo = MagicMock()
        repo.create = AsyncMock(return_value=created_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        await create_sale_transaction(
            data=data,
            tenant_id="tenant-001",
            correlation_id=str(uuid.uuid4()),
            repo=repo,
            kafka_producer=producer,
        )

        call_kwargs = repo.create.call_args
        txn_number = call_kwargs.kwargs["transaction_number"]
        pattern = re.compile(r"^TXN-\d{8}-[A-F0-9]{8}$")
        assert pattern.match(txn_number), (
            f"transaction_number '{txn_number}' does not match pattern TXN-YYYYMMDD-XXXXXXXX"
        )

    @pytest.mark.asyncio
    async def test_publishes_correct_kafka_event_type(self):
        """The published Kafka event must be on Topics.SALES_SELLOUT_COMPLETED."""
        data = _make_create_data()
        created_txn = _make_transaction()
        repo = MagicMock()
        repo.create = AsyncMock(return_value=created_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        await create_sale_transaction(
            data=data,
            tenant_id="tenant-001",
            correlation_id=str(uuid.uuid4()),
            repo=repo,
            kafka_producer=producer,
        )

        producer.send.assert_awaited_once()
        send_args = producer.send.call_args
        published_topic = send_args.args[0]
        assert published_topic == Topics.SALES_SELLOUT_COMPLETED

    @pytest.mark.asyncio
    async def test_kafka_event_data_contains_correct_dealer_party_id(self):
        """The event payload's dealer_party_id matches the input."""
        dealer_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        data = SaleTransactionCreate(
            dealer_party_id=dealer_id,
            channel=SaleChannel.AGENT,
            items=[
                SaleTransactionItemCreate(
                    product_id=uuid.uuid4(),
                    product_name="Device",
                    quantity=1,
                    unit_price=100.00,
                    discount_amount=0.0,
                )
            ],
        )
        created_txn = _make_transaction(dealer_party_id=dealer_id)
        repo = MagicMock()
        repo.create = AsyncMock(return_value=created_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        await create_sale_transaction(
            data=data,
            tenant_id="tenant-001",
            correlation_id=str(uuid.uuid4()),
            repo=repo,
            kafka_producer=producer,
        )

        send_args = producer.send.call_args
        event_payload = send_args.args[1]  # the event dict
        assert event_payload["data"]["dealer_party_id"] == str(dealer_id)

    @pytest.mark.asyncio
    async def test_kafka_event_key_is_dealer_party_id(self):
        """Kafka message key must be the dealer_party_id string (for partitioning)."""
        dealer_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        data = _make_create_data()
        created_txn = _make_transaction(dealer_party_id=dealer_id)
        repo = MagicMock()
        repo.create = AsyncMock(return_value=created_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        await create_sale_transaction(
            data=data,
            tenant_id="tenant-001",
            correlation_id=str(uuid.uuid4()),
            repo=repo,
            kafka_producer=producer,
        )

        send_args = producer.send.call_args
        assert send_args.kwargs["key"] == str(dealer_id)

    @pytest.mark.asyncio
    async def test_zero_discount_total_amount(self):
        """When discount_amount=0, total = unit_price * quantity."""
        data = _make_create_data(quantity=3, unit_price=15.00, discount_amount=0.00)
        expected_total = 45.00

        created_txn = _make_transaction(total_amount=expected_total)
        repo = MagicMock()
        repo.create = AsyncMock(return_value=created_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        await create_sale_transaction(
            data=data,
            tenant_id="tenant-001",
            correlation_id=str(uuid.uuid4()),
            repo=repo,
            kafka_producer=producer,
        )

        call_kwargs = repo.create.call_args
        assert call_kwargs.kwargs["total_amount"] == expected_total


# ─── reverse_transaction tests ────────────────────────────────────────────────

class TestReverseTransaction:
    @pytest.mark.asyncio
    async def test_raises_conflict_if_status_pending(self):
        """Reversing a PENDING transaction raises ConflictException."""
        pending_txn = _make_transaction(status=SaleStatus.PENDING)
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=pending_txn)
        producer = AsyncMock()

        with pytest.raises(ConflictException) as exc_info:
            await reverse_transaction(
                transaction_id=str(pending_txn.id),
                reason="Test reversal",
                tenant_id="tenant-001",
                repo=repo,
                kafka_producer=producer,
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_raises_conflict_if_already_reversed(self):
        """Reversing an already REVERSED transaction raises ConflictException."""
        reversed_txn = _make_transaction(status=SaleStatus.REVERSED)
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=reversed_txn)
        producer = AsyncMock()

        with pytest.raises(ConflictException) as exc_info:
            await reverse_transaction(
                transaction_id=str(reversed_txn.id),
                reason="Double reversal attempt",
                tenant_id="tenant-001",
                repo=repo,
                kafka_producer=producer,
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_raises_not_found_if_transaction_missing(self):
        """Reversing a non-existent transaction raises NotFoundException."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        producer = AsyncMock()

        with pytest.raises(NotFoundException) as exc_info:
            await reverse_transaction(
                transaction_id=str(uuid.uuid4()),
                reason="Test reversal",
                tenant_id="tenant-001",
                repo=repo,
                kafka_producer=producer,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_successful_reversal_calls_update_status(self):
        """Successful reversal calls repo.update_status with REVERSED."""
        completed_txn = _make_transaction(status=SaleStatus.COMPLETED)
        reversed_txn = _make_transaction(status=SaleStatus.REVERSED)
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=completed_txn)
        repo.update_status = AsyncMock(return_value=reversed_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        result = await reverse_transaction(
            transaction_id=str(completed_txn.id),
            reason="Customer request",
            tenant_id="tenant-001",
            repo=repo,
            kafka_producer=producer,
        )

        repo.update_status.assert_awaited_once_with(
            completed_txn.id, SaleStatus.REVERSED, "tenant-001"
        )
        assert result.status == SaleStatus.REVERSED

    @pytest.mark.asyncio
    async def test_successful_reversal_publishes_event(self):
        """Successful reversal publishes a reversal event to Kafka."""
        completed_txn = _make_transaction(status=SaleStatus.COMPLETED)
        reversed_txn = _make_transaction(status=SaleStatus.REVERSED)
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=completed_txn)
        repo.update_status = AsyncMock(return_value=reversed_txn)
        producer = AsyncMock()
        producer.send = AsyncMock()

        await reverse_transaction(
            transaction_id=str(completed_txn.id),
            reason="Customer request",
            tenant_id="tenant-001",
            repo=repo,
            kafka_producer=producer,
        )

        producer.send.assert_awaited_once()
        send_args = producer.send.call_args
        published_topic = send_args.args[0]
        assert published_topic == Topics.SALES_SELLOUT_REVERSED
