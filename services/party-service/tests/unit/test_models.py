"""Unit tests for party-service Pydantic domain models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.models import (
    Party,
    PartyAccount,
    PartyAccountCreate,
    PartyCharacteristic,
    PartyCharacteristicCreate,
    PartyCreate,
    PartyRole,
    PartyStatus,
    PartyType,
    PartyUpdate,
)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


def test_party_type_enum_values():
    assert PartyType.ORGANIZATION == "ORGANIZATION"
    assert PartyType.INDIVIDUAL == "INDIVIDUAL"
    assert set(PartyType) == {PartyType.ORGANIZATION, PartyType.INDIVIDUAL}


def test_party_role_enum_values():
    assert PartyRole.DISTRIBUTOR == "DISTRIBUTOR"
    assert PartyRole.DEALER == "DEALER"
    assert PartyRole.CHANNEL_PARTNER == "CHANNEL_PARTNER"
    assert PartyRole.SALES_EMPLOYEE == "SALES_EMPLOYEE"
    assert PartyRole.CUSTOMER == "CUSTOMER"


def test_party_status_enum_values():
    assert PartyStatus.ACTIVE == "ACTIVE"
    assert PartyStatus.SUSPENDED == "SUSPENDED"
    assert PartyStatus.TERMINATED == "TERMINATED"


# ---------------------------------------------------------------------------
# PartyCreate
# ---------------------------------------------------------------------------


def test_party_create_minimal_valid_with_defaults():
    model = PartyCreate(
        party_type=PartyType.ORGANIZATION,
        role=PartyRole.DEALER,
        name="Acme Distribution",
    )
    assert model.name == "Acme Distribution"
    assert model.party_type == PartyType.ORGANIZATION
    assert model.role == PartyRole.DEALER
    # Defaults
    assert model.status == PartyStatus.ACTIVE
    assert model.tax_number is None
    assert model.parent_party_id is None


def test_party_create_full_valid():
    parent = uuid.uuid4()
    model = PartyCreate(
        party_type=PartyType.INDIVIDUAL,
        role=PartyRole.SALES_EMPLOYEE,
        name="Jane Doe",
        tax_number="TX-123",
        status=PartyStatus.SUSPENDED,
        parent_party_id=parent,
    )
    assert model.tax_number == "TX-123"
    assert model.status == PartyStatus.SUSPENDED
    assert model.parent_party_id == parent


def test_party_create_accepts_string_enum_values():
    model = PartyCreate(party_type="ORGANIZATION", role="CUSTOMER", name="X")
    assert model.role == PartyRole.CUSTOMER
    assert model.party_type == PartyType.ORGANIZATION


def test_party_create_missing_required_field_raises():
    with pytest.raises(ValidationError):
        PartyCreate(role=PartyRole.DEALER, name="No type")  # missing party_type


def test_party_create_missing_name_raises():
    with pytest.raises(ValidationError):
        PartyCreate(party_type=PartyType.ORGANIZATION, role=PartyRole.DEALER)


def test_party_create_invalid_enum_raises():
    with pytest.raises(ValidationError):
        PartyCreate(party_type="ALIEN", role=PartyRole.DEALER, name="X")


def test_party_create_invalid_role_raises():
    with pytest.raises(ValidationError):
        PartyCreate(party_type=PartyType.ORGANIZATION, role="OVERLORD", name="X")


def test_party_create_invalid_parent_uuid_raises():
    with pytest.raises(ValidationError):
        PartyCreate(
            party_type=PartyType.ORGANIZATION,
            role=PartyRole.DEALER,
            name="X",
            parent_party_id="not-a-uuid",
        )


# ---------------------------------------------------------------------------
# PartyUpdate
# ---------------------------------------------------------------------------


def test_party_update_all_optional_empty():
    model = PartyUpdate()
    assert model.name is None
    assert model.status is None
    assert model.role is None
    assert model.tax_number is None
    assert model.parent_party_id is None


def test_party_update_partial():
    model = PartyUpdate(name="New Name", status=PartyStatus.SUSPENDED)
    dumped = model.model_dump(exclude_none=True)
    assert dumped == {"name": "New Name", "status": PartyStatus.SUSPENDED}


def test_party_update_invalid_status_raises():
    with pytest.raises(ValidationError):
        PartyUpdate(status="GONE")


# ---------------------------------------------------------------------------
# Party (read model)
# ---------------------------------------------------------------------------


def test_party_full_model_valid():
    now = datetime.now(UTC)
    pid = uuid.uuid4()
    model = Party(
        id=pid,
        href=f"/api/v1/party/{pid}",
        party_type=PartyType.ORGANIZATION,
        role=PartyRole.DISTRIBUTOR,
        name="Top Distributor",
        status=PartyStatus.ACTIVE,
        tenant_id="tenant-1",
        created_at=now,
        updated_at=now,
    )
    assert model.id == pid
    assert model.href == f"/api/v1/party/{pid}"
    assert model.parent_party_id is None


def test_party_from_attributes():
    """Party.model_validate should work from an attribute-bearing object."""

    class _Row:
        id = uuid.uuid4()
        href = "/api/v1/party/x"
        party_type = "ORGANIZATION"
        role = "DEALER"
        name = "Row Dealer"
        tax_number = None
        status = "ACTIVE"
        parent_party_id = None
        tenant_id = "tenant-9"
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

    model = Party.model_validate(_Row())
    assert model.name == "Row Dealer"
    assert model.role == PartyRole.DEALER


def test_party_missing_required_raises():
    with pytest.raises(ValidationError):
        Party(
            id=uuid.uuid4(),
            href="/x",
            party_type=PartyType.ORGANIZATION,
            role=PartyRole.DEALER,
            name="X",
            # status missing
            tenant_id="t",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


# ---------------------------------------------------------------------------
# PartyCharacteristic
# ---------------------------------------------------------------------------


def test_party_characteristic_create_defaults_value_type():
    pid = uuid.uuid4()
    model = PartyCharacteristicCreate(party_id=pid, name="region", value="EMEA")
    assert model.value_type == "string"
    assert model.value == "EMEA"
    assert model.party_id == pid


def test_party_characteristic_create_accepts_arbitrary_value():
    model = PartyCharacteristicCreate(
        party_id=uuid.uuid4(), name="limits", value={"max": 10}, value_type="json"
    )
    assert model.value == {"max": 10}
    assert model.value_type == "json"


def test_party_characteristic_read_model():
    model = PartyCharacteristic(
        id=uuid.uuid4(),
        party_id=uuid.uuid4(),
        name="tier",
        value=3,
        value_type="number",
    )
    assert model.value == 3


def test_party_characteristic_create_missing_party_id_raises():
    with pytest.raises(ValidationError):
        PartyCharacteristicCreate(name="x", value="y")


# ---------------------------------------------------------------------------
# PartyAccount
# ---------------------------------------------------------------------------


def test_party_account_create_defaults():
    model = PartyAccountCreate(party_id=uuid.uuid4(), account_type="PREPAID")
    assert model.balance == 0.0
    assert model.currency == "THB"


def test_party_account_read_model():
    model = PartyAccount(
        id=uuid.uuid4(),
        party_id=uuid.uuid4(),
        account_type="POSTPAID",
        balance=125.5,
        currency="EUR",
        last_updated=datetime.now(UTC),
    )
    assert model.balance == 125.5
    assert model.currency == "EUR"
