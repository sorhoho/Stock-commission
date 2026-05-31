"""Unit tests for StockReadModel — update_from_adjustment, update_from_transfer, query."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT = "tenant-abc"
PRODUCT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PRODUCT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
LOC_WH = "11111111-1111-1111-1111-111111111111"
LOC_DC = "22222222-2222-2222-2222-222222222222"


def _adjustment_event(
    product_id: str = PRODUCT_A,
    location_id: str = LOC_WH,
    new_quantity: int = 100,
    tenant_id: str = TENANT,
) -> dict:
    return {
        "inventory_id": "inv-001",
        "product_id": product_id,
        "location_id": location_id,
        "previous_quantity": 0,
        "new_quantity": new_quantity,
        "adjustment_reason": "initial_stock",
        "adjusted_by": "admin",
        "tenant_id": tenant_id,
    }


def _transfer_event(
    product_id: str = PRODUCT_A,
    quantity: int = 30,
    source_location_id: str = LOC_WH,
    source_location_type: str = "WAREHOUSE",
    destination_location_id: str = LOC_DC,
    destination_location_type: str = "DISTRIBUTION_CENTER",
    tenant_id: str = TENANT,
) -> dict:
    return {
        "transfer_id": "xfr-001",
        "transfer_order_number": "TO-001",
        "source_location_id": source_location_id,
        "source_location_type": source_location_type,
        "destination_location_id": destination_location_id,
        "destination_location_type": destination_location_type,
        "product_id": product_id,
        "quantity": quantity,
        "completed_at": datetime.now(UTC).isoformat(),
        "tenant_id": tenant_id,
    }


# ---------------------------------------------------------------------------
# Tests: update_from_adjustment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_from_adjustment_sets_quantity(stock_read_model):
    """Adjustment event should persist new_quantity in Redis hash."""
    await stock_read_model.update_from_adjustment(_adjustment_event(new_quantity=50))

    result = await stock_read_model.get_availability(TENANT, PRODUCT_A, LOC_WH)
    assert result is not None
    assert result["available_quantity"] == 50
    assert result["tenant_id"] == TENANT


@pytest.mark.asyncio
async def test_update_from_adjustment_overwrites_quantity(stock_read_model):
    """A second adjustment event should overwrite the previous quantity."""
    await stock_read_model.update_from_adjustment(_adjustment_event(new_quantity=80))
    await stock_read_model.update_from_adjustment(_adjustment_event(new_quantity=45))

    result = await stock_read_model.get_availability(TENANT, PRODUCT_A, LOC_WH)
    assert result["available_quantity"] == 45


@pytest.mark.asyncio
async def test_update_from_adjustment_preserves_reserved_quantity(stock_read_model):
    """Adjustment must not reset an existing reserved_quantity."""
    # Seed a key with a reserved_quantity already set
    key = stock_read_model._key(TENANT, PRODUCT_A, LOC_WH)
    await stock_read_model._redis.hset(  # type: ignore[attr-defined]
        key,
        mapping={
            "product_name": "SIM Card",
            "location_type": "WAREHOUSE",
            "available_quantity": 100,
            "reserved_quantity": 20,
            "last_updated": datetime.now(UTC).isoformat(),
        },
    )

    await stock_read_model.update_from_adjustment(_adjustment_event(new_quantity=120))

    result = await stock_read_model.get_availability(TENANT, PRODUCT_A, LOC_WH)
    assert result["available_quantity"] == 120
    assert result["reserved_quantity"] == 20  # preserved


@pytest.mark.asyncio
async def test_update_from_adjustment_bad_data_does_not_raise(stock_read_model):
    """Malformed event data should be swallowed (logged) without raising."""
    # missing required fields
    await stock_read_model.update_from_adjustment({"garbage": True})
    # no exception → pass


# ---------------------------------------------------------------------------
# Tests: update_from_transfer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transfer_decrements_source_increments_destination(stock_read_model):
    """Transfer should decrement source and increment destination by the quantity."""
    # Seed source
    await stock_read_model.update_from_adjustment(_adjustment_event(location_id=LOC_WH, new_quantity=100))

    await stock_read_model.update_from_transfer(_transfer_event(quantity=30))

    src = await stock_read_model.get_availability(TENANT, PRODUCT_A, LOC_WH)
    dst = await stock_read_model.get_availability(TENANT, PRODUCT_A, LOC_DC)

    assert src is not None
    assert src["available_quantity"] == 70

    assert dst is not None
    assert dst["available_quantity"] == 30


@pytest.mark.asyncio
async def test_transfer_creates_destination_if_missing(stock_read_model):
    """If destination key doesn't exist, transfer should bootstrap it."""
    # No seed for destination
    await stock_read_model.update_from_adjustment(_adjustment_event(location_id=LOC_WH, new_quantity=50))

    await stock_read_model.update_from_transfer(_transfer_event(quantity=10))

    dst = await stock_read_model.get_availability(TENANT, PRODUCT_A, LOC_DC)
    assert dst is not None
    assert dst["available_quantity"] == 10
    assert dst["location_type"] == "DISTRIBUTION_CENTER"


@pytest.mark.asyncio
async def test_transfer_source_quantity_floors_at_zero(stock_read_model):
    """Source quantity must not go negative — floor at 0."""
    await stock_read_model.update_from_adjustment(_adjustment_event(location_id=LOC_WH, new_quantity=5))

    await stock_read_model.update_from_transfer(_transfer_event(quantity=100))

    src = await stock_read_model.get_availability(TENANT, PRODUCT_A, LOC_WH)
    assert src["available_quantity"] == 0  # floored, not negative


@pytest.mark.asyncio
async def test_transfer_bad_data_does_not_raise(stock_read_model):
    """Malformed transfer event data should be swallowed without raising."""
    await stock_read_model.update_from_transfer({"invalid": "payload"})
    # no exception → pass


# ---------------------------------------------------------------------------
# Tests: query filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_returns_all_items_for_tenant(stock_read_model):
    """Query without filters should return all items for the tenant."""
    await stock_read_model.update_from_adjustment(_adjustment_event(product_id=PRODUCT_A, location_id=LOC_WH, new_quantity=100))
    await stock_read_model.update_from_adjustment(_adjustment_event(product_id=PRODUCT_B, location_id=LOC_DC, new_quantity=200))

    results = await stock_read_model.query(tenant_id=TENANT)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_query_filters_by_product_id(stock_read_model):
    """Query with product_id filter should return only matching items."""
    await stock_read_model.update_from_adjustment(_adjustment_event(product_id=PRODUCT_A, location_id=LOC_WH, new_quantity=10))
    await stock_read_model.update_from_adjustment(_adjustment_event(product_id=PRODUCT_B, location_id=LOC_DC, new_quantity=20))

    results = await stock_read_model.query(tenant_id=TENANT, product_id=PRODUCT_A)
    assert all(r["product_id"] == PRODUCT_A for r in results)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_query_filters_by_min_quantity(stock_read_model):
    """Query with min_quantity should exclude items below the threshold."""
    await stock_read_model.update_from_adjustment(_adjustment_event(product_id=PRODUCT_A, location_id=LOC_WH, new_quantity=5))
    await stock_read_model.update_from_adjustment(_adjustment_event(product_id=PRODUCT_B, location_id=LOC_DC, new_quantity=50))

    results = await stock_read_model.query(tenant_id=TENANT, min_quantity=10)
    assert all(r["available_quantity"] >= 10 for r in results)
    assert len(results) == 1
    assert results[0]["available_quantity"] == 50


@pytest.mark.asyncio
async def test_query_does_not_return_other_tenant_data(stock_read_model):
    """Data for tenant-A must not appear in results for tenant-B."""
    await stock_read_model.update_from_adjustment(
        _adjustment_event(tenant_id="tenant-a", product_id=PRODUCT_A, location_id=LOC_WH, new_quantity=100)
    )
    await stock_read_model.update_from_adjustment(
        _adjustment_event(tenant_id="tenant-b", product_id=PRODUCT_A, location_id=LOC_WH, new_quantity=50)
    )

    results_a = await stock_read_model.query(tenant_id="tenant-a")
    results_b = await stock_read_model.query(tenant_id="tenant-b")

    assert all(r["tenant_id"] == "tenant-a" for r in results_a)
    assert all(r["tenant_id"] == "tenant-b" for r in results_b)


@pytest.mark.asyncio
async def test_get_availability_returns_none_for_missing_key(stock_read_model):
    """get_availability should return None when key does not exist."""
    result = await stock_read_model.get_availability(TENANT, PRODUCT_A, LOC_WH)
    assert result is None
