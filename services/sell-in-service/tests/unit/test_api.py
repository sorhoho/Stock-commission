"""Unit tests for sell-in-service API handlers."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.models import (
    OrderState,
    ProductOrder,
    ProductOrderCreate,
    ProductOrderItem,
    ProductOrderItemCreate,
    ProductOrderUpdate,
)
from telco_common.exceptions import NotFoundException

pytestmark = pytest.mark.asyncio

TENANT = "tenant-test-001"
REQUESTOR = uuid.uuid4()
SUPPLIER = uuid.uuid4()
PRODUCT = uuid.uuid4()


def _make_order(**overrides) -> ProductOrder:
    now = datetime.now(UTC)
    order_id = uuid.uuid4()
    defaults = dict(
        id=order_id,
        order_number="ORD-20260101-0001",
        requestor_party_id=REQUESTOR,
        supplier_party_id=SUPPLIER,
        items=[
            ProductOrderItem(
                id=uuid.uuid4(),
                order_id=order_id,
                product_id=PRODUCT,
                product_name="SIM Card",
                quantity=10,
                unit_price=5.0,
            )
        ],
        state=OrderState.ACKNOWLEDGED,
        total_amount=50.0,
        currency="USD",
        requested_delivery_date=date(2026, 2, 1),
        actual_delivery_date=None,
        notes=None,
        tenant_id=TENANT,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return ProductOrder(**defaults)


def _make_create() -> ProductOrderCreate:
    return ProductOrderCreate(
        requestor_party_id=REQUESTOR,
        supplier_party_id=SUPPLIER,
        items=[ProductOrderItemCreate(product_id=PRODUCT, product_name="SIM", quantity=10, unit_price=5.0)],
        requested_delivery_date=date(2026, 2, 1),
    )


# ── create_product_order ──────────────────────────────────────────────────────


async def test_create_product_order_delegates_to_service():
    from app.api.v1.product_order import create_product_order

    order = _make_order()
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()

    with patch("app.api.v1.product_order.create_order", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = order
        with patch("app.api.v1.product_order.ProductOrderRepository"):
            result = await create_product_order(
                body=_make_create(),
                db=mock_db,
                tenant_id=TENANT,
                kafka_producer=mock_kafka,
            )

    assert result.id == order.id
    mock_svc.assert_awaited_once()


# ── list_product_orders ───────────────────────────────────────────────────────


async def test_list_product_orders_empty():
    from app.api.v1.product_order import list_product_orders

    mock_db = AsyncMock()

    with patch("app.api.v1.product_order.ProductOrderRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = []
        MockRepo.return_value = instance

        result = await list_product_orders(
            db=mock_db, tenant_id=TENANT,
            requestor_party_id=None, state=None,
            from_date=None, to_date=None, page=1, size=20,
        )

    assert result == []
    instance.list_with_filters.assert_awaited_once_with(
        tenant_id=TENANT, requestor_party_id=None, state=None,
        from_date=None, to_date=None, page=1, size=20,
    )


async def test_list_product_orders_with_filters():
    from app.api.v1.product_order import list_product_orders

    order = _make_order()
    mock_db = AsyncMock()

    with patch("app.api.v1.product_order.ProductOrderRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = [order]
        MockRepo.return_value = instance

        result = await list_product_orders(
            db=mock_db, tenant_id=TENANT,
            requestor_party_id=REQUESTOR, state=OrderState.ACKNOWLEDGED,
            from_date=None, to_date=None, page=1, size=20,
        )

    assert len(result) == 1
    kwargs = instance.list_with_filters.call_args.kwargs
    assert kwargs["requestor_party_id"] == REQUESTOR
    assert kwargs["state"] == OrderState.ACKNOWLEDGED


# ── get_product_order ─────────────────────────────────────────────────────────


async def test_get_product_order_found():
    from app.api.v1.product_order import get_product_order

    order = _make_order()
    mock_db = AsyncMock()

    with patch("app.api.v1.product_order.ProductOrderRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = order
        MockRepo.return_value = instance

        result = await get_product_order(order_id=order.id, db=mock_db, tenant_id=TENANT)

    assert result.id == order.id


async def test_get_product_order_not_found():
    from fastapi import HTTPException
    from app.api.v1.product_order import get_product_order

    mock_db = AsyncMock()

    with patch("app.api.v1.product_order.ProductOrderRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(HTTPException) as exc_info:
            await get_product_order(order_id=uuid.uuid4(), db=mock_db, tenant_id=TENANT)

    assert exc_info.value.status_code == 404


# ── update_product_order ──────────────────────────────────────────────────────


async def test_update_product_order_complete():
    from app.api.v1.product_order import update_product_order

    order = _make_order(state=OrderState.COMPLETED)
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    delivery = date(2026, 2, 5)
    body = ProductOrderUpdate(state=OrderState.COMPLETED, actual_delivery_date=delivery)

    with patch("app.api.v1.product_order.complete_order", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = order
        with patch("app.api.v1.product_order.ProductOrderRepository"):
            result = await update_product_order(
                order_id=order.id, body=body,
                db=mock_db, tenant_id=TENANT, kafka_producer=mock_kafka,
            )

    assert result.state == OrderState.COMPLETED
    mock_svc.assert_awaited_once()


async def test_update_product_order_complete_missing_delivery_date():
    from fastapi import HTTPException
    from app.api.v1.product_order import update_product_order

    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = ProductOrderUpdate(state=OrderState.COMPLETED)  # no delivery date

    with patch("app.api.v1.product_order.ProductOrderRepository"):
        with pytest.raises(HTTPException) as exc_info:
            await update_product_order(
                order_id=uuid.uuid4(), body=body,
                db=mock_db, tenant_id=TENANT, kafka_producer=mock_kafka,
            )

    assert exc_info.value.status_code == 422


async def test_update_product_order_cancel():
    from app.api.v1.product_order import update_product_order

    order = _make_order(state=OrderState.CANCELLED)
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = ProductOrderUpdate(state=OrderState.CANCELLED)

    with patch("app.api.v1.product_order.cancel_order", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = order
        with patch("app.api.v1.product_order.ProductOrderRepository"):
            result = await update_product_order(
                order_id=order.id, body=body,
                db=mock_db, tenant_id=TENANT, kafka_producer=mock_kafka,
            )

    assert result.state == OrderState.CANCELLED


async def test_update_product_order_generic_state_change():
    from app.api.v1.product_order import update_product_order

    order = _make_order(state=OrderState.IN_PROGRESS)
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = ProductOrderUpdate(state=OrderState.IN_PROGRESS)

    with patch("app.api.v1.product_order.ProductOrderRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = order
        instance.update_state.return_value = order
        MockRepo.return_value = instance

        result = await update_product_order(
            order_id=order.id, body=body,
            db=mock_db, tenant_id=TENANT, kafka_producer=mock_kafka,
        )

    assert result.state == OrderState.IN_PROGRESS


async def test_update_product_order_not_found():
    from fastapi import HTTPException
    from app.api.v1.product_order import update_product_order

    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = ProductOrderUpdate(state=OrderState.IN_PROGRESS)

    with patch("app.api.v1.product_order.ProductOrderRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(HTTPException) as exc_info:
            await update_product_order(
                order_id=uuid.uuid4(), body=body,
                db=mock_db, tenant_id=TENANT, kafka_producer=mock_kafka,
            )

    assert exc_info.value.status_code == 404


async def test_update_product_order_no_state_returns_existing():
    from app.api.v1.product_order import update_product_order

    order = _make_order()
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = ProductOrderUpdate()  # no state

    with patch("app.api.v1.product_order.ProductOrderRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = order
        MockRepo.return_value = instance

        result = await update_product_order(
            order_id=order.id, body=body,
            db=mock_db, tenant_id=TENANT, kafka_producer=mock_kafka,
        )

    assert result.id == order.id


# ── cancel_product_order ──────────────────────────────────────────────────────


async def test_cancel_product_order_delegates_to_service():
    from app.api.v1.product_order import cancel_product_order

    order = _make_order(state=OrderState.CANCELLED)
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()

    with patch("app.api.v1.product_order.cancel_order", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = order
        with patch("app.api.v1.product_order.ProductOrderRepository"):
            result = await cancel_product_order(
                order_id=order.id, db=mock_db,
                tenant_id=TENANT, kafka_producer=mock_kafka,
            )

    assert result.state == OrderState.CANCELLED
    mock_svc.assert_awaited_once()


# ── dependencies ──────────────────────────────────────────────────────────────


async def test_get_kafka_producer_returns_producer():
    from app.dependencies import get_kafka_producer

    mock_producer = AsyncMock()
    mock_request = MagicMock()
    mock_request.app.state.kafka_producer = mock_producer

    result = await get_kafka_producer(mock_request)
    assert result is mock_producer


async def test_get_kafka_producer_raises_503_when_missing():
    from fastapi import HTTPException
    from app.dependencies import get_kafka_producer

    mock_request = MagicMock()
    mock_request.app.state.kafka_producer = None

    with pytest.raises(HTTPException) as exc_info:
        await get_kafka_producer(mock_request)
    assert exc_info.value.status_code == 503


def test_get_current_tenant_id_returns_value():
    from app.dependencies import get_current_tenant_id

    mock_request = MagicMock()
    mock_request.state.tenant_id = "tenant-abc"
    result = get_current_tenant_id(mock_request)
    assert result == "tenant-abc"


def test_get_current_tenant_id_raises_400_when_missing():
    from fastapi import HTTPException
    from app.dependencies import get_current_tenant_id

    mock_request = MagicMock()
    mock_request.state.tenant_id = ""

    with pytest.raises(HTTPException) as exc_info:
        get_current_tenant_id(mock_request)
    assert exc_info.value.status_code == 400


async def test_get_db_commit_path():
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


async def test_get_db_rollback_on_exception():
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
