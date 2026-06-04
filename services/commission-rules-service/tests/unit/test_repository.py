"""Unit tests for commission-rules-service repositories using in-memory SQLite."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.infrastructure.db.repository import (
    AgreementRepository,
    AgreementSpecRepository,
    CommissionRuleRepository,
)
from tests.unit.conftest import make_agreement_orm, make_rule_orm, make_spec_orm

pytestmark = pytest.mark.asyncio


# ── AgreementSpecRepository ───────────────────────────────────────────────────


async def test_spec_create_and_get_by_id(db_session, tenant_id):
    repo = AgreementSpecRepository(db_session)
    spec = make_spec_orm(tenant_id)
    created = await repo.create(spec)
    assert created.id is not None

    fetched = await repo.get_by_id(str(created.id))
    assert fetched is not None
    assert fetched.name == "Standard Dealer Scheme"


async def test_spec_get_by_id_missing_returns_none(db_session):
    repo = AgreementSpecRepository(db_session)
    assert await repo.get_by_id(str(uuid.uuid4())) is None


async def test_spec_get_by_id_deleted_returns_none(db_session, tenant_id):
    repo = AgreementSpecRepository(db_session)
    spec = await repo.create(make_spec_orm(tenant_id))
    await repo.soft_delete(str(spec.id))
    await db_session.flush()
    assert await repo.get_by_id(str(spec.id)) is None


async def test_spec_list_active_excludes_deleted(db_session, tenant_id):
    repo = AgreementSpecRepository(db_session)
    active = await repo.create(make_spec_orm(tenant_id, name="Active"))
    deleted = await repo.create(make_spec_orm(tenant_id, name="Deleted"))
    await repo.soft_delete(str(deleted.id))
    await db_session.flush()

    results = await repo.list_active(tenant_id)
    names = [r.name for r in results]
    assert "Active" in names
    assert "Deleted" not in names


async def test_spec_list_active_tenant_isolation(db_session, tenant_id):
    repo = AgreementSpecRepository(db_session)
    await repo.create(make_spec_orm(tenant_id))
    await repo.create(make_spec_orm("other-tenant"))

    results = await repo.list_active(tenant_id)
    assert all(r.tenant_id == tenant_id for r in results)
    assert len(results) == 1


async def test_spec_update_name(db_session, tenant_id):
    repo = AgreementSpecRepository(db_session)
    spec = await repo.create(make_spec_orm(tenant_id))
    spec_id = str(spec.id)

    updated = await repo.update(spec_id, {"name": "Updated Name"})
    assert updated is not None
    assert updated.name == "Updated Name"


async def test_spec_update_missing_returns_none(db_session):
    repo = AgreementSpecRepository(db_session)
    result = await repo.update(str(uuid.uuid4()), {"name": "X"})
    assert result is None


async def test_spec_soft_delete(db_session, tenant_id):
    repo = AgreementSpecRepository(db_session)
    spec = await repo.create(make_spec_orm(tenant_id))
    spec_id = str(spec.id)

    await repo.soft_delete(spec_id)
    await db_session.flush()

    assert await repo.get_by_id(spec_id) is None
    still_active = await repo.list_active(tenant_id)
    assert all(str(r.id) != spec_id for r in still_active)


# ── AgreementRepository ───────────────────────────────────────────────────────


async def test_agreement_create_and_get_by_id(db_session, tenant_id, spec_id, party_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = AgreementRepository(db_session)
    agreement = await repo.create(make_agreement_orm(spec_id, party_id, tenant_id))
    assert agreement.id is not None

    fetched = await repo.get_by_id(str(agreement.id))
    assert fetched is not None
    assert fetched.status == "ACTIVE"


async def test_agreement_get_by_id_missing_returns_none(db_session):
    repo = AgreementRepository(db_session)
    assert await repo.get_by_id(str(uuid.uuid4())) is None


async def test_agreement_get_active_for_party(db_session, tenant_id, spec_id, party_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = AgreementRepository(db_session)
    await repo.create(make_agreement_orm(spec_id, party_id, tenant_id))

    found = await repo.get_active_for_party(str(party_id), tenant_id)
    assert found is not None
    assert found.status == "ACTIVE"


async def test_agreement_get_active_for_party_not_found(db_session, tenant_id):
    repo = AgreementRepository(db_session)
    result = await repo.get_active_for_party(str(uuid.uuid4()), tenant_id)
    assert result is None


async def test_agreement_get_active_for_party_wrong_tenant(db_session, spec_id, party_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm("tenant-A", id=spec_id))

    repo = AgreementRepository(db_session)
    await repo.create(make_agreement_orm(spec_id, party_id, "tenant-A"))

    result = await repo.get_active_for_party(str(party_id), "tenant-B")
    assert result is None


async def test_agreement_list_with_filters_no_filter(db_session, tenant_id, spec_id, party_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = AgreementRepository(db_session)
    other_party = uuid.uuid4()
    await repo.create(make_agreement_orm(spec_id, party_id, tenant_id))
    await repo.create(make_agreement_orm(spec_id, other_party, tenant_id))

    results = await repo.list_with_filters(tenant_id)
    assert len(results) == 2


async def test_agreement_list_with_filters_by_party(db_session, tenant_id, spec_id, party_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = AgreementRepository(db_session)
    other = uuid.uuid4()
    await repo.create(make_agreement_orm(spec_id, party_id, tenant_id))
    await repo.create(make_agreement_orm(spec_id, other, tenant_id))

    results = await repo.list_with_filters(tenant_id, party_id=str(party_id))
    assert len(results) == 1
    assert results[0].party_id == party_id


async def test_agreement_list_with_filters_by_status(db_session, tenant_id, spec_id, party_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = AgreementRepository(db_session)
    other = uuid.uuid4()
    await repo.create(make_agreement_orm(spec_id, party_id, tenant_id, status="ACTIVE"))
    await repo.create(make_agreement_orm(spec_id, other, tenant_id, status="SUSPENDED"))

    active = await repo.list_with_filters(tenant_id, status="ACTIVE")
    assert len(active) == 1
    assert active[0].status == "ACTIVE"


async def test_agreement_update_status(db_session, tenant_id, spec_id, party_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = AgreementRepository(db_session)
    agreement = await repo.create(make_agreement_orm(spec_id, party_id, tenant_id))
    agreement_id = str(agreement.id)

    await repo.update_status(agreement_id, "SUSPENDED")
    await db_session.flush()
    db_session.expire_all()

    refreshed = await repo.get_by_id(agreement_id)
    assert refreshed.status == "SUSPENDED"


# ── CommissionRuleRepository ──────────────────────────────────────────────────


async def test_rule_create_and_get_by_id(db_session, tenant_id, spec_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = CommissionRuleRepository(db_session)
    rule = await repo.create(make_rule_orm(spec_id, tenant_id))
    assert rule.id is not None

    fetched = await repo.get_by_id(str(rule.id))
    assert fetched is not None
    assert fetched.commission_type == "FLAT_AMOUNT"
    assert fetched.commission_value == 5.0


async def test_rule_get_by_id_missing_returns_none(db_session):
    repo = CommissionRuleRepository(db_session)
    assert await repo.get_by_id(str(uuid.uuid4())) is None


async def test_rule_get_by_id_deleted_returns_none(db_session, tenant_id, spec_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = CommissionRuleRepository(db_session)
    rule = await repo.create(make_rule_orm(spec_id, tenant_id))
    rule_id = str(rule.id)

    await repo.soft_delete(rule_id)
    await db_session.flush()
    assert await repo.get_by_id(rule_id) is None


async def test_rule_list_for_spec_ordered_by_priority(db_session, tenant_id, spec_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = CommissionRuleRepository(db_session)
    await repo.create(make_rule_orm(spec_id, tenant_id, priority=30))
    await repo.create(make_rule_orm(spec_id, tenant_id, priority=10))
    await repo.create(make_rule_orm(spec_id, tenant_id, priority=20))

    rules = await repo.list_for_spec(str(spec_id))
    priorities = [r.priority for r in rules]
    assert priorities == sorted(priorities)


async def test_rule_list_for_spec_excludes_deleted(db_session, tenant_id, spec_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = CommissionRuleRepository(db_session)
    r1 = await repo.create(make_rule_orm(spec_id, tenant_id, priority=10))
    r2 = await repo.create(make_rule_orm(spec_id, tenant_id, priority=20))
    await repo.soft_delete(str(r2.id))
    await db_session.flush()

    rules = await repo.list_for_spec(str(spec_id))
    ids = [str(r.id) for r in rules]
    assert str(r1.id) in ids
    assert str(r2.id) not in ids


async def test_rule_soft_delete(db_session, tenant_id, spec_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    repo = CommissionRuleRepository(db_session)
    rule = await repo.create(make_rule_orm(spec_id, tenant_id))
    rule_id = str(rule.id)

    await repo.soft_delete(rule_id)
    await db_session.flush()

    assert await repo.get_by_id(rule_id) is None
    rules = await repo.list_for_spec(str(spec_id))
    assert all(str(r.id) != rule_id for r in rules)
