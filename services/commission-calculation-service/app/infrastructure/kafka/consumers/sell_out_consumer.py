"""Sell-out event consumer — the primary trigger for commission calculation."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rule_evaluator import (
    calculate_commission,
    calculate_tiered_commission,
    find_applicable_rule,
)
from app.infrastructure.db.models import CommissionEvent, CommissionStatement, ProcessedEventLog
from app.infrastructure.db.repository import (
    CommissionEventRepository,
    CommissionStatementRepository,
    ProcessedEventLogRepository,
)
from telco_common.events.schemas.sales_events import SellOutCompletedData
from telco_common.events import Topics, make_event
from telco_common.kafka import KafkaProducer

logger = structlog.get_logger(__name__)


async def _fetch_agreement_with_rules(party_id: str, tenant_id: str, rules_service_url: str) -> dict | None:
    """Fetch active commission agreement + rules from commission-rules-service."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{rules_service_url}/api/v1/agreementManagement/agreement/party/{party_id}/active",
                headers={"X-Tenant-ID": tenant_id},
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch agreement", party_id=party_id, error=str(exc))
        return None


async def handle_sell_out_completed(
    event: dict,
    session: AsyncSession,
    kafka_producer: KafkaProducer,
    rules_service_url: str,
) -> None:
    try:
        data = SellOutCompletedData.model_validate(event["data"])
    except Exception as exc:
        logger.error("Invalid SellOutCompletedData payload", error=str(exc))
        return

    tenant_id = event.get("tenantid", "")
    correlation_id = event.get("correlationid", "")

    agreement_data = await _fetch_agreement_with_rules(data.dealer_party_id, tenant_id, rules_service_url)
    if not agreement_data:
        logger.warning("No active agreement found for dealer", dealer_party_id=data.dealer_party_id)
        return

    agreement_id = agreement_data["id"]
    rules_raw = agreement_data.get("rules", [])

    event_repo = CommissionEventRepository(session)
    stmt_repo = CommissionStatementRepository(session)
    log_repo = ProcessedEventLogRepository(session)

    from telco_common.events.schemas.commission_events import CommissionEventCalculatedData
    from datetime import UTC, datetime

    for item in data.items:
        if not item.commission_eligible:
            continue

        # Idempotency guard
        if await log_repo.is_processed(data.transaction_id, agreement_id):
            logger.info("Already processed", transaction_id=data.transaction_id, agreement_id=agreement_id)
            continue

        # Build rule objects
        from app.domain.rule_evaluator import CommissionRule, CommissionType
        rules = []
        for r in rules_raw:
            try:
                rules.append(CommissionRule(
                    id=r["id"],
                    product_category=r.get("product_category", "*"),
                    channel_type=r.get("channel_type"),
                    tier_min_qty=r.get("tier_min_qty", 0),
                    tier_max_qty=r.get("tier_max_qty"),
                    commission_type=CommissionType(r["commission_type"]),
                    commission_value=float(r["commission_value"]),
                    currency=r.get("currency", "THB"),
                    priority=r.get("priority", 100),
                ))
            except (KeyError, ValueError):
                continue

        matched_rule = find_applicable_rule(rules, item.product_name, data.channel, item.quantity)
        if not matched_rule:
            logger.info("No matching rule for item", product=item.product_name, channel=data.channel)
            continue

        if matched_rule.commission_type == CommissionType.TIERED:
            commission_amount = calculate_tiered_commission(
                rules, item.product_name, data.channel, item.quantity
            )
        else:
            commission_amount = calculate_commission(matched_rule, item.quantity, item.unit_price)
        base_amount = item.unit_price * item.quantity
        now_str = datetime.now(UTC).isoformat()

        # Persist commission event
        created_event = await event_repo.create(
            source_transaction_id=data.transaction_id,
            party_id=data.dealer_party_id,
            agreement_id=agreement_id,
            rule_id=matched_rule.id,
            product_id=item.product_id,
            quantity=item.quantity,
            base_amount=base_amount,
            commission_amount=commission_amount,
            currency=data.currency,
            calculation_date=datetime.now(UTC),
            tenant_id=tenant_id,
        )

        # Mark processed
        await log_repo.mark_processed(data.transaction_id, agreement_id)

        # Publish calculated event
        calculated_data = CommissionEventCalculatedData(
            commission_event_id=str(created_event.id),
            source_transaction_id=data.transaction_id,
            party_id=data.dealer_party_id,
            party_type="DEALER",
            agreement_id=agreement_id,
            rule_id=matched_rule.id,
            product_id=item.product_id,
            quantity=item.quantity,
            base_amount=base_amount,
            commission_amount=commission_amount,
            commission_rate=matched_rule.commission_value,
            currency=data.currency,
            calculation_date=now_str,
            tenant_id=tenant_id,
        )
        calc_event = make_event(
            Topics.COMMISSION_EVENT_CALCULATED,
            "commission-calculation-service",
            tenant_id,
            calculated_data,
            correlation_id,
        )
        await kafka_producer.send(Topics.COMMISSION_EVENT_CALCULATED, calc_event, key=data.dealer_party_id)

        # Upsert monthly statement
        sale_month = datetime.fromisoformat(data.sale_date).month if hasattr(data, 'sale_date') else datetime.now(UTC).month
        sale_year = datetime.fromisoformat(data.sale_date).year if hasattr(data, 'sale_date') else datetime.now(UTC).year
        await stmt_repo.add_commission_to_draft(
            party_id=data.dealer_party_id,
            year=sale_year,
            month=sale_month,
            commission_amount=commission_amount,
            currency=data.currency,
            tenant_id=tenant_id,
        )

        logger.info(
            "Commission calculated",
            transaction_id=data.transaction_id,
            dealer=data.dealer_party_id,
            amount=commission_amount,
        )
