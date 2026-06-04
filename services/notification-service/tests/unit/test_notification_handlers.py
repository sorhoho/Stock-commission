"""Unit tests for app/domain/notification_handlers.py.

The handlers build a NotificationEvent from a raw event ``data`` dict and
dispatch it through module-level singleton clients (``_email_client`` /
``_sms_client``).  We patch those singletons with AsyncMocks (autospec'd
against the real client classes) so call signatures are enforced and no real
SMTP/HTTP I/O happens.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.domain import notification_handlers as handlers
from app.infrastructure.email.smtp_client import SmtpClient
from app.infrastructure.sms.sms_client import SmsClient


@pytest.fixture
def patched_clients():
    """Patch the module-level email/SMS singletons with autospec'd AsyncMocks."""
    email = AsyncMock(spec=SmtpClient)
    email.send_email = AsyncMock(return_value="msg-email-1")
    sms = AsyncMock(spec=SmsClient)
    sms.send_sms = AsyncMock(return_value="msg-sms-1")
    with patch.object(handlers, "_email_client", email), patch.object(
        handlers, "_sms_client", sms
    ):
        yield email, sms


class TestDispatch:
    async def test_email_channel_invokes_smtp_with_correct_payload(self, patched_clients):
        email, sms = patched_clients
        from app.domain.models import NotificationChannel, NotificationEvent

        evt = NotificationEvent(
            party_id="p-1",
            party_email="dealer@example.com",
            message="body text",
            subject="A Subject",
            channel=[NotificationChannel.EMAIL],
        )
        results = await handlers._dispatch(evt)

        email.send_email.assert_awaited_once_with(
            to_address="dealer@example.com",
            subject="A Subject",
            body="body text",
        )
        sms.send_sms.assert_not_awaited()
        assert len(results) == 1
        assert results[0].channel == NotificationChannel.EMAIL
        assert results[0].status == "mocked"
        assert "dealer@example.com" in results[0].detail

    async def test_email_channel_skipped_when_no_address(self, patched_clients):
        email, _ = patched_clients
        from app.domain.models import NotificationChannel, NotificationEvent

        evt = NotificationEvent(
            party_id="p-1",
            party_email=None,
            message="body",
            subject="subj",
            channel=[NotificationChannel.EMAIL],
        )
        results = await handlers._dispatch(evt)
        email.send_email.assert_not_awaited()
        assert results == []

    async def test_sms_channel_invokes_sms_client(self, patched_clients):
        email, sms = patched_clients
        from app.domain.models import NotificationChannel, NotificationEvent

        evt = NotificationEvent(
            party_id="p-1",
            party_phone="+15551112222",
            message="short sms",
            subject="ignored for sms",
            channel=[NotificationChannel.SMS],
        )
        results = await handlers._dispatch(evt)
        sms.send_sms.assert_awaited_once_with(
            to_number="+15551112222",
            message="short sms",
        )
        email.send_email.assert_not_awaited()
        assert results[0].channel == NotificationChannel.SMS

    async def test_sms_channel_skipped_when_no_phone(self, patched_clients):
        _, sms = patched_clients
        from app.domain.models import NotificationChannel, NotificationEvent

        evt = NotificationEvent(
            party_id="p-1",
            party_phone=None,
            message="m",
            subject="s",
            channel=[NotificationChannel.SMS],
        )
        results = await handlers._dispatch(evt)
        sms.send_sms.assert_not_awaited()
        assert results == []

    async def test_webhook_channel_is_mocked_without_clients(self, patched_clients):
        email, sms = patched_clients
        from app.domain.models import NotificationChannel, NotificationEvent

        evt = NotificationEvent(
            party_id="p-1",
            message="m",
            subject="s",
            channel=[NotificationChannel.WEBHOOK],
        )
        results = await handlers._dispatch(evt)
        email.send_email.assert_not_awaited()
        sms.send_sms.assert_not_awaited()
        assert results[0].channel == NotificationChannel.WEBHOOK
        assert results[0].status == "mocked"

    async def test_multi_channel_shares_one_notification_id(self, patched_clients):
        from app.domain.models import NotificationChannel, NotificationEvent

        evt = NotificationEvent(
            party_id="p-1",
            party_email="d@example.com",
            party_phone="+15550000000",
            message="m",
            subject="s",
            channel=[NotificationChannel.EMAIL, NotificationChannel.SMS],
        )
        results = await handlers._dispatch(evt)
        assert len(results) == 2
        assert results[0].notification_id == results[1].notification_id

    async def test_send_failure_recorded_as_failed_result(self, patched_clients):
        email, _ = patched_clients
        email.send_email.side_effect = RuntimeError("smtp down")
        from app.domain.models import NotificationChannel, NotificationEvent

        evt = NotificationEvent(
            party_id="p-1",
            party_email="d@example.com",
            message="m",
            subject="s",
            channel=[NotificationChannel.EMAIL],
        )
        results = await handlers._dispatch(evt)
        assert results[0].status == "failed"
        assert "smtp down" in results[0].detail


class TestHandleDealerOnboarded:
    async def test_builds_welcome_email(self, patched_clients):
        email, sms = patched_clients
        await handlers.handle_dealer_onboarded(
            {
                "party_id": "dealer-1",
                "name": "Acme Telco",
                "email": "acme@example.com",
                "phone": "+15551234567",
                "tenant_id": "t-1",
            }
        )
        email.send_email.assert_awaited_once()
        kwargs = email.send_email.await_args.kwargs
        assert kwargs["to_address"] == "acme@example.com"
        assert kwargs["subject"] == "Welcome to Telco Distribution Network"
        assert "Dear Acme Telco" in kwargs["body"]
        # dealer_onboarded is EMAIL-only — SMS must not be sent even with phone
        sms.send_sms.assert_not_awaited()

    async def test_no_email_means_no_send(self, patched_clients):
        email, _ = patched_clients
        await handlers.handle_dealer_onboarded(
            {"party_id": "dealer-1", "name": "Acme"}
        )
        email.send_email.assert_not_awaited()


class TestHandlePayoutCompleted:
    async def test_sends_both_email_and_sms(self, patched_clients):
        email, sms = patched_clients
        await handlers.handle_payout_completed(
            {
                "party_id": "dealer-2",
                "amount": 1234.5,
                "currency": "USD",
                "external_reference": "REF-99",
                "processed_at": "2026-01-01T00:00:00Z",
                "email": "dealer2@example.com",
                "phone": "+15559998888",
                "tenant_id": "t-1",
            }
        )
        email.send_email.assert_awaited_once()
        sms.send_sms.assert_awaited_once()

        e_kwargs = email.send_email.await_args.kwargs
        assert e_kwargs["subject"] == "Payout Confirmed: USD 1,234.50"
        assert "REF-99" in e_kwargs["body"]
        assert "USD 1,234.50" in e_kwargs["body"]

        s_kwargs = sms.send_sms.await_args.kwargs
        assert s_kwargs["to_number"] == "+15559998888"
        assert "1,234.50" in s_kwargs["message"]

    async def test_only_email_when_no_phone(self, patched_clients):
        email, sms = patched_clients
        await handlers.handle_payout_completed(
            {
                "party_id": "dealer-2",
                "amount": 100,
                "currency": "EUR",
                "email": "d@example.com",
            }
        )
        email.send_email.assert_awaited_once()
        sms.send_sms.assert_not_awaited()


class TestHandleCommissionStatementConfirmed:
    async def test_builds_statement_email(self, patched_clients):
        email, sms = patched_clients
        await handlers.handle_commission_statement_confirmed(
            {
                "party_id": "dealer-3",
                "statement_id": "STMT-7",
                "period_year": 2026,
                "period_month": 3,
                "total_commission": 5000.0,
                "currency": "USD",
                "email": "dealer3@example.com",
                "tenant_id": "t-1",
            }
        )
        email.send_email.assert_awaited_once()
        kwargs = email.send_email.await_args.kwargs
        # month is zero-padded via :02d
        assert kwargs["subject"] == "Commission Statement Ready — 2026/03"
        assert "STMT-7" in kwargs["body"]
        assert "USD 5,000.00" in kwargs["body"]
        sms.send_sms.assert_not_awaited()


class TestHandleStockTransferCompleted:
    async def test_builds_stock_transfer_email(self, patched_clients):
        email, _ = patched_clients
        await handlers.handle_stock_transfer_completed(
            {
                "transfer_id": "TR-1",
                "transfer_order_number": "TO-100",
                "product_id": "prod-9",
                "destination_location_id": "loc-5",
                "quantity": 50,
                "tenant_id": "t-1",
                "destination_contact_email": "warehouse@example.com",
            }
        )
        email.send_email.assert_awaited_once()
        kwargs = email.send_email.await_args.kwargs
        assert kwargs["to_address"] == "warehouse@example.com"
        assert kwargs["subject"] == "Stock Transfer Received — Order TO-100"
        assert "50 units" in kwargs["body"]
        assert "loc-5" in kwargs["body"]

    async def test_no_recipient_email_skips_send(self, patched_clients):
        email, _ = patched_clients
        await handlers.handle_stock_transfer_completed(
            {
                "transfer_id": "TR-1",
                "transfer_order_number": "TO-100",
                "destination_location_id": "loc-5",
                "quantity": 10,
            }
        )
        email.send_email.assert_not_awaited()
