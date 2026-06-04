"""Unit tests for notification domain models (app/domain/models.py)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationResult,
)


class TestNotificationChannel:
    def test_enum_values(self):
        assert NotificationChannel.EMAIL == "EMAIL"
        assert NotificationChannel.SMS == "SMS"
        assert NotificationChannel.WEBHOOK == "WEBHOOK"

    def test_is_str_enum(self):
        # StrEnum members compare/serialize as plain strings.
        assert NotificationChannel.EMAIL.value == "EMAIL"
        assert str(NotificationChannel.SMS) == "SMS"

    def test_invalid_member(self):
        with pytest.raises(ValueError):
            NotificationChannel("PIGEON")


class TestNotificationEvent:
    def test_minimal_valid_event_defaults_to_email_channel(self):
        evt = NotificationEvent(
            party_id="p-1",
            message="hello",
            subject="hi",
        )
        assert evt.party_id == "p-1"
        # default_factory yields a fresh [EMAIL] list
        assert evt.channel == [NotificationChannel.EMAIL]
        assert evt.party_email is None
        assert evt.party_phone is None
        assert evt.metadata == {}

    def test_default_channel_is_independent_per_instance(self):
        a = NotificationEvent(party_id="a", message="m", subject="s")
        b = NotificationEvent(party_id="b", message="m", subject="s")
        a.channel.append(NotificationChannel.SMS)
        # b must not share the mutable default
        assert b.channel == [NotificationChannel.EMAIL]

    def test_multi_channel_event(self):
        evt = NotificationEvent(
            party_id="p-1",
            party_email="d@example.com",
            party_phone="+15551234567",
            message="m",
            subject="s",
            channel=[NotificationChannel.EMAIL, NotificationChannel.SMS],
            metadata={"tenant_id": "t-1"},
        )
        assert evt.channel == [NotificationChannel.EMAIL, NotificationChannel.SMS]
        assert evt.metadata["tenant_id"] == "t-1"

    def test_channel_coerced_from_string(self):
        evt = NotificationEvent(
            party_id="p-1", message="m", subject="s", channel=["SMS"]
        )
        assert evt.channel == [NotificationChannel.SMS]

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            NotificationEvent(party_id="p-1", subject="s")  # missing message

    def test_invalid_channel_value_raises(self):
        with pytest.raises(ValidationError):
            NotificationEvent(
                party_id="p-1", message="m", subject="s", channel=["FAX"]
            )


class TestNotificationResult:
    def test_valid_result(self):
        res = NotificationResult(
            notification_id="n-1",
            party_id="p-1",
            channel=NotificationChannel.EMAIL,
            status="sent",
            detail="ok",
        )
        assert res.status == "sent"
        assert res.channel == NotificationChannel.EMAIL

    def test_detail_defaults_to_empty_string(self):
        res = NotificationResult(
            notification_id="n-1",
            party_id="p-1",
            channel=NotificationChannel.SMS,
            status="mocked",
        )
        assert res.detail == ""

    def test_model_dump_round_trip(self):
        res = NotificationResult(
            notification_id="n-1",
            party_id="p-1",
            channel=NotificationChannel.WEBHOOK,
            status="mocked",
            detail="Webhook mock",
        )
        dumped = res.model_dump()
        assert dumped["channel"] == NotificationChannel.WEBHOOK
        assert dumped["detail"] == "Webhook mock"

    def test_invalid_channel_enum_raises(self):
        with pytest.raises(ValidationError):
            NotificationResult(
                notification_id="n-1",
                party_id="p-1",
                channel="TELEGRAM",
                status="sent",
            )
