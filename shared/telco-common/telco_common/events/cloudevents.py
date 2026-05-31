"""CloudEvents 1.0 envelope factory and base event models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class CloudEvent(BaseModel, Generic[T]):
    """CloudEvents 1.0 spec envelope."""

    specversion: str = "1.0"
    type: str
    source: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    datacontenttype: str = "application/json"
    tenantid: str
    correlationid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: T


def make_event(
    event_type: str,
    source_service: str,
    tenant_id: str,
    data: T,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build a serialisable CloudEvents envelope dict."""
    return {
        "specversion": "1.0",
        "type": event_type,
        "source": f"/telco/{source_service}",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "tenantid": tenant_id,
        "correlationid": correlation_id or str(uuid.uuid4()),
        "data": data.model_dump(mode="json") if isinstance(data, BaseModel) else data,
    }


# Topic constants
class Topics:
    INVENTORY_STOCK_TRANSFERRED = "telco.inventory.stock.transferred"
    INVENTORY_STOCK_ADJUSTED = "telco.inventory.stock.adjusted"
    INVENTORY_STOCK_RESERVED = "telco.inventory.stock.reserved"

    SALES_SELLOUT_COMPLETED = "telco.sales.sellout.completed"
    SALES_SELLOUT_REVERSED = "telco.sales.sellout.reversed"
    SALES_SELLIN_ORDERED = "telco.sales.sellin.ordered"
    SALES_SELLIN_DELIVERED = "telco.sales.sellin.delivered"

    COMMISSION_EVENT_CALCULATED = "telco.commission.event.calculated"
    COMMISSION_STATEMENT_CONFIRMED = "telco.commission.statement.confirmed"

    PAYOUT_REQUEST_CREATED = "telco.payout.request.created"
    PAYOUT_REQUEST_COMPLETED = "telco.payout.request.completed"

    PARTY_DEALER_ONBOARDED = "telco.party.dealer.onboarded"
    PERFORMANCE_MEASUREMENT_RECORDED = "telco.performance.measurement.recorded"
