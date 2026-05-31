"""Kafka consumer for telco.sales.sellout.completed events.

Upserts PerformanceMeasurement records for:
- MONTHLY_SELL_OUT_UNITS  (sum of item quantities per dealer per month)
- MONTHLY_SELL_OUT_REVENUE (total_amount per dealer per month)

After upserting, checks whether any ACTIVE targets have been met and
updates their TargetStatus to ACHIEVED or MISSED accordingly.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date
from typing import Any

import structlog

from telco_common.events.cloudevents import Topics
from telco_common.events.schemas.sales_events import SellOutCompletedData
from telco_common.kafka.consumer_factory import KafkaConsumer
from telco_common.kafka.producer_factory import KafkaProducer

log = structlog.get_logger(__name__)

# Well-known KPI spec names — resolved to UUIDs at first encounter via DB lookup.
KPI_UNITS_NAME = "MONTHLY_SELL_OUT_UNITS"
KPI_REVENUE_NAME = "MONTHLY_SELL_OUT_REVENUE"


async def _handle_sell_out_event(
    event: dict[str, Any],
    kafka_producer: KafkaProducer,
) -> None:
    """Process a single sell-out completed CloudEvent."""
    from app.infrastructure.db.session import AsyncSessionLocal
    from app.infrastructure.db.repository import (
        IndicatorSpecRepository,
        MeasurementRepository,
        TargetRepository,
    )
    from app.domain.models import TargetStatus

    raw_data = event.get("data", {})
    data = SellOutCompletedData.model_validate(raw_data)

    # Derive period as the first day of the sale month
    sale_date = date.fromisoformat(data.sale_date[:10])
    period = date(sale_date.year, sale_date.month, 1)
    party_id = uuid.UUID(data.dealer_party_id)
    tenant_id = data.tenant_id
    event_id = event.get("id", data.transaction_id)

    total_units = sum(item.quantity for item in data.items)
    total_revenue = data.total_amount

    async with AsyncSessionLocal() as session:
        spec_repo = IndicatorSpecRepository(session)
        meas_repo = MeasurementRepository(session)
        target_repo = TargetRepository(session)

        # Resolve KPI specs by name
        all_specs = await spec_repo.list_all(tenant_id)
        spec_by_name = {s.name: s for s in all_specs}

        units_spec = spec_by_name.get(KPI_UNITS_NAME)
        revenue_spec = spec_by_name.get(KPI_REVENUE_NAME)

        measurements = []

        if units_spec:
            m = await meas_repo.upsert(
                party_id=party_id,
                kpi_spec_id=units_spec.id,
                period=period,
                measured_value=float(total_units),
                source_event_id=event_id,
                tenant_id=tenant_id,
            )
            measurements.append((units_spec, m))

        if revenue_spec:
            m = await meas_repo.upsert(
                party_id=party_id,
                kpi_spec_id=revenue_spec.id,
                period=period,
                measured_value=total_revenue,
                source_event_id=event_id,
                tenant_id=tenant_id,
            )
            measurements.append((revenue_spec, m))

        # Check targets for each updated measurement
        for spec, measurement in measurements:
            active_targets = await target_repo.get_active_for_party_and_spec(
                party_id=party_id,
                kpi_spec_id=spec.id,
                period=period,
                tenant_id=tenant_id,
            )
            for target in active_targets:
                new_status: TargetStatus | None = None
                if measurement.measured_value >= target.target_value:
                    new_status = TargetStatus.ACHIEVED
                elif period > target.period_end:
                    new_status = TargetStatus.MISSED

                if new_status is not None:
                    await target_repo.update_status(
                        target_id=target.id,
                        status=new_status,
                        tenant_id=tenant_id,
                    )
                    log.info(
                        "target.status_evaluated",
                        target_id=str(target.id),
                        new_status=new_status,
                        measured=measurement.measured_value,
                        target_value=target.target_value,
                    )

        await session.commit()

    log.info(
        "sell_out.processed",
        transaction_id=data.transaction_id,
        dealer_party_id=data.dealer_party_id,
        period=str(period),
    )


async def start_consumer(
    bootstrap_servers: str,
    group_id: str,
    kafka_producer: KafkaProducer,
) -> None:
    """Create and run the KafkaConsumer for sell-out events indefinitely."""
    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        topics=[Topics.SALES_SELLOUT_COMPLETED],
    )
    await consumer.start()
    log.info("sell_out_consumer.started", topic=Topics.SALES_SELLOUT_COMPLETED)

    async def handler(event: dict[str, Any]) -> None:
        await _handle_sell_out_event(event, kafka_producer)

    try:
        await consumer.consume(handler=handler, dlq_producer=kafka_producer)
    finally:
        await consumer.stop()
        log.info("sell_out_consumer.stopped")
