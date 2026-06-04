"""Unit tests for SaleTransactionRepository against in-memory SQLite."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import (
    SaleChannel,
    SaleStatus,
    SaleTransactionCreate,
    SaleTransactionItemCreate,
)
from app.infrastructure.db.repository import SaleTransactionRepository

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


@pytest.fixture
def repo(db_session) -> SaleTransactionRepository:
    return SaleTransactionRepository(db_session)


def _make_txn_create(
    dealer_id: uuid.UUID,
    *,
    channel: SaleChannel = SaleChannel.RETAIL,
    items: list[SaleTransactionItemCreate] | None = None,
    customer_id: uuid.UUID | None = None,
) -> SaleTransactionCreate:
    if items is None:
        items = [
            SaleTransactionItemCreate(
                product_id=uuid.uuid4(),
                product_name="SIM Card",
                quantity=5,
                unit_price=10.0,
                discount_amount=1.0,
                serial_numbers=["SN001", "SN002"],
                commission_eligible=True,
            )
        ]
    return SaleTransactionCreate(
        dealer_party_id=dealer_id,
        customer_party_id=customer_id,
        channel=channel,
        items=items,
    )


def _make_item_create(
    *,
    qty: int = 5,
    unit_price: float = 10.0,
    discount: float = 1.0,
    name: str = "SIM Card",
    commission_eligible: bool = True,
    serial_numbers: list[str] | None = None,
) -> SaleTransactionItemCreate:
    return SaleTransactionItemCreate(
        product_id=uuid.uuid4(),
        product_name=name,
        quantity=qty,
        unit_price=unit_price,
        discount_amount=discount,
        serial_numbers=serial_numbers or [],
        commission_eligible=commission_eligible,
    )


async def _create_txn(
    repo: SaleTransactionRepository,
    dealer_id: uuid.UUID,
    tenant_id: str,
    *,
    txn_number: str = "TXN-001",
    total_amount: float = 45.0,
    status_override: SaleStatus | None = None,
    channel: SaleChannel = SaleChannel.RETAIL,
    items: list[SaleTransactionItemCreate] | None = None,
) -> object:
    item = items or [_make_item_create()]
    txn_create = _make_txn_create(dealer_id, channel=channel, items=item)
    created = await repo.create(txn_create, item, tenant_id, txn_number, total_amount)
    if status_override is not None:
        created = await repo.update_status(created.id, status_override, tenant_id)
    return created


# ── create ────────────────────────────────────────────────────────────────────


async def test_create_returns_transaction_with_id(repo, sample_tenant_id, dealer_id):
    txn = await _create_txn(repo, dealer_id, sample_tenant_id)
    assert txn.id is not None
    assert txn.transaction_number == "TXN-001"
    assert txn.tenant_id == sample_tenant_id
    assert txn.status == SaleStatus.COMPLETED
    assert txn.currency == "USD"
    assert txn.total_amount == 45.0


async def test_create_includes_items(repo, sample_tenant_id, dealer_id):
    items = [
        _make_item_create(name="SIM A", qty=2, unit_price=10.0),
        _make_item_create(name="SIM B", qty=3, unit_price=5.0),
    ]
    txn = await _create_txn(repo, dealer_id, sample_tenant_id, items=items)
    assert len(txn.items) == 2
    names = {i.product_name for i in txn.items}
    assert names == {"SIM A", "SIM B"}


async def test_create_maps_serial_numbers(repo, sample_tenant_id, dealer_id):
    items = [_make_item_create(serial_numbers=["SN-X", "SN-Y"])]
    txn = await _create_txn(repo, dealer_id, sample_tenant_id, items=items)
    assert txn.items[0].serial_numbers == ["SN-X", "SN-Y"]


async def test_create_maps_commission_eligible_false(repo, sample_tenant_id, dealer_id):
    items = [_make_item_create(commission_eligible=False)]
    txn = await _create_txn(repo, dealer_id, sample_tenant_id, items=items)
    assert txn.items[0].commission_eligible is False


async def test_create_stores_dealer_and_channel(repo, sample_tenant_id, dealer_id):
    txn = await _create_txn(repo, dealer_id, sample_tenant_id, channel=SaleChannel.ONLINE)
    assert txn.dealer_party_id == dealer_id
    assert txn.channel == SaleChannel.ONLINE


# ── get_by_id ─────────────────────────────────────────────────────────────────


async def test_get_by_id_found(repo, sample_tenant_id, dealer_id):
    created = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-G1")
    fetched = await repo.get_by_id(created.id, sample_tenant_id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.transaction_number == "TXN-G1"


async def test_get_by_id_not_found(repo, sample_tenant_id):
    result = await repo.get_by_id(uuid.uuid4(), sample_tenant_id)
    assert result is None


async def test_get_by_id_tenant_isolation(repo, sample_tenant_id, other_tenant_id, dealer_id):
    created = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-ISO")
    # Same id, different tenant -> not found
    assert await repo.get_by_id(created.id, other_tenant_id) is None
    # Correct tenant -> found
    assert await repo.get_by_id(created.id, sample_tenant_id) is not None


async def test_get_by_id_roundtrip_items(repo, sample_tenant_id, dealer_id):
    items = [_make_item_create(name="Router", qty=2, unit_price=100.0, serial_numbers=["R1"])]
    created = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-RT", items=items)
    fetched = await repo.get_by_id(created.id, sample_tenant_id)
    assert len(fetched.items) == 1
    assert fetched.items[0].product_name == "Router"
    assert fetched.items[0].quantity == 2


# ── list_with_filters ─────────────────────────────────────────────────────────


async def test_list_no_filters_returns_tenant_records(repo, sample_tenant_id, other_tenant_id, dealer_id):
    await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-L1")
    await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-L2")
    await _create_txn(repo, dealer_id, other_tenant_id, txn_number="TXN-L3")

    items, total = await repo.list_with_filters(sample_tenant_id)
    assert total == 2
    assert len(items) == 2
    assert all(t.tenant_id == sample_tenant_id for t in items)


async def test_list_empty(repo, sample_tenant_id):
    items, total = await repo.list_with_filters(sample_tenant_id)
    assert total == 0
    assert items == []


async def test_list_filter_by_dealer_party_id(repo, sample_tenant_id):
    d1 = uuid.uuid4()
    d2 = uuid.uuid4()
    await _create_txn(repo, d1, sample_tenant_id, txn_number="TXN-D1")
    await _create_txn(repo, d2, sample_tenant_id, txn_number="TXN-D2")

    items, total = await repo.list_with_filters(sample_tenant_id, dealer_party_id=d1)
    assert total == 1
    assert items[0].dealer_party_id == d1


async def test_list_filter_by_status(repo, sample_tenant_id, dealer_id):
    completed = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-S1")
    await _create_txn(
        repo, dealer_id, sample_tenant_id, txn_number="TXN-S2",
        status_override=SaleStatus.REVERSED,
    )

    items, total = await repo.list_with_filters(sample_tenant_id, status=SaleStatus.COMPLETED)
    assert total == 1
    assert items[0].id == completed.id

    rev_items, rev_total = await repo.list_with_filters(sample_tenant_id, status=SaleStatus.REVERSED)
    assert rev_total == 1


async def test_list_filter_by_from_date(repo, sample_tenant_id, dealer_id, db_session):
    """Transactions created before from_date are excluded."""
    from app.infrastructure.db import models as db_models

    # Create two transactions and manually set created_at on one to be "old"
    t1 = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-FD1")
    t2 = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-FD2")

    # Move t1's created_at to 10 days ago via direct ORM update
    old_time = datetime.now(UTC) - timedelta(days=10)
    db_obj = await db_session.get(db_models.SaleTransaction, t1.id)
    db_obj.created_at = old_time
    await db_session.flush()

    cutoff = datetime.now(UTC) - timedelta(days=1)
    items, total = await repo.list_with_filters(sample_tenant_id, from_date=cutoff)
    assert total == 1
    assert items[0].id == t2.id


async def test_list_filter_by_to_date(repo, sample_tenant_id, dealer_id, db_session):
    """Transactions created after to_date are excluded."""
    from app.infrastructure.db import models as db_models

    t1 = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-TD1")
    t2 = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-TD2")

    # Move t2's created_at to 10 days in the future
    future_time = datetime.now(UTC) + timedelta(days=10)
    db_obj = await db_session.get(db_models.SaleTransaction, t2.id)
    db_obj.created_at = future_time
    await db_session.flush()

    cutoff = datetime.now(UTC) + timedelta(days=1)
    items, total = await repo.list_with_filters(sample_tenant_id, to_date=cutoff)
    assert total == 1
    assert items[0].id == t1.id


async def test_list_pagination(repo, sample_tenant_id, dealer_id):
    for i in range(5):
        await _create_txn(repo, dealer_id, sample_tenant_id, txn_number=f"TXN-P{i}")

    page1, total = await repo.list_with_filters(sample_tenant_id, page=1, size=2)
    page2, _ = await repo.list_with_filters(sample_tenant_id, page=2, size=2)
    page3, _ = await repo.list_with_filters(sample_tenant_id, page=3, size=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
    all_ids = {t.id for t in page1} | {t.id for t in page2} | {t.id for t in page3}
    assert len(all_ids) == 5


# ── update_status ─────────────────────────────────────────────────────────────


async def test_update_status_changes_status(repo, sample_tenant_id, dealer_id):
    txn = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-US1")
    assert txn.status == SaleStatus.COMPLETED

    updated = await repo.update_status(txn.id, SaleStatus.REVERSED, sample_tenant_id)
    assert updated is not None
    assert updated.status == SaleStatus.REVERSED


async def test_update_status_not_found_returns_none(repo, sample_tenant_id):
    result = await repo.update_status(uuid.uuid4(), SaleStatus.REVERSED, sample_tenant_id)
    assert result is None


async def test_update_status_tenant_isolation(repo, sample_tenant_id, other_tenant_id, dealer_id):
    txn = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-TI1")
    # Different tenant cannot update
    result = await repo.update_status(txn.id, SaleStatus.REVERSED, other_tenant_id)
    assert result is None
    # Original remains unchanged
    original = await repo.get_by_id(txn.id, sample_tenant_id)
    assert original.status == SaleStatus.COMPLETED


async def test_update_status_persisted(repo, sample_tenant_id, dealer_id):
    txn = await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-UP1")
    await repo.update_status(txn.id, SaleStatus.REVERSED, sample_tenant_id)
    refetched = await repo.get_by_id(txn.id, sample_tenant_id)
    assert refetched.status == SaleStatus.REVERSED


# ── get_summary ───────────────────────────────────────────────────────────────


async def test_get_summary_counts_transactions(repo, sample_tenant_id, dealer_id):
    items = [_make_item_create(qty=3, unit_price=20.0, discount=0.0)]
    await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-SM1", total_amount=60.0, items=items)
    await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-SM2", total_amount=60.0, items=items)

    summary = await repo.get_summary(dealer_id, "2026-06", sample_tenant_id)
    assert summary.total_transactions == 2
    assert summary.total_amount == pytest.approx(120.0)
    assert summary.dealer_party_id == dealer_id
    assert summary.currency == "USD"


async def test_get_summary_sums_units(repo, sample_tenant_id, dealer_id):
    items = [_make_item_create(qty=4), _make_item_create(qty=6)]
    await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-SU1", items=items)

    summary = await repo.get_summary(dealer_id, "2026-06", sample_tenant_id)
    assert summary.total_units == 10


async def test_get_summary_excludes_reversed(repo, sample_tenant_id, dealer_id):
    await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-SX1")
    await _create_txn(
        repo, dealer_id, sample_tenant_id, txn_number="TXN-SX2",
        status_override=SaleStatus.REVERSED,
    )

    summary = await repo.get_summary(dealer_id, "2026-06", sample_tenant_id)
    assert summary.total_transactions == 1


async def test_get_summary_empty(repo, sample_tenant_id, dealer_id):
    summary = await repo.get_summary(dealer_id, "2026-06", sample_tenant_id)
    assert summary.total_transactions == 0
    assert summary.total_units == 0
    assert summary.total_amount == 0.0


async def test_get_summary_invalid_period_returns_all(repo, sample_tenant_id, dealer_id):
    """An unparseable period string should still return results (no date filter)."""
    await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-IP1")
    summary = await repo.get_summary(dealer_id, "not-a-period", sample_tenant_id)
    assert summary.total_transactions == 1


async def test_get_summary_tenant_isolation(repo, sample_tenant_id, other_tenant_id, dealer_id):
    await _create_txn(repo, dealer_id, sample_tenant_id, txn_number="TXN-STI")
    summary = await repo.get_summary(dealer_id, "2026-06", other_tenant_id)
    assert summary.total_transactions == 0


async def test_get_summary_period_stored_in_result(repo, sample_tenant_id, dealer_id):
    summary = await repo.get_summary(dealer_id, "2026-06", sample_tenant_id)
    assert summary.period == "2026-06"
