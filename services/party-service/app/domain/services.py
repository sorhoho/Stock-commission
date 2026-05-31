"""Business logic for the Party service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.domain.models import Party, PartyCreate, PartyRole
from app.infrastructure.db.repository import PartyRepository
from telco_common.events.cloudevents import Topics, make_event
from telco_common.events.schemas.party_events import PartyOnboardedData
from telco_common.exceptions import NotFoundException
from telco_common.kafka.producer_factory import KafkaProducer

log = structlog.get_logger(__name__)


async def onboard_party(
    data: PartyCreate,
    tenant_id: str,
    repo: PartyRepository,
    kafka_producer: KafkaProducer,
    correlation_id: str | None = None,
    region: str | None = None,
    tier: str | None = None,
) -> object:
    """Create a Party entity and publish an onboarding event for dealers.

    If the party role is DEALER, publish a ``telco.party.dealer.onboarded``
    CloudEvent so downstream services (commission, inventory, etc.) can
    react to the new dealer.

    Returns the persisted ORM Party instance.
    """
    party = await repo.create(data=data, tenant_id=tenant_id)
    log.info(
        "Party created",
        party_id=str(party.id),
        role=party.role,
        name=party.name,
        tenant_id=tenant_id,
    )

    if data.role == PartyRole.DEALER:
        event_data = PartyOnboardedData(
            party_id=str(party.id),
            party_type=str(party.party_type),
            name=party.name,
            role=str(party.role),
            region=region,
            tier=tier,
            effective_date=datetime.now(UTC).isoformat(),
            tenant_id=tenant_id,
        )
        event = make_event(
            event_type=Topics.PARTY_DEALER_ONBOARDED,
            source_service="party-service",
            tenant_id=tenant_id,
            data=event_data,
            correlation_id=correlation_id,
        )
        await kafka_producer.send(
            topic=Topics.PARTY_DEALER_ONBOARDED,
            event=event,
            key=str(party.id),
        )
        log.info(
            "Dealer onboarded event published",
            party_id=str(party.id),
            tenant_id=tenant_id,
        )

    return party


async def get_party_hierarchy(
    party_id: uuid.UUID,
    tenant_id: str,
    repo: PartyRepository,
) -> list[object]:
    """Return the party hierarchy from root down to *party_id*.

    Resolves the parent_party_id chain iteratively and returns the list
    in root-first order (root at index 0, the requested party at the end).

    Raises NotFoundException if *party_id* does not exist.
    """
    # Confirm the party exists first
    party = await repo.get_by_id(party_id=party_id, tenant_id=tenant_id)
    if party is None:
        raise NotFoundException("Party", str(party_id))

    hierarchy = await repo.get_ancestors(party_id=party_id, tenant_id=tenant_id)
    return hierarchy
