"""Unit tests for ProductOrderRepository against in-memory SQLite."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.domain.models import OrderState, ProductOrderCreate, ProductOrderItemCreate
from app.infrastructure.db.repository import ProductOrderRepository, _generate_order_number

pytestmark = pytest.mark.asyncio


@pytest.fixture
def repo(db_session) -> ProductOrderRepository:
    return ProductOrderRepository(db_session)


def _make_order_create(
    requestor: uuid.UUID,
    supplier: uuid.UUID,
    *,
    items: list[ProductOrderItemCreate] | None = None,
    delivery: date = date(2026, 7, 1),
) -> ProductOrderCreate:
    if items is None:
        items = [
            ProductOrderItemCreate(
                product_id=uuid.uuid4(),
                product_name="Router X100",
                quantity=10,
                unit_price=25.5,
            )
        ]
    return ProductOrderCreate(
        requestor_party_id=requestor,
        supplier_party_id=supplier,
        items=items,
        requested_delivery_date=delivery,
    )


# ── create ──────────────────────────────────────────────────────────────────────


async def test_create_persists_order_and_computes_total(repo, sample_tenant_id, requestor_party_id, supplier_party_id):
    items = [
        ProductOrderItemCreate(product_id=uuid.uuid4(), product_name="A", quantity=3, unit_price=10.0),
        ProductOrderItemCreate(product_id=uuid.uuid4(), product_name="B", quantity=2, unit_price=5.5),
    ]
    order = await repo.create(_make_order_create(requestor_party_id, supplier_party_id, items=items), sample_tenant_id)

    assert order.id is not None
    assert order.order_number.startswith("SLI-")
    assert order.state is OrderState.ACKNOWLEDGED
    assert order.currency == "THB"
    assert order.total_amount == pytest.approx(3 * 10.0 + 2 * 5.5)
    assert order.tenant_id == sample_tenant_id
    assert len(order.items) == 2
    assert {i.product_name for i in order.items} == {"A", "B"}
    assert order.actual_delivery_date is None


async def test_create_then_get_by_id_roundtrip(repo, sample_tenant_id, requestor_party_id, supplier_party_id):
    created = await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    fetched = await repo.get_by_id(created.id, sample_tenant_id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.order_number == created.order_number
    assert fetched.items[0].product_name == "Router X100"


# ── get_by_id ─────────────────────────────────────────────────────────────────


async def test_get_by_id_not_found(repo, sample_tenant_id):
    assert await repo.get_by_id(uuid.uuid4(), sample_tenant_id) is None


async def test_get_by_id_tenant_isolation(repo, sample_tenant_id, other_tenant_id, requestor_party_id, supplier_party_id):
    created = await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    # Same id but wrong tenant -> not visible
    assert await repo.get_by_id(created.id, other_tenant_id) is None
    assert await repo.get_by_id(created.id, sample_tenant_id) is not None


# ── list_with_filters ────────────────────────────────────────────────────────


async def test_list_returns_only_tenant_orders(repo, sample_tenant_id, other_tenant_id, requestor_party_id, supplier_party_id):
    await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    await repo.create(_make_order_create(requestor_party_id, supplier_party_id), other_tenant_id)

    mine = await repo.list_with_filters(tenant_id=sample_tenant_id)
    theirs = await repo.list_with_filters(tenant_id=other_tenant_id)
    assert len(mine) == 2
    assert len(theirs) == 1
    assert all(o.tenant_id == sample_tenant_id for o in mine)


async def test_list_filter_by_requestor(repo, sample_tenant_id, supplier_party_id):
    r1 = uuid.uuid4()
    r2 = uuid.uuid4()
    await repo.create(_make_order_create(r1, supplier_party_id), sample_tenant_id)
    await repo.create(_make_order_create(r2, supplier_party_id), sample_tenant_id)

    results = await repo.list_with_filters(tenant_id=sample_tenant_id, requestor_party_id=r1)
    assert len(results) == 1
    assert results[0].requestor_party_id == r1


async def test_list_filter_by_state(repo, sample_tenant_id, requestor_party_id, supplier_party_id):
    o1 = await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    await repo.update_state(o1.id, sample_tenant_id, OrderState.COMPLETED, actual_delivery_date=date(2026, 7, 2))

    completed = await repo.list_with_filters(tenant_id=sample_tenant_id, state=OrderState.COMPLETED)
    acknowledged = await repo.list_with_filters(tenant_id=sample_tenant_id, state=OrderState.ACKNOWLEDGED)
    assert len(completed) == 1
    assert completed[0].id == o1.id
    assert len(acknowledged) == 1


async def test_list_filter_by_date_range(repo, sample_tenant_id, requestor_party_id, supplier_party_id):
    await repo.create(_make_order_create(requestor_party_id, supplier_party_id, delivery=date(2026, 1, 10)), sample_tenant_id)
    await repo.create(_make_order_create(requestor_party_id, supplier_party_id, delivery=date(2026, 6, 10)), sample_tenant_id)
    await repo.create(_make_order_create(requestor_party_id, supplier_party_id, delivery=date(2026, 12, 10)), sample_tenant_id)

    mid = await repo.list_with_filters(
        tenant_id=sample_tenant_id, from_date=date(2026, 5, 1), to_date=date(2026, 8, 1)
    )
    assert len(mid) == 1
    assert mid[0].requested_delivery_date == date(2026, 6, 10)


async def test_list_pagination(repo, sample_tenant_id, requestor_party_id, supplier_party_id):
    for _ in range(5):
        await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)

    page1 = await repo.list_with_filters(tenant_id=sample_tenant_id, page=1, size=2)
    page2 = await repo.list_with_filters(tenant_id=sample_tenant_id, page=2, size=2)
    page3 = await repo.list_with_filters(tenant_id=sample_tenant_id, page=3, size=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
    ids = {o.id for o in page1} | {o.id for o in page2} | {o.id for o in page3}
    assert len(ids) == 5  # no overlap across pages


async def test_list_empty(repo, sample_tenant_id):
    assert await repo.list_with_filters(tenant_id=sample_tenant_id) == []


# ── update_state ─────────────────────────────────────────────────────────────


async def test_update_state_sets_state_and_delivery_date(repo, sample_tenant_id, requestor_party_id, supplier_party_id):
    order = await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    updated = await repo.update_state(
        order.id, sample_tenant_id, OrderState.COMPLETED, actual_delivery_date=date(2026, 7, 3)
    )
    assert updated is not None
    assert updated.state is OrderState.COMPLETED
    assert updated.actual_delivery_date == date(2026, 7, 3)

    # persisted
    refetched = await repo.get_by_id(order.id, sample_tenant_id)
    assert refetched.state is OrderState.COMPLETED
    assert refetched.actual_delivery_date == date(2026, 7, 3)


async def test_update_state_without_delivery_date_leaves_it_none(repo, sample_tenant_id, requestor_party_id, supplier_party_id):
    order = await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    updated = await repo.update_state(order.id, sample_tenant_id, OrderState.CANCELLED)
    assert updated.state is OrderState.CANCELLED
    assert updated.actual_delivery_date is None


async def test_update_state_not_found_returns_none(repo, sample_tenant_id):
    assert await repo.update_state(uuid.uuid4(), sample_tenant_id, OrderState.COMPLETED) is None


async def test_update_state_tenant_isolation(repo, sample_tenant_id, other_tenant_id, requestor_party_id, supplier_party_id):
    order = await repo.create(_make_order_create(requestor_party_id, supplier_party_id), sample_tenant_id)
    # wrong tenant cannot update
    assert await repo.update_state(order.id, other_tenant_id, OrderState.CANCELLED) is None
    refetched = await repo.get_by_id(order.id, sample_tenant_id)
    assert refetched.state is OrderState.ACKNOWLEDGED


# ── helpers ─────────────────────────────────────────────────────────────────


def test_generate_order_number_format():
    num = _generate_order_number()
    assert num.startswith("SLI-")
    parts = num.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD
    assert 1000 <= int(parts[2]) <= 9999
