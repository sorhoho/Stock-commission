from __future__ import annotations

import random
import uuid
from datetime import UTC, date, datetime

import structlog

from app.infrastructure.db.models import PayoutRequest as PayoutRequestORM
from app.infrastructure.db.repository import PayoutRequestRepository
from telco_common.events import Topics, make_event
from telco_common.events.schemas.commission_events import (
    PayoutRequestCompletedData,
    PayoutRequestCreatedData,
)
from telco_common.kafka import KafkaProducer

logger = structlog.get_logger(__name__)


async def create_payout_request(
    party_id: str,
    statement_id: str,
    amount: float,
    currency: str,
    payment_method: str,
    bank_account_ref: str,
    scheduled_date: date,
    tenant_id: str,
    repo: PayoutRequestRepository,
    kafka_producer: KafkaProducer,
) -> PayoutRequestORM:
    masked_ref = f"****{bank_account_ref[-4:]}" if len(bank_account_ref) >= 4 else "****"
    payout = PayoutRequestORM(
        party_id=uuid.UUID(party_id),
        statement_id=uuid.UUID(statement_id),
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        bank_account_ref=masked_ref,
        status="PENDING",
        scheduled_date=scheduled_date,
        tenant_id=tenant_id,
    )
    created = await repo.create(payout)

    event_data = PayoutRequestCreatedData(
        payout_request_id=str(created.id),
        party_id=party_id,
        statement_id=statement_id,
        amount=amount,
        currency=currency,
        scheduled_date=scheduled_date.isoformat(),
        tenant_id=tenant_id,
    )
    event = make_event(Topics.PAYOUT_REQUEST_CREATED, "payout-service", tenant_id, event_data)
    await kafka_producer.send(Topics.PAYOUT_REQUEST_CREATED, event, key=party_id)
    logger.info("Payout request created", payout_id=str(created.id), party_id=party_id)
    return created


async def process_payout(
    payout_request_id: str,
    tenant_id: str,
    repo: PayoutRequestRepository,
    kafka_producer: KafkaProducer,
) -> PayoutRequestORM:
    request = await repo.get_by_id(payout_request_id)
    if not request:
        from telco_common.exceptions import NotFoundException
        raise NotFoundException("PayoutRequest", payout_request_id)

    # Mock payment gateway call
    success = random.random() > 0.05  # 95% success rate in mock
    external_ref = f"MOCK-{uuid.uuid4().hex[:12].upper()}"

    new_status = "COMPLETED" if success else "FAILED"
    await repo.update_status(payout_request_id, new_status, external_ref)

    event_data = PayoutRequestCompletedData(
        payout_request_id=payout_request_id,
        party_id=str(request.party_id),
        amount=request.amount,
        currency=request.currency,
        external_reference=external_ref,
        processed_at=datetime.now(UTC).isoformat(),
        tenant_id=tenant_id,
    )
    event = make_event(Topics.PAYOUT_REQUEST_COMPLETED, "payout-service", tenant_id, event_data)
    await kafka_producer.send(Topics.PAYOUT_REQUEST_COMPLETED, event, key=str(request.party_id))
    logger.info("Payout processed", payout_id=payout_request_id, status=new_status)
    return await repo.get_by_id(payout_request_id)
