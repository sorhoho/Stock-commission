"""Unit tests for payout-service domain models (Pydantic validation + enums)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.domain.models import (
    PaymentMethod,
    PayoutRequest,
    PayoutRequestCreate,
    PayoutRequestUpdate,
    PayoutStatus,
)


def test_payout_status_enum_members():
    assert PayoutStatus.PENDING == "PENDING"
    assert PayoutStatus.PROCESSING == "PROCESSING"
    assert PayoutStatus.COMPLETED == "COMPLETED"
    assert PayoutStatus.FAILED == "FAILED"
    assert {s.value for s in PayoutStatus} == {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}


def test_payment_method_enum_members():
    assert {m.value for m in PaymentMethod} == {"BANK_TRANSFER", "WALLET", "OFFSET"}


def test_payout_request_create_defaults():
    model = PayoutRequestCreate(
        party_id=uuid.uuid4(),
        statement_id=uuid.uuid4(),
        amount=100.0,
        bank_account_ref="1234567890",
        scheduled_date=date(2026, 1, 28),
        tenant_id="tenant-1",
    )
    assert model.currency == "THB"
    assert model.payment_method == PaymentMethod.BANK_TRANSFER


def test_payout_request_create_accepts_explicit_method():
    model = PayoutRequestCreate(
        party_id=uuid.uuid4(),
        statement_id=uuid.uuid4(),
        amount=50.0,
        currency="EUR",
        payment_method="WALLET",
        bank_account_ref="ref",
        scheduled_date=date(2026, 2, 28),
        tenant_id="tenant-1",
    )
    assert model.payment_method == PaymentMethod.WALLET
    assert model.currency == "EUR"


def test_payout_request_create_missing_required_field():
    with pytest.raises(ValidationError) as exc:
        PayoutRequestCreate(
            statement_id=uuid.uuid4(),
            amount=100.0,
            bank_account_ref="ref",
            scheduled_date=date(2026, 1, 28),
            tenant_id="tenant-1",
        )
    assert "party_id" in str(exc.value)


def test_payout_request_create_invalid_payment_method():
    with pytest.raises(ValidationError):
        PayoutRequestCreate(
            party_id=uuid.uuid4(),
            statement_id=uuid.uuid4(),
            amount=100.0,
            payment_method="CASH_UNDER_TABLE",
            bank_account_ref="ref",
            scheduled_date=date(2026, 1, 28),
            tenant_id="tenant-1",
        )


def test_payout_request_create_invalid_uuid():
    with pytest.raises(ValidationError):
        PayoutRequestCreate(
            party_id="not-a-uuid",
            statement_id=uuid.uuid4(),
            amount=100.0,
            bank_account_ref="ref",
            scheduled_date=date(2026, 1, 28),
            tenant_id="tenant-1",
        )


def test_payout_request_full_model_validates():
    pid = uuid.uuid4()
    model = PayoutRequest(
        id=uuid.uuid4(),
        party_id=pid,
        statement_id=uuid.uuid4(),
        amount=250.5,
        currency="USD",
        payment_method=PaymentMethod.BANK_TRANSFER,
        bank_account_ref="****7890",
        status=PayoutStatus.PENDING,
        scheduled_date=date(2026, 1, 28),
        tenant_id="tenant-1",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    assert model.party_id == pid
    assert model.processed_date is None
    assert model.external_reference is None


def test_payout_request_invalid_status_rejected():
    with pytest.raises(ValidationError):
        PayoutRequest(
            id=uuid.uuid4(),
            party_id=uuid.uuid4(),
            statement_id=uuid.uuid4(),
            amount=10.0,
            currency="USD",
            payment_method=PaymentMethod.BANK_TRANSFER,
            bank_account_ref="ref",
            status="NOT_A_STATUS",
            scheduled_date=date(2026, 1, 28),
            tenant_id="tenant-1",
            created_at=datetime.now(),
        )


def test_payout_request_from_attributes():
    """from_attributes lets us validate directly off an ORM-like object."""

    class FakeORM:
        id = uuid.uuid4()
        party_id = uuid.uuid4()
        statement_id = uuid.uuid4()
        amount = 99.0
        currency = "USD"
        payment_method = "BANK_TRANSFER"
        bank_account_ref = "****1234"
        status = "PENDING"
        scheduled_date = date(2026, 1, 28)
        processed_date = None
        external_reference = None
        tenant_id = "tenant-1"
        created_at = datetime.now()

    model = PayoutRequest.model_validate(FakeORM())
    assert model.amount == 99.0
    assert model.status == PayoutStatus.PENDING


def test_payout_request_update_all_optional():
    empty = PayoutRequestUpdate()
    assert empty.status is None
    assert empty.external_reference is None
    assert empty.processed_date is None

    partial = PayoutRequestUpdate(status=PayoutStatus.COMPLETED, external_reference="EXT-1")
    assert partial.status == PayoutStatus.COMPLETED
    assert partial.external_reference == "EXT-1"
