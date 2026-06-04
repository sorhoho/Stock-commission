"""Unit tests for party-service domain services."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.domain import services
from app.domain.models import PartyCreate, PartyRole, PartyStatus, PartyType
from app.infrastructure.db.repository import PartyRepository
from telco_common.events.cloudevents import Topics
from telco_common.exceptions import NotFoundException

pytestmark = pytest.mark.asyncio


def _make_create(
    name: str = "Acme",
    role: PartyRole = PartyRole.DEALER,
) -> PartyCreate:
    return PartyCreate(
        party_type=PartyType.ORGANIZATION,
        role=role,
        name=name,
        status=PartyStatus.ACTIVE,
    )


# ---------------------------------------------------------------------------
# onboard_party — using real repo + in-memory SQLite, mocked Kafka
# ---------------------------------------------------------------------------


async def test_onboard_dealer_persists_and_publishes_event(
    db_session, mock_kafka_producer, sample_tenant_id
):
    repo = PartyRepository(db_session)
    data = _make_create(name="Dealer Co", role=PartyRole.DEALER)

    party = await services.onboard_party(
        data=data,
        tenant_id=sample_tenant_id,
        repo=repo,
        kafka_producer=mock_kafka_producer,
        correlation_id="corr-1",
        region="EMEA",
        tier="GOLD",
    )

    # Persisted
    assert party.id is not None
    fetched = await repo.get_by_id(party_id=party.id, tenant_id=sample_tenant_id)
    assert fetched is not None
    assert fetched.name == "Dealer Co"

    # Event published with correct topic, key, and payload
    mock_kafka_producer.send.assert_awaited_once()
    call = mock_kafka_producer.send.call_args
    assert call.kwargs["topic"] == Topics.PARTY_DEALER_ONBOARDED
    assert call.kwargs["key"] == str(party.id)

    event = call.kwargs["event"]
    assert event["type"] == Topics.PARTY_DEALER_ONBOARDED
    assert event["tenantid"] == sample_tenant_id
    assert event["correlationid"] == "corr-1"
    assert event["data"]["party_id"] == str(party.id)
    assert event["data"]["name"] == "Dealer Co"
    assert event["data"]["role"] == PartyRole.DEALER
    assert event["data"]["region"] == "EMEA"
    assert event["data"]["tier"] == "GOLD"
    assert event["data"]["tenant_id"] == sample_tenant_id


async def test_onboard_non_dealer_does_not_publish(
    db_session, mock_kafka_producer, sample_tenant_id
):
    repo = PartyRepository(db_session)
    data = _make_create(name="A Customer", role=PartyRole.CUSTOMER)

    party = await services.onboard_party(
        data=data,
        tenant_id=sample_tenant_id,
        repo=repo,
        kafka_producer=mock_kafka_producer,
    )

    # Still persisted
    fetched = await repo.get_by_id(party_id=party.id, tenant_id=sample_tenant_id)
    assert fetched is not None
    assert fetched.role == PartyRole.CUSTOMER

    # No event for non-dealer roles
    mock_kafka_producer.send.assert_not_awaited()


async def test_onboard_distributor_does_not_publish(
    db_session, mock_kafka_producer, sample_tenant_id
):
    repo = PartyRepository(db_session)
    party = await services.onboard_party(
        data=_make_create(name="Dist", role=PartyRole.DISTRIBUTOR),
        tenant_id=sample_tenant_id,
        repo=repo,
        kafka_producer=mock_kafka_producer,
    )
    assert party.role == PartyRole.DISTRIBUTOR
    mock_kafka_producer.send.assert_not_awaited()


# ---------------------------------------------------------------------------
# get_party_hierarchy
# ---------------------------------------------------------------------------


async def test_get_party_hierarchy_returns_chain(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    root = await repo.create(
        data=_make_create(name="Root", role=PartyRole.DISTRIBUTOR),
        tenant_id=sample_tenant_id,
    )
    child = await repo.create(
        data=PartyCreate(
            party_type=PartyType.ORGANIZATION,
            role=PartyRole.DEALER,
            name="Child",
            parent_party_id=root.id,
        ),
        tenant_id=sample_tenant_id,
    )

    hierarchy = await services.get_party_hierarchy(
        party_id=child.id, tenant_id=sample_tenant_id, repo=repo
    )
    assert [p.name for p in hierarchy] == ["Root", "Child"]


async def test_get_party_hierarchy_missing_raises(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    with pytest.raises(NotFoundException):
        await services.get_party_hierarchy(
            party_id=uuid.uuid4(), tenant_id=sample_tenant_id, repo=repo
        )


async def test_onboard_dealer_generates_correlation_id_when_absent(
    db_session, mock_kafka_producer, sample_tenant_id
):
    """When no correlation_id is passed, make_event still produces one."""
    repo = PartyRepository(db_session)
    party = await services.onboard_party(
        data=_make_create(name="Dealer NoCorr", role=PartyRole.DEALER),
        tenant_id=sample_tenant_id,
        repo=repo,
        kafka_producer=mock_kafka_producer,
    )
    event = mock_kafka_producer.send.call_args.kwargs["event"]
    # A correlation id was auto-generated
    assert event["correlationid"]
    uuid.UUID(event["correlationid"])  # parses as a valid uuid
    assert event["data"]["region"] is None
    assert event["data"]["tier"] is None
