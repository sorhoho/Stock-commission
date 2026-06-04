"""API endpoint tests for commission-rules-service.

Uses the async_client fixture from conftest which wires in-memory SQLite and
patches require_auth so all JWT-protected routes work without a real token.
The internal /agreement/party/{id}/active endpoint authenticates via X-Tenant-ID
header only.
"""

from __future__ import annotations

import uuid

import pytest

from tests.unit.conftest import (
    TEST_TENANT_ID,
    make_agreement_orm,
    make_rule_orm,
    make_spec_orm,
)
from app.infrastructure.db.repository import (
    AgreementRepository,
    AgreementSpecRepository,
    CommissionRuleRepository,
)

pytestmark = pytest.mark.asyncio

HEADERS = {"X-Tenant-ID": TEST_TENANT_ID}
BASE = "/api/v1/agreementManagement"


# ── /agreementSpec ────────────────────────────────────────────────────────────


async def test_list_specs_empty(async_client):
    r = await async_client.get(f"{BASE}/agreementSpec/", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []


async def test_create_spec(async_client):
    payload = {
        "name": "Dealer Standard",
        "version": "2026.1",
        "applicable_party_roles": ["DEALER"],
        "effective_from": "2026-01-01",
        "tenant_id": TEST_TENANT_ID,
    }
    r = await async_client.post(f"{BASE}/agreementSpec/", json=payload, headers=HEADERS)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Dealer Standard"
    assert data["version"] == "2026.1"
    assert "id" in data


async def test_list_specs_returns_created(async_client):
    payload = {
        "name": "Scheme A",
        "applicable_party_roles": ["DEALER"],
        "effective_from": "2026-01-01",
        "tenant_id": TEST_TENANT_ID,
    }
    await async_client.post(f"{BASE}/agreementSpec/", json=payload, headers=HEADERS)

    r = await async_client.get(f"{BASE}/agreementSpec/", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_get_spec_by_id(async_client):
    payload = {
        "name": "Scheme B",
        "applicable_party_roles": ["DEALER"],
        "effective_from": "2026-01-01",
        "tenant_id": TEST_TENANT_ID,
    }
    created = (await async_client.post(f"{BASE}/agreementSpec/", json=payload, headers=HEADERS)).json()

    r = await async_client.get(f"{BASE}/agreementSpec/{created['id']}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_get_spec_not_found(async_client):
    r = await async_client.get(f"{BASE}/agreementSpec/{uuid.uuid4()}", headers=HEADERS)
    assert r.status_code == 404


async def test_patch_spec(async_client):
    payload = {
        "name": "Old Name",
        "applicable_party_roles": ["DEALER"],
        "effective_from": "2026-01-01",
        "tenant_id": TEST_TENANT_ID,
    }
    created = (await async_client.post(f"{BASE}/agreementSpec/", json=payload, headers=HEADERS)).json()

    r = await async_client.patch(
        f"{BASE}/agreementSpec/{created['id']}",
        json={"name": "New Name"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


async def test_patch_spec_not_found(async_client):
    r = await async_client.patch(
        f"{BASE}/agreementSpec/{uuid.uuid4()}",
        json={"name": "X"},
        headers=HEADERS,
    )
    assert r.status_code == 404


async def test_delete_spec(async_client):
    payload = {
        "name": "To Delete",
        "applicable_party_roles": ["DEALER"],
        "effective_from": "2026-01-01",
        "tenant_id": TEST_TENANT_ID,
    }
    created = (await async_client.post(f"{BASE}/agreementSpec/", json=payload, headers=HEADERS)).json()

    r = await async_client.delete(f"{BASE}/agreementSpec/{created['id']}", headers=HEADERS)
    assert r.status_code == 204

    r2 = await async_client.get(f"{BASE}/agreementSpec/{created['id']}", headers=HEADERS)
    assert r2.status_code == 404


# ── /agreement ────────────────────────────────────────────────────────────────


async def _create_spec(async_client) -> str:
    spec_payload = {
        "name": "Test Scheme",
        "applicable_party_roles": ["DEALER"],
        "effective_from": "2026-01-01",
        "tenant_id": TEST_TENANT_ID,
    }
    spec = (await async_client.post(f"{BASE}/agreementSpec/", json=spec_payload, headers=HEADERS)).json()
    return spec["id"]


async def test_list_agreements_empty(async_client):
    r = await async_client.get(f"{BASE}/agreement/", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []


async def test_create_agreement(async_client):
    spec_id = await _create_spec(async_client)
    party_id = str(uuid.uuid4())
    payload = {
        "agreement_spec_id": spec_id,
        "party_id": party_id,
        "party_name": "Test Dealer",
        "signed_date": "2026-01-15",
        "tenant_id": TEST_TENANT_ID,
    }
    r = await async_client.post(f"{BASE}/agreement/", json=payload, headers=HEADERS)
    assert r.status_code == 201
    data = r.json()
    assert data["party_id"] == party_id
    assert data["status"] == "ACTIVE"


async def test_get_agreement_by_id(async_client):
    spec_id = await _create_spec(async_client)
    party_id = str(uuid.uuid4())
    payload = {
        "agreement_spec_id": spec_id,
        "party_id": party_id,
        "party_name": "Dealer X",
        "signed_date": "2026-01-15",
        "tenant_id": TEST_TENANT_ID,
    }
    created = (await async_client.post(f"{BASE}/agreement/", json=payload, headers=HEADERS)).json()

    r = await async_client.get(f"{BASE}/agreement/{created['id']}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_get_agreement_not_found(async_client):
    r = await async_client.get(f"{BASE}/agreement/{uuid.uuid4()}", headers=HEADERS)
    assert r.status_code == 404


async def test_patch_agreement_status(async_client):
    spec_id = await _create_spec(async_client)
    party_id = str(uuid.uuid4())
    payload = {
        "agreement_spec_id": spec_id,
        "party_id": party_id,
        "party_name": "Dealer Y",
        "signed_date": "2026-01-15",
        "tenant_id": TEST_TENANT_ID,
    }
    created = (await async_client.post(f"{BASE}/agreement/", json=payload, headers=HEADERS)).json()

    r = await async_client.patch(
        f"{BASE}/agreement/{created['id']}",
        json={"status": "SUSPENDED"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "SUSPENDED"


async def test_patch_agreement_not_found(async_client):
    r = await async_client.patch(
        f"{BASE}/agreement/{uuid.uuid4()}",
        json={"status": "SUSPENDED"},
        headers=HEADERS,
    )
    assert r.status_code == 404


async def test_list_agreements_filter_by_party(async_client):
    spec_id = await _create_spec(async_client)
    party_a = str(uuid.uuid4())
    party_b = str(uuid.uuid4())
    for pid, name in [(party_a, "Dealer A"), (party_b, "Dealer B")]:
        await async_client.post(
            f"{BASE}/agreement/",
            json={
                "agreement_spec_id": spec_id,
                "party_id": pid,
                "party_name": name,
                "signed_date": "2026-01-15",
                "tenant_id": TEST_TENANT_ID,
            },
            headers=HEADERS,
        )

    r = await async_client.get(f"{BASE}/agreement/?party_id={party_a}", headers=HEADERS)
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert results[0]["party_id"] == party_a


async def test_list_agreements_filter_by_status(async_client):
    spec_id = await _create_spec(async_client)
    party_a = str(uuid.uuid4())
    party_b = str(uuid.uuid4())
    # create active
    r1 = await async_client.post(
        f"{BASE}/agreement/",
        json={"agreement_spec_id": spec_id, "party_id": party_a, "party_name": "A", "signed_date": "2026-01-15", "tenant_id": TEST_TENANT_ID},
        headers=HEADERS,
    )
    created = r1.json()
    # suspend it
    await async_client.patch(f"{BASE}/agreement/{created['id']}", json={"status": "SUSPENDED"}, headers=HEADERS)
    # create another active
    await async_client.post(
        f"{BASE}/agreement/",
        json={"agreement_spec_id": spec_id, "party_id": party_b, "party_name": "B", "signed_date": "2026-01-15", "tenant_id": TEST_TENANT_ID},
        headers=HEADERS,
    )

    r = await async_client.get(f"{BASE}/agreement/?status=SUSPENDED", headers=HEADERS)
    assert r.status_code == 200
    suspended = r.json()
    assert all(a["status"] == "SUSPENDED" for a in suspended)


# ── /agreement/party/{id}/active (internal endpoint) ─────────────────────────


async def test_get_active_agreement_for_party(async_client, db_session, tenant_id, spec_id, party_id):
    spec_repo = AgreementSpecRepository(db_session)
    await spec_repo.create(make_spec_orm(tenant_id, id=spec_id))

    agreement_repo = AgreementRepository(db_session)
    await agreement_repo.create(make_agreement_orm(spec_id, party_id, tenant_id))

    rule_repo = CommissionRuleRepository(db_session)
    await rule_repo.create(make_rule_orm(spec_id, tenant_id))

    await db_session.flush()

    r = await async_client.get(
        f"{BASE}/agreement/party/{party_id}/active",
        headers={"X-Tenant-ID": tenant_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["party_id"] == str(party_id)
    assert "rules" in data
    assert len(data["rules"]) == 1


async def test_get_active_agreement_for_party_not_found(async_client, tenant_id):
    r = await async_client.get(
        f"{BASE}/agreement/party/{uuid.uuid4()}/active",
        headers={"X-Tenant-ID": tenant_id},
    )
    assert r.status_code == 404


async def test_get_active_agreement_missing_tenant_header(async_client):
    r = await async_client.get(f"{BASE}/agreement/party/{uuid.uuid4()}/active")
    assert r.status_code == 400


# ── /commissionRule ───────────────────────────────────────────────────────────


async def test_create_and_list_rules(async_client):
    spec_id = await _create_spec(async_client)
    payload = {
        "agreement_spec_id": spec_id,
        "product_category": "*",
        "commission_type": "PERCENTAGE",
        "commission_value": 0.08,
        "tier_min_qty": 1,
        "tier_max_qty": 10,
        "priority": 10,
        "tenant_id": TEST_TENANT_ID,
    }
    r = await async_client.post(f"{BASE}/commissionRule/", json=payload, headers=HEADERS)
    assert r.status_code == 201
    created = r.json()
    assert created["commission_type"] == "PERCENTAGE"

    r2 = await async_client.get(f"{BASE}/commissionRule/?agreement_spec_id={spec_id}", headers=HEADERS)
    assert r2.status_code == 200
    assert len(r2.json()) == 1


async def test_get_rule_by_id(async_client):
    spec_id = await _create_spec(async_client)
    payload = {
        "agreement_spec_id": spec_id,
        "commission_type": "FLAT_AMOUNT",
        "commission_value": 5.0,
        "tenant_id": TEST_TENANT_ID,
    }
    created = (await async_client.post(f"{BASE}/commissionRule/", json=payload, headers=HEADERS)).json()

    r = await async_client.get(f"{BASE}/commissionRule/{created['id']}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_get_rule_not_found(async_client):
    r = await async_client.get(f"{BASE}/commissionRule/{uuid.uuid4()}", headers=HEADERS)
    assert r.status_code == 404


async def test_delete_rule(async_client):
    spec_id = await _create_spec(async_client)
    payload = {
        "agreement_spec_id": spec_id,
        "commission_type": "FLAT_AMOUNT",
        "commission_value": 5.0,
        "tenant_id": TEST_TENANT_ID,
    }
    created = (await async_client.post(f"{BASE}/commissionRule/", json=payload, headers=HEADERS)).json()

    r = await async_client.delete(f"{BASE}/commissionRule/{created['id']}", headers=HEADERS)
    assert r.status_code == 204

    r2 = await async_client.get(f"{BASE}/commissionRule/{created['id']}", headers=HEADERS)
    assert r2.status_code == 404


async def test_list_rules_without_spec_filter(async_client):
    spec_id = await _create_spec(async_client)
    payload = {
        "agreement_spec_id": spec_id,
        "commission_type": "FLAT_AMOUNT",
        "commission_value": 3.0,
        "tenant_id": TEST_TENANT_ID,
    }
    await async_client.post(f"{BASE}/commissionRule/", json=payload, headers=HEADERS)

    r = await async_client.get(f"{BASE}/commissionRule/", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) >= 1
