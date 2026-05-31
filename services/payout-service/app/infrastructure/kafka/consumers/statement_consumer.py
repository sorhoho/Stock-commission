"""Consumes commission.statement.confirmed events to auto-create payout requests."""

from __future__ import annotations

from datetime import date

import structlog

from telco_common.events.schemas.commission_events import CommissionStatementConfirmedData

logger = structlog.get_logger(__name__)


async def handle_statement_confirmed(
    event: dict,
    repo,
    kafka_producer,
) -> None:
    try:
        data = CommissionStatementConfirmedData.model_validate(event["data"])
    except Exception as exc:
        logger.error("Invalid CommissionStatementConfirmedData", error=str(exc))
        return

    from app.domain.services import create_payout_request

    scheduled = date(data.period_year, data.period_month, 28)

    await create_payout_request(
        party_id=data.party_id,
        statement_id=data.statement_id,
        amount=data.total_commission,
        currency=data.currency,
        payment_method="BANK_TRANSFER",
        bank_account_ref="00000000",  # Fetched from party profile in full implementation
        scheduled_date=scheduled,
        tenant_id=data.tenant_id,
        repo=repo,
        kafka_producer=kafka_producer,
    )
    logger.info("Payout request created from statement", statement_id=data.statement_id)
