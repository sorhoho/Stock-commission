"""Return event consumer — claws back commission when a return is approved."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repository import CommissionEventRepository, CommissionStatementRepository
from telco_common.events import Topics, make_event
from telco_common.events.schemas.sales_events import SalesReturnProcessedData
from telco_common.kafka import KafkaProducer

logger = structlog.get_logger(__name__)


async def handle_return_processed(
    event: dict,
    session: AsyncSession,
    kafka_producer: KafkaProducer,
) -> None:
    """Create a negative CommissionEvent for each original event tied to the returned sale."""
    try:
        data = SalesReturnProcessedData.model_validate(event["data"])
    except Exception as exc:
        logger.error("Invalid SalesReturnProcessedData payload", error=str(exc))
        return

    tenant_id = event.get("tenantid", "")
    original_txn_id = data.original_transaction_id
    if not original_txn_id:
        logger.info("Return has no original_transaction_id — no clawback needed")
        return

    event_repo = CommissionEventRepository(session)
    stmt_repo = CommissionStatementRepository(session)

    originals = await event_repo.list_by_source_transaction(original_txn_id, tenant_id)
    if not originals:
        logger.info(
            "No commission events for original transaction",
            original_transaction_id=original_txn_id,
        )
        return

    now = datetime.now(UTC)
    clawback_ref = f"CLAWBACK-{data.return_number}"

    from telco_common.events.schemas.commission_events import CommissionEventCalculatedData

    for orig in originals:
        clawback_amount = -abs(orig.commission_amount)
        clawback_event = await event_repo.create(
            source_transaction_id=clawback_ref,
            party_id=orig.party_id,
            agreement_id=orig.agreement_id,
            rule_id=orig.rule_id,
            product_id=orig.product_id,
            quantity=-abs(orig.quantity),
            base_amount=-abs(orig.base_amount),
            commission_amount=clawback_amount,
            currency=orig.currency,
            calculation_date=now,
            tenant_id=tenant_id,
        )
        await stmt_repo.add_commission_to_draft(
            party_id=orig.party_id,
            year=now.year,
            month=now.month,
            commission_amount=clawback_amount,
            currency=orig.currency,
            tenant_id=tenant_id,
        )
        clawback_data = CommissionEventCalculatedData(
            commission_event_id=str(clawback_event.id),
            source_transaction_id=clawback_ref,
            party_id=str(orig.party_id),
            party_type="DEALER",
            agreement_id=str(orig.agreement_id),
            rule_id=str(orig.rule_id),
            product_id=str(orig.product_id),
            quantity=-abs(orig.quantity),
            base_amount=-abs(orig.base_amount),
            commission_amount=clawback_amount,
            commission_rate=0.0,
            currency=orig.currency,
            calculation_date=now.isoformat(),
            tenant_id=tenant_id,
        )
        ce = make_event(
            Topics.COMMISSION_EVENT_CALCULATED,
            "commission-calculation-service",
            tenant_id,
            clawback_data,
        )
        await kafka_producer.send(Topics.COMMISSION_EVENT_CALCULATED, ce, key=str(orig.party_id))

    logger.info(
        "Commission clawback processed",
        return_number=data.return_number,
        original_transaction_id=original_txn_id,
        clawback_count=len(originals),
        tenant_id=tenant_id,
    )
