"""Unit tests for PartyRepository against in-memory SQLite."""

from __future__ import annotations

import uuid

import pytest

from app.domain.models import (
    PartyCreate,
    PartyRole,
    PartyStatus,
    PartyType,
    PartyUpdate,
)
from app.infrastructure.db.repository import PartyRepository

pytestmark = pytest.mark.asyncio


def _make_create(
    name: str = "Acme",
    role: PartyRole = PartyRole.DEALER,
    party_type: PartyType = PartyType.ORGANIZATION,
    status: PartyStatus = PartyStatus.ACTIVE,
    tax_number: str | None = None,
    parent_party_id: uuid.UUID | None = None,
) -> PartyCreate:
    return PartyCreate(
        party_type=party_type,
        role=role,
        name=name,
        status=status,
        tax_number=tax_number,
        parent_party_id=parent_party_id,
    )


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_persists_and_returns_party(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    party = await repo.create(
        data=_make_create(name="Acme", tax_number="TX-1"),
        tenant_id=sample_tenant_id,
    )
    assert party.id is not None
    assert isinstance(party.id, uuid.UUID)
    assert party.name == "Acme"
    assert party.tax_number == "TX-1"
    assert party.role == PartyRole.DEALER
    assert party.party_type == PartyType.ORGANIZATION
    assert party.status == PartyStatus.ACTIVE
    assert party.tenant_id == sample_tenant_id
    assert party.href == f"/api/v1/party/{party.id}"


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_existing(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    created = await repo.create(data=_make_create(name="Lookup"), tenant_id=sample_tenant_id)

    fetched = await repo.get_by_id(party_id=created.id, tenant_id=sample_tenant_id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Lookup"


async def test_get_by_id_returns_none_for_missing(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    result = await repo.get_by_id(party_id=uuid.uuid4(), tenant_id=sample_tenant_id)
    assert result is None


async def test_get_by_id_enforces_tenant_isolation(
    db_session, sample_tenant_id, other_tenant_id
):
    repo = PartyRepository(db_session)
    created = await repo.create(data=_make_create(name="Owned"), tenant_id=sample_tenant_id)

    # Same id, different tenant -> not found
    result = await repo.get_by_id(party_id=created.id, tenant_id=other_tenant_id)
    assert result is None


# ---------------------------------------------------------------------------
# list_with_filters
# ---------------------------------------------------------------------------


async def test_list_returns_only_own_tenant(db_session, sample_tenant_id, other_tenant_id):
    repo = PartyRepository(db_session)
    await repo.create(data=_make_create(name="Mine A"), tenant_id=sample_tenant_id)
    await repo.create(data=_make_create(name="Mine B"), tenant_id=sample_tenant_id)
    await repo.create(data=_make_create(name="Theirs"), tenant_id=other_tenant_id)

    items = await repo.list_with_filters(tenant_id=sample_tenant_id)
    names = {p.name for p in items}
    assert names == {"Mine A", "Mine B"}


async def test_list_orders_by_name(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    await repo.create(data=_make_create(name="Zeta"), tenant_id=sample_tenant_id)
    await repo.create(data=_make_create(name="Alpha"), tenant_id=sample_tenant_id)
    await repo.create(data=_make_create(name="Mike"), tenant_id=sample_tenant_id)

    items = await repo.list_with_filters(tenant_id=sample_tenant_id)
    assert [p.name for p in items] == ["Alpha", "Mike", "Zeta"]


async def test_list_filters_by_role(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    await repo.create(
        data=_make_create(name="A Dealer", role=PartyRole.DEALER),
        tenant_id=sample_tenant_id,
    )
    await repo.create(
        data=_make_create(name="A Distributor", role=PartyRole.DISTRIBUTOR),
        tenant_id=sample_tenant_id,
    )

    items = await repo.list_with_filters(tenant_id=sample_tenant_id, role=PartyRole.DEALER)
    assert len(items) == 1
    assert items[0].role == PartyRole.DEALER


async def test_list_filters_by_status(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    await repo.create(
        data=_make_create(name="Active One", status=PartyStatus.ACTIVE),
        tenant_id=sample_tenant_id,
    )
    await repo.create(
        data=_make_create(name="Suspended One", status=PartyStatus.SUSPENDED),
        tenant_id=sample_tenant_id,
    )

    items = await repo.list_with_filters(
        tenant_id=sample_tenant_id, status=PartyStatus.SUSPENDED
    )
    assert len(items) == 1
    assert items[0].name == "Suspended One"


async def test_list_filters_by_parent(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    parent = await repo.create(data=_make_create(name="Parent"), tenant_id=sample_tenant_id)
    await repo.create(
        data=_make_create(name="Child", parent_party_id=parent.id),
        tenant_id=sample_tenant_id,
    )
    await repo.create(data=_make_create(name="Orphan"), tenant_id=sample_tenant_id)

    items = await repo.list_with_filters(
        tenant_id=sample_tenant_id, parent_party_id=parent.id
    )
    assert len(items) == 1
    assert items[0].name == "Child"


async def test_list_pagination(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    for i in range(5):
        await repo.create(data=_make_create(name=f"P{i}"), tenant_id=sample_tenant_id)

    page1 = await repo.list_with_filters(tenant_id=sample_tenant_id, page=1, size=2)
    page2 = await repo.list_with_filters(tenant_id=sample_tenant_id, page=2, size=2)
    page3 = await repo.list_with_filters(tenant_id=sample_tenant_id, page=3, size=2)

    assert [p.name for p in page1] == ["P0", "P1"]
    assert [p.name for p in page2] == ["P2", "P3"]
    assert [p.name for p in page3] == ["P4"]


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_modifies_fields(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    created = await repo.create(data=_make_create(name="Old"), tenant_id=sample_tenant_id)

    updated = await repo.update(
        party_id=created.id,
        tenant_id=sample_tenant_id,
        data=PartyUpdate(name="New", status=PartyStatus.SUSPENDED),
    )
    assert updated is not None
    assert updated.name == "New"
    assert updated.status == PartyStatus.SUSPENDED
    # Unchanged field preserved
    assert updated.role == PartyRole.DEALER


async def test_update_exclude_none_leaves_others(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    created = await repo.create(
        data=_make_create(name="Keep", tax_number="ORIG"), tenant_id=sample_tenant_id
    )

    updated = await repo.update(
        party_id=created.id,
        tenant_id=sample_tenant_id,
        data=PartyUpdate(name="Renamed"),
    )
    assert updated.name == "Renamed"
    assert updated.tax_number == "ORIG"  # not overwritten with None


async def test_update_missing_returns_none(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    result = await repo.update(
        party_id=uuid.uuid4(),
        tenant_id=sample_tenant_id,
        data=PartyUpdate(name="X"),
    )
    assert result is None


async def test_update_respects_tenant_isolation(
    db_session, sample_tenant_id, other_tenant_id
):
    repo = PartyRepository(db_session)
    created = await repo.create(data=_make_create(name="Owned"), tenant_id=sample_tenant_id)

    result = await repo.update(
        party_id=created.id,
        tenant_id=other_tenant_id,
        data=PartyUpdate(name="Hijack"),
    )
    assert result is None


# ---------------------------------------------------------------------------
# soft_delete
# ---------------------------------------------------------------------------


async def test_soft_delete_sets_terminated(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    created = await repo.create(data=_make_create(name="ToDelete"), tenant_id=sample_tenant_id)

    deleted = await repo.soft_delete(party_id=created.id, tenant_id=sample_tenant_id)
    assert deleted is not None
    assert deleted.status == PartyStatus.TERMINATED

    # Still retrievable, just terminated
    fetched = await repo.get_by_id(party_id=created.id, tenant_id=sample_tenant_id)
    assert fetched.status == PartyStatus.TERMINATED


async def test_soft_delete_missing_returns_none(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    result = await repo.soft_delete(party_id=uuid.uuid4(), tenant_id=sample_tenant_id)
    assert result is None


# ---------------------------------------------------------------------------
# get_ancestors (hierarchy)
# ---------------------------------------------------------------------------


async def test_get_ancestors_returns_root_first_chain(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    root = await repo.create(
        data=_make_create(name="Root", role=PartyRole.DISTRIBUTOR),
        tenant_id=sample_tenant_id,
    )
    mid = await repo.create(
        data=_make_create(name="Mid", role=PartyRole.CHANNEL_PARTNER, parent_party_id=root.id),
        tenant_id=sample_tenant_id,
    )
    leaf = await repo.create(
        data=_make_create(name="Leaf", role=PartyRole.DEALER, parent_party_id=mid.id),
        tenant_id=sample_tenant_id,
    )

    chain = await repo.get_ancestors(party_id=leaf.id, tenant_id=sample_tenant_id)
    assert [p.name for p in chain] == ["Root", "Mid", "Leaf"]


async def test_get_ancestors_single_node(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    solo = await repo.create(data=_make_create(name="Solo"), tenant_id=sample_tenant_id)

    chain = await repo.get_ancestors(party_id=solo.id, tenant_id=sample_tenant_id)
    assert [p.id for p in chain] == [solo.id]


async def test_get_ancestors_missing_returns_empty(db_session, sample_tenant_id):
    repo = PartyRepository(db_session)
    chain = await repo.get_ancestors(party_id=uuid.uuid4(), tenant_id=sample_tenant_id)
    assert chain == []
