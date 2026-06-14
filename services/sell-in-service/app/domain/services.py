"""Domain service layer for sell-in-service (TMF622)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import structlog
from fastapi import HTTPException, status

from app.domain.models import OrderState, ProductOrder, ProductOrderCreate
from app.infrastructure.db.repository import ProductOrderRepository
from telco_common.events.cloudevents import Topics, make_event
from telco_common.events.schemas.sales_events import SellInDeliveredData, SellInOrderedData
from telco_common.kafka.producer_factory import KafkaProducer

log = structlog.get_logger(__name__)


async def create_order(
    data: ProductOrderCreate,
    tenant_id: str,
    repo: ProductOrderRepository,
    kafka_producer: KafkaProducer,
) -> ProductOrder:
    """Persist a new sell-in order and publish telco.sales.sellin.ordered event."""
    order = await repo.create(data, tenant_id)

    event_data = SellInOrderedData(
        order_id=str(order.id),
        order_number=order.order_number,
        requestor_party_id=str(order.requestor_party_id),
        supplier_party_id=str(order.supplier_party_id),
        items=[
            {
                "product_id": str(item.product_id),
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in order.items
        ],
        requested_delivery_date=order.requested_delivery_date.isoformat(),
        tenant_id=tenant_id,
    )
    event = make_event(
        event_type=Topics.SALES_SELLIN_ORDERED,
        source_service="sell-in-service",
        tenant_id=tenant_id,
        data=event_data,
    )
    await kafka_producer.send(
        topic=Topics.SALES_SELLIN_ORDERED,
        event=event,
        key=str(order.requestor_party_id),
    )
    log.info(
        "sellin.order.created_event_published",
        order_id=str(order.id),
        order_number=order.order_number,
    )
    return order


async def complete_order(
    order_id: uuid.UUID,
    actual_delivery_date: date,
    tenant_id: str,
    repo: ProductOrderRepository,
    kafka_producer: KafkaProducer,
) -> ProductOrder:
    """Mark an order as COMPLETED and publish telco.sales.sellin.delivered event."""
    order = await repo.get_by_id(order_id, tenant_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ProductOrder '{order_id}' not found",
        )
    if order.state == OrderState.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot complete a cancelled order",
        )
    if order.state == OrderState.COMPLETED:
        return order

    updated = await repo.update_state(
        order_id=order_id,
        tenant_id=tenant_id,
        state=OrderState.COMPLETED,
        actual_delivery_date=actual_delivery_date,
    )
    assert updated is not None

    event_data = SellInDeliveredData(
        order_id=str(updated.id),
        order_number=updated.order_number,
        delivered_at=datetime.now(UTC).isoformat(),
        delivered_items=[
            {
                "product_id": str(item.product_id),
                "product_name": item.product_name,
                "quantity": item.quantity,
            }
            for item in updated.items
        ],
        destination_location_id=str(updated.destination_location_id or updated.requestor_party_id),
        tenant_id=tenant_id,
    )
    event = make_event(
        event_type=Topics.SALES_SELLIN_DELIVERED,
        source_service="sell-in-service",
        tenant_id=tenant_id,
        data=event_data,
    )
    await kafka_producer.send(
        topic=Topics.SALES_SELLIN_DELIVERED,
        event=event,
        key=str(updated.requestor_party_id),
    )
    log.info(
        "sellin.order.completed_event_published",
        order_id=str(updated.id),
        order_number=updated.order_number,
    )
    return updated


async def cancel_order(
    order_id: uuid.UUID,
    tenant_id: str,
    repo: ProductOrderRepository,
    kafka_producer: KafkaProducer,
) -> ProductOrder:
    """Cancel an order if it is not yet COMPLETED."""
    order = await repo.get_by_id(order_id, tenant_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ProductOrder '{order_id}' not found",
        )
    if order.state == OrderState.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot cancel a completed order",
        )
    if order.state == OrderState.CANCELLED:
        return order

    updated = await repo.update_state(
        order_id=order_id,
        tenant_id=tenant_id,
        state=OrderState.CANCELLED,
    )
    assert updated is not None
    log.info("sellin.order.cancelled", order_id=str(order_id))
    return updated
