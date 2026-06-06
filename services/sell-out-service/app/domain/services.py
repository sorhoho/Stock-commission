"""Domain service layer for sell-out-service business logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
import structlog

from app.domain.models import (
    ReturnStatus,
    ReturnTransaction,
    ReturnTransactionCreate,
    SaleStatus,
    SaleTransaction,
    SaleTransactionCreate,
)
from app.infrastructure.db.repository import ReturnRepository, SaleTransactionRepository
from telco_common.events.cloudevents import Topics, make_event
from telco_common.events.schemas.sales_events import (
    SaleTransactionItem as EventSaleTransactionItem,
    SellOutCompletedData,
)
from telco_common.exceptions import ConflictException, NotFoundException, UnprocessableEntityException

log = structlog.get_logger(__name__)


async def _check_stock_availability(
    items: list,
    tenant_id: str,
    stock_query_url: str,
) -> None:
    """Raise UnprocessableEntityException if any item has insufficient stock."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        for item in items:
            try:
                resp = await client.get(
                    f"{stock_query_url}/api/v1/inventory/stockAvailability"
                    f"/{item.product_id}",
                    headers={"X-Tenant-ID": tenant_id},
                )
                if resp.status_code == 404:
                    raise UnprocessableEntityException(
                        f"No stock record for product {item.product_id}"
                    )
                resp.raise_for_status()
                available = resp.json().get("net_quantity", 0)
                if available < item.quantity:
                    raise UnprocessableEntityException(
                        f"Insufficient stock for product {item.product_id}: "
                        f"available={available}, requested={item.quantity}"
                    )
            except httpx.HTTPStatusError:
                raise
            except httpx.RequestError as exc:
                log.warning("stock_check.unavailable", error=str(exc))
                # Fail open on connectivity errors to avoid blocking sales when stock-query is down


async def create_sale_transaction(
    data: SaleTransactionCreate,
    tenant_id: str,
    correlation_id: str,
    repo: SaleTransactionRepository,
    kafka_producer,
    stock_query_url: str | None = None,
) -> SaleTransaction:
    """
    Create a new sell-out transaction.

    Steps:
    1. Pre-sale stock availability check (if stock_query_url provided)
    2. Calculate total_amount from line items
    3. Generate a unique transaction_number
    4. Persist sale_transaction + sale_transaction_items (status=COMPLETED)
    5. Build SellOutCompletedData event payload
    6. Publish event to SALES_SELLOUT_COMPLETED topic
    7. Return created SaleTransaction domain object
    """
    # 1. Stock availability check
    if stock_query_url:
        await _check_stock_availability(data.items, tenant_id, stock_query_url)

    # 2. Calculate total amount
    total_amount = sum(
        (item.unit_price - item.discount_amount) * item.quantity
        for item in data.items
    )
    total_amount = round(total_amount, 2)

    # 2. Generate transaction number
    transaction_number = (
        f"TXN-{datetime.now(UTC).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    )

    log.info(
        "sale_transaction.creating",
        transaction_number=transaction_number,
        dealer_party_id=str(data.dealer_party_id),
        total_amount=total_amount,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    # 3. Persist
    created = await repo.create(
        transaction_data=data,
        items_data=data.items,
        tenant_id=tenant_id,
        transaction_number=transaction_number,
        total_amount=total_amount,
    )

    # 4. Build event payload
    sale_date = (
        data.sale_date.isoformat()
        if data.sale_date
        else datetime.now(UTC).isoformat()
    )
    event_items = [
        EventSaleTransactionItem(
            product_id=str(item.product_id),
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            serial_numbers=item.serial_numbers,
            commission_eligible=item.commission_eligible,
        )
        for item in data.items
    ]
    sell_out_data = SellOutCompletedData(
        transaction_id=str(created.id),
        transaction_number=transaction_number,
        dealer_party_id=str(data.dealer_party_id),
        dealer_name="",  # enriched downstream via party-service
        channel=data.channel.value,
        sale_date=sale_date,
        total_amount=total_amount,
        currency=created.currency,
        items=event_items,
        tenant_id=tenant_id,
    )

    # 5. Publish Kafka event
    event = make_event(
        Topics.SALES_SELLOUT_COMPLETED,
        "sell-out-service",
        tenant_id,
        sell_out_data,
        correlation_id,
    )
    await kafka_producer.send(
        Topics.SALES_SELLOUT_COMPLETED,
        event,
        key=str(data.dealer_party_id),
    )

    log.info(
        "sale_transaction.created",
        transaction_id=str(created.id),
        transaction_number=transaction_number,
        tenant_id=tenant_id,
    )

    return created


async def reverse_transaction(
    transaction_id: str,
    reason: str,
    tenant_id: str,
    repo: SaleTransactionRepository,
    kafka_producer,
) -> SaleTransaction:
    """
    Reverse a completed sale transaction.

    Steps:
    1. Fetch transaction, validate it exists and is COMPLETED
    2. Update status to REVERSED
    3. Publish SellOutReversedData event
    4. Return updated transaction
    """
    txn_uuid = uuid.UUID(transaction_id)
    existing = await repo.get_by_id(txn_uuid, tenant_id)
    if existing is None:
        raise NotFoundException("SaleTransaction", transaction_id)

    # 1. Validate status
    if existing.status != SaleStatus.COMPLETED:
        raise ConflictException(
            f"Cannot reverse transaction '{transaction_id}': "
            f"current status is '{existing.status}', expected '{SaleStatus.COMPLETED}'"
        )

    # 2. Update to REVERSED
    updated = await repo.update_status(txn_uuid, SaleStatus.REVERSED, tenant_id)
    if updated is None:
        raise NotFoundException("SaleTransaction", transaction_id)

    log.info(
        "sale_transaction.reversed",
        transaction_id=transaction_id,
        reason=reason,
        tenant_id=tenant_id,
    )

    # 3. Publish reversal event
    from telco_common.events.schemas.sales_events import SellOutReversedData

    reversal_data = SellOutReversedData(
        transaction_id=transaction_id,
        transaction_number=updated.transaction_number,
        dealer_party_id=str(updated.dealer_party_id),
        reversal_reason=reason,
        reversed_at=datetime.now(UTC).isoformat(),
        tenant_id=tenant_id,
    )
    event = make_event(
        Topics.SALES_SELLOUT_REVERSED,
        "sell-out-service",
        tenant_id,
        reversal_data,
        None,
    )
    await kafka_producer.send(
        Topics.SALES_SELLOUT_REVERSED,
        event,
        key=str(updated.dealer_party_id),
    )

    return updated


async def process_return(
    return_id: uuid.UUID,
    action: str,
    tenant_id: str,
    repo: ReturnRepository,
    kafka_producer,
) -> ReturnTransaction:
    """Approve or reject a return. On approval, publishes SALES_RETURN_PROCESSED."""
    ret = await repo.get_by_id(return_id, tenant_id)
    if ret is None:
        raise NotFoundException("ReturnTransaction", str(return_id))
    if ret.status != ReturnStatus.PENDING:
        raise ConflictException(
            f"Cannot {action} return '{return_id}': status is '{ret.status}'"
        )

    new_status = ReturnStatus.APPROVED if action == "approve" else ReturnStatus.REJECTED
    updated = await repo.update_status(return_id, tenant_id, new_status)
    if updated is None:
        raise NotFoundException("ReturnTransaction", str(return_id))

    if new_status == ReturnStatus.APPROVED:
        from telco_common.events.schemas.sales_events import SalesReturnProcessedData
        return_data = SalesReturnProcessedData(
            return_id=str(updated.id),
            return_number=updated.return_number,
            original_transaction_id=str(updated.original_transaction_id) if updated.original_transaction_id else None,
            return_reason=updated.return_reason,
            returned_by=updated.returned_by,
            returned_at=updated.returned_at,
            tenant_id=tenant_id,
        )
        event = make_event(
            Topics.SALES_RETURN_PROCESSED,
            "sell-out-service",
            tenant_id,
            return_data,
            None,
        )
        await kafka_producer.send(Topics.SALES_RETURN_PROCESSED, event, key=tenant_id)

    log.info(
        "return_transaction.processed",
        return_id=str(return_id),
        action=action,
        tenant_id=tenant_id,
    )
    return updated
