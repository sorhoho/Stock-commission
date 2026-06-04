"""Unit tests for sell-in-service Pydantic domain models."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.models import (
    OrderState,
    ProductOrder,
    ProductOrderCreate,
    ProductOrderItem,
    ProductOrderItemCreate,
    ProductOrderUpdate,
)


# ── OrderState enum ────────────────────────────────────────────────────────────


def test_order_state_values():
    assert OrderState.ACKNOWLEDGED == "ACKNOWLEDGED"
    assert OrderState.IN_PROGRESS == "IN_PROGRESS"
    assert OrderState.COMPLETED == "COMPLETED"
    assert OrderState.CANCELLED == "CANCELLED"
    assert {s.value for s in OrderState} == {
        "ACKNOWLEDGED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    }


def test_order_state_invalid_value():
    with pytest.raises(ValueError):
        OrderState("SHIPPED")


# ── ProductOrderItemCreate ─────────────────────────────────────────────────────


def test_item_create_valid(product_id):
    item = ProductOrderItemCreate(
        product_id=product_id,
        product_name="Router X100",
        quantity=5,
        unit_price=12.5,
    )
    assert item.product_id == product_id
    assert item.quantity == 5
    assert item.unit_price == 12.5


def test_item_create_quantity_must_be_positive(product_id):
    with pytest.raises(ValidationError):
        ProductOrderItemCreate(
            product_id=product_id,
            product_name="Router",
            quantity=0,
            unit_price=1.0,
        )


def test_item_create_quantity_negative_rejected(product_id):
    with pytest.raises(ValidationError):
        ProductOrderItemCreate(
            product_id=product_id,
            product_name="Router",
            quantity=-3,
            unit_price=1.0,
        )


def test_item_create_unit_price_negative_rejected(product_id):
    with pytest.raises(ValidationError):
        ProductOrderItemCreate(
            product_id=product_id,
            product_name="Router",
            quantity=1,
            unit_price=-0.01,
        )


def test_item_create_unit_price_zero_allowed(product_id):
    item = ProductOrderItemCreate(
        product_id=product_id,
        product_name="Freebie",
        quantity=1,
        unit_price=0.0,
    )
    assert item.unit_price == 0.0


def test_item_create_requires_product_id():
    with pytest.raises(ValidationError):
        ProductOrderItemCreate(product_name="Router", quantity=1, unit_price=1.0)


def test_item_create_invalid_uuid():
    with pytest.raises(ValidationError):
        ProductOrderItemCreate(
            product_id="not-a-uuid",
            product_name="Router",
            quantity=1,
            unit_price=1.0,
        )


# ── ProductOrderCreate ──────────────────────────────────────────────────────────


def test_order_create_valid(sample_order_create):
    assert len(sample_order_create.items) == 1
    assert sample_order_create.notes == "Urgent restock"
    assert sample_order_create.requested_delivery_date == date(2026, 7, 1)


def test_order_create_requires_at_least_one_item(requestor_party_id, supplier_party_id):
    with pytest.raises(ValidationError):
        ProductOrderCreate(
            requestor_party_id=requestor_party_id,
            supplier_party_id=supplier_party_id,
            items=[],
            requested_delivery_date=date(2026, 7, 1),
        )


def test_order_create_notes_optional(requestor_party_id, supplier_party_id, sample_item_create):
    order = ProductOrderCreate(
        requestor_party_id=requestor_party_id,
        supplier_party_id=supplier_party_id,
        items=[sample_item_create],
        requested_delivery_date=date(2026, 7, 1),
    )
    assert order.notes is None


def test_order_create_requires_delivery_date(requestor_party_id, supplier_party_id, sample_item_create):
    with pytest.raises(ValidationError):
        ProductOrderCreate(
            requestor_party_id=requestor_party_id,
            supplier_party_id=supplier_party_id,
            items=[sample_item_create],
        )


def test_order_create_requires_requestor(supplier_party_id, sample_item_create):
    with pytest.raises(ValidationError):
        ProductOrderCreate(
            supplier_party_id=supplier_party_id,
            items=[sample_item_create],
            requested_delivery_date=date(2026, 7, 1),
        )


# ── ProductOrderUpdate ──────────────────────────────────────────────────────────


def test_order_update_all_optional():
    upd = ProductOrderUpdate()
    assert upd.state is None
    assert upd.actual_delivery_date is None


def test_order_update_with_state():
    upd = ProductOrderUpdate(state=OrderState.COMPLETED, actual_delivery_date=date(2026, 7, 2))
    assert upd.state is OrderState.COMPLETED
    assert upd.actual_delivery_date == date(2026, 7, 2)


def test_order_update_invalid_state():
    with pytest.raises(ValidationError):
        ProductOrderUpdate(state="BOGUS")


# ── ProductOrder (full read model) ──────────────────────────────────────────────


def test_product_order_full_model(requestor_party_id, supplier_party_id, product_id):
    now = datetime.now(timezone.utc)
    order_id = uuid.uuid4()
    order = ProductOrder(
        id=order_id,
        order_number="SLI-20260601-1234",
        requestor_party_id=requestor_party_id,
        supplier_party_id=supplier_party_id,
        items=[
            ProductOrderItem(
                id=uuid.uuid4(),
                order_id=order_id,
                product_id=product_id,
                product_name="Router X100",
                quantity=10,
                unit_price=25.5,
            )
        ],
        state=OrderState.ACKNOWLEDGED,
        total_amount=255.0,
        currency="USD",
        requested_delivery_date=date(2026, 7, 1),
        actual_delivery_date=None,
        notes=None,
        tenant_id="tenant-test-001",
        created_at=now,
        updated_at=now,
    )
    assert order.total_amount == 255.0
    assert order.state is OrderState.ACKNOWLEDGED
    assert order.items[0].quantity == 10


def test_product_order_state_coerced_from_string(requestor_party_id, supplier_party_id):
    now = datetime.now(timezone.utc)
    order = ProductOrder(
        id=uuid.uuid4(),
        order_number="SLI-1",
        requestor_party_id=requestor_party_id,
        supplier_party_id=supplier_party_id,
        items=[],
        state="COMPLETED",
        total_amount=0.0,
        currency="USD",
        requested_delivery_date=date(2026, 7, 1),
        actual_delivery_date=None,
        notes=None,
        tenant_id="t",
        created_at=now,
        updated_at=now,
    )
    assert order.state is OrderState.COMPLETED
