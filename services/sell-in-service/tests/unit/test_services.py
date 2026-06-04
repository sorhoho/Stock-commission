"""Unit tests for sell-in-service domain service layer.

Uses the real repository against in-memory SQLite plus a mocked Kafka producer
so we assert on real persisted state AND on event publishing behaviour.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.domain.models import OrderState, ProductOrderCreate, ProductOrderItemCreate
from app.domain.services import cancel_order, complete_order, create_order
from app.infrastructure.db.repository import ProductOrderRepository
from telco_common.events.cloudevents import Topics

pytestmark = pytest.mark.asyncio


@pytest.fixture
def repo(db_session) -> ProductOrderRepository:
    return ProductOrderRepository(db_session)


# ── create_order ─────────────────────────────────────────────────────────────


async def test_create_order_persists_and_publishes(repo, mock_kafka_producer, sample_order_create, sample_tenant_id):
    order = await create_order(sample_order_create, sample_tenant_id, repo, mock_kafka_producer)

    # persisted real state
    assert order.state is OrderState.ACKNOWLEDGED
    assert order.total_amount == pytest.approx(10 * 25.5)
    fetched = await repo.get_by_id(order.id, sample_tenant_id)
    assert fetched is not None

    # event published exactly once on the ordered topic
    mock_kafka_producer.send.assert_awaited_once()
    kwargs = mock_kafka_producer.send.await_args.kwargs
    assert kwargs["topic"] == Topics.SALES_SELLIN_ORDERED
    assert kwargs["key"] == str(order.requestor_party_id)
    event_data = kwargs["event"]["data"]
    assert event_data["order_id"] == str(order.id)
    assert event_data["order_number"] == order.order_number
    assert len(event_data["items"]) == 1
    assert event_data["items"][0]["quantity"] == 10


async def test_create_order_total_for_multiple_items(repo, mock_kafka_producer, requestor_party_id, supplier_party_id, sample_tenant_id):
    data = ProductOrderCreate(
        requestor_party_id=requestor_party_id,
        supplier_party_id=supplier_party_id,
        items=[
            ProductOrderItemCreate(product_id=uuid.uuid4(), product_name="A", quantity=4, unit_price=2.5),
            ProductOrderItemCreate(product_id=uuid.uuid4(), product_name="B", quantity=1, unit_price=100.0),
        ],
        requested_delivery_date=date(2026, 7, 1),
    )
    order = await create_order(data, sample_tenant_id, repo, mock_kafka_producer)
    assert order.total_amount == pytest.approx(4 * 2.5 + 100.0)


# ── complete_order ───────────────────────────────────────────────────────────


async def test_complete_order_updates_state_and_publishes_delivered(repo, mock_kafka_producer, sample_order_create, sample_tenant_id):
    order = await create_order(sample_order_create, sample_tenant_id, repo, mock_kafka_producer)
    mock_kafka_producer.send.reset_mock()

    completed = await complete_order(
        order_id=order.id,
        actual_delivery_date=date(2026, 7, 5),
        tenant_id=sample_tenant_id,
        repo=repo,
        kafka_producer=mock_kafka_producer,
    )
    assert completed.state is OrderState.COMPLETED
    assert completed.actual_delivery_date == date(2026, 7, 5)

    mock_kafka_producer.send.assert_awaited_once()
    kwargs = mock_kafka_producer.send.await_args.kwargs
    assert kwargs["topic"] == Topics.SALES_SELLIN_DELIVERED
    assert kwargs["event"]["data"]["order_id"] == str(order.id)


async def test_complete_order_not_found_raises_404(repo, mock_kafka_producer, sample_tenant_id):
    with pytest.raises(HTTPException) as exc:
        await complete_order(
            order_id=uuid.uuid4(),
            actual_delivery_date=date(2026, 7, 5),
            tenant_id=sample_tenant_id,
            repo=repo,
            kafka_producer=mock_kafka_producer,
        )
    assert exc.value.status_code == 404
    mock_kafka_producer.send.assert_not_awaited()


async def test_complete_order_idempotent_when_already_completed(repo, mock_kafka_producer, sample_order_create, sample_tenant_id):
    order = await create_order(sample_order_create, sample_tenant_id, repo, mock_kafka_producer)
    await complete_order(order.id, date(2026, 7, 5), sample_tenant_id, repo, mock_kafka_producer)
    mock_kafka_producer.send.reset_mock()

    # second completion is a no-op (returns order, no new event)
    again = await complete_order(order.id, date(2026, 8, 1), sample_tenant_id, repo, mock_kafka_producer)
    assert again.state is OrderState.COMPLETED
    mock_kafka_producer.send.assert_not_awaited()


async def test_complete_cancelled_order_raises_422(repo, mock_kafka_producer, sample_order_create, sample_tenant_id):
    order = await create_order(sample_order_create, sample_tenant_id, repo, mock_kafka_producer)
    await cancel_order(order.id, sample_tenant_id, repo, mock_kafka_producer)

    with pytest.raises(HTTPException) as exc:
        await complete_order(order.id, date(2026, 7, 5), sample_tenant_id, repo, mock_kafka_producer)
    assert exc.value.status_code == 422


# ── cancel_order ─────────────────────────────────────────────────────────────


async def test_cancel_order_updates_state(repo, mock_kafka_producer, sample_order_create, sample_tenant_id):
    order = await create_order(sample_order_create, sample_tenant_id, repo, mock_kafka_producer)
    cancelled = await cancel_order(order.id, sample_tenant_id, repo, mock_kafka_producer)
    assert cancelled.state is OrderState.CANCELLED

    fetched = await repo.get_by_id(order.id, sample_tenant_id)
    assert fetched.state is OrderState.CANCELLED


async def test_cancel_order_not_found_raises_404(repo, mock_kafka_producer, sample_tenant_id):
    with pytest.raises(HTTPException) as exc:
        await cancel_order(uuid.uuid4(), sample_tenant_id, repo, mock_kafka_producer)
    assert exc.value.status_code == 404


async def test_cancel_order_idempotent_when_already_cancelled(repo, mock_kafka_producer, sample_order_create, sample_tenant_id):
    order = await create_order(sample_order_create, sample_tenant_id, repo, mock_kafka_producer)
    await cancel_order(order.id, sample_tenant_id, repo, mock_kafka_producer)
    again = await cancel_order(order.id, sample_tenant_id, repo, mock_kafka_producer)
    assert again.state is OrderState.CANCELLED


async def test_cancel_completed_order_raises_422(repo, mock_kafka_producer, sample_order_create, sample_tenant_id):
    order = await create_order(sample_order_create, sample_tenant_id, repo, mock_kafka_producer)
    await complete_order(order.id, date(2026, 7, 5), sample_tenant_id, repo, mock_kafka_producer)

    with pytest.raises(HTTPException) as exc:
        await cancel_order(order.id, sample_tenant_id, repo, mock_kafka_producer)
    assert exc.value.status_code == 422
