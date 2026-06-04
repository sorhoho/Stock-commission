"""Unit tests for the channel clients.

app/infrastructure/email/smtp_client.py and
app/infrastructure/sms/sms_client.py are thin async wrappers with a mock path
(the default) and a real-delivery path.  Both paths are exercised here with
the transport fully mocked — ``aiosmtplib.SMTP`` and ``httpx.AsyncClient`` are
patched so no real network call is made — and we assert on the constructed
message/payload, not just that the mock was called.
"""

from __future__ import annotations

import sys
import types
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.email import smtp_client as smtp_mod
from app.infrastructure.sms import sms_client as sms_mod
from app.infrastructure.email.smtp_client import SmtpClient
from app.infrastructure.sms.sms_client import SmsClient


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


class TestSmtpClientMockMode:
    async def test_mock_mode_returns_uuid_message_id_without_network(self):
        client = SmtpClient()
        # smtp_mock defaults to True; assert no aiosmtplib import/use happens by
        # making the module raise if touched.
        with patch.object(smtp_mod.settings, "smtp_mock", True), \
             patch.dict(sys.modules, {"aiosmtplib": None}):
            message_id = await client.send_email(
                to_address="dealer@example.com",
                subject="Hi",
                body="hello world",
            )
        assert _is_uuid(message_id)

    async def test_mock_mode_does_not_call_smtp_transport(self):
        client = SmtpClient()
        fake_aiosmtplib = MagicMock()
        with patch.object(smtp_mod.settings, "smtp_mock", True), \
             patch.dict(sys.modules, {"aiosmtplib": fake_aiosmtplib}):
            await client.send_email(to_address="d@example.com", subject="s", body="b")
        fake_aiosmtplib.SMTP.assert_not_called()


class TestSmtpClientRealMode:
    async def test_real_delivery_constructs_message_and_sends(self):
        client = SmtpClient()

        smtp_instance = AsyncMock()
        # async context manager protocol
        smtp_ctx = MagicMock()
        smtp_ctx.__aenter__ = AsyncMock(return_value=smtp_instance)
        smtp_ctx.__aexit__ = AsyncMock(return_value=False)

        fake_aiosmtplib = types.ModuleType("aiosmtplib")
        fake_aiosmtplib.SMTP = MagicMock(return_value=smtp_ctx)

        with patch.object(smtp_mod.settings, "smtp_mock", False), \
             patch.object(smtp_mod.settings, "smtp_host", "smtp.test"), \
             patch.object(smtp_mod.settings, "smtp_port", 2525), \
             patch.object(smtp_mod.settings, "smtp_user", "no-reply@telco.local"), \
             patch.object(smtp_mod.settings, "smtp_password", "secret"), \
             patch.object(smtp_mod.settings, "smtp_from_name", "Telco Distribution"), \
             patch.dict(sys.modules, {"aiosmtplib": fake_aiosmtplib}):
            message_id = await client.send_email(
                to_address="dealer@example.com",
                subject="Payout Confirmed",
                body="Your payout is ready.",
            )

        # SMTP constructed against configured host/port with TLS.
        _, kwargs = fake_aiosmtplib.SMTP.call_args
        assert kwargs["hostname"] == "smtp.test"
        assert kwargs["port"] == 2525
        assert kwargs["start_tls"] is True

        # login uses configured credentials
        smtp_instance.login.assert_awaited_once_with("no-reply@telco.local", "secret")

        # sendmail: envelope sender, recipient list, and the RFC822 message body
        smtp_instance.sendmail.assert_awaited_once()
        sender, recipients, message = smtp_instance.sendmail.await_args.args
        assert sender == "no-reply@telco.local"
        assert recipients == ["dealer@example.com"]
        assert "From: Telco Distribution <no-reply@telco.local>" in message
        assert "To: dealer@example.com" in message
        assert "Subject: Payout Confirmed" in message
        assert f"Message-ID: <{message_id}>" in message
        assert "Content-Type: text/plain; charset=utf-8" in message
        assert message.endswith("Your payout is ready.")

    async def test_explicit_from_address_overrides_default(self):
        client = SmtpClient()
        smtp_instance = AsyncMock()
        smtp_ctx = MagicMock()
        smtp_ctx.__aenter__ = AsyncMock(return_value=smtp_instance)
        smtp_ctx.__aexit__ = AsyncMock(return_value=False)
        fake_aiosmtplib = types.ModuleType("aiosmtplib")
        fake_aiosmtplib.SMTP = MagicMock(return_value=smtp_ctx)

        with patch.object(smtp_mod.settings, "smtp_mock", False), \
             patch.object(smtp_mod.settings, "smtp_user", "no-reply@telco.local"), \
             patch.dict(sys.modules, {"aiosmtplib": fake_aiosmtplib}):
            await client.send_email(
                to_address="d@example.com",
                subject="s",
                body="b",
                from_address="Custom <custom@telco.local>",
            )
        _, _, message = smtp_instance.sendmail.await_args.args
        assert "From: Custom <custom@telco.local>" in message


class TestSmsClientMockMode:
    async def test_mock_mode_returns_uuid_without_network(self):
        client = SmsClient()
        fake_httpx = MagicMock()
        with patch.object(sms_mod.settings, "sms_mock", True), \
             patch.dict(sys.modules, {"httpx": fake_httpx}):
            message_id = await client.send_sms(to_number="+15551234567", message="hi")
        assert _is_uuid(message_id)
        fake_httpx.AsyncClient.assert_not_called()

    async def test_no_gateway_url_falls_back_to_mock(self):
        client = SmsClient()
        fake_httpx = MagicMock()
        # sms_mock False but no gateway url -> still mock path
        with patch.object(sms_mod.settings, "sms_mock", False), \
             patch.object(sms_mod.settings, "sms_gateway_url", None), \
             patch.dict(sys.modules, {"httpx": fake_httpx}):
            message_id = await client.send_sms(to_number="+1555", message="m")
        assert _is_uuid(message_id)
        fake_httpx.AsyncClient.assert_not_called()


class TestSmsClientRealMode:
    async def test_real_delivery_posts_payload_and_raises_for_status(self):
        client = SmsClient()

        response = MagicMock()
        response.raise_for_status = MagicMock()

        http_instance = MagicMock()
        http_instance.post = AsyncMock(return_value=response)
        http_ctx = MagicMock()
        http_ctx.__aenter__ = AsyncMock(return_value=http_instance)
        http_ctx.__aexit__ = AsyncMock(return_value=False)

        fake_httpx = types.ModuleType("httpx")
        fake_httpx.AsyncClient = MagicMock(return_value=http_ctx)

        with patch.object(sms_mod.settings, "sms_mock", False), \
             patch.object(sms_mod.settings, "sms_gateway_url", "https://gw.test/send"), \
             patch.dict(sys.modules, {"httpx": fake_httpx}):
            message_id = await client.send_sms(
                to_number="+15559998888",
                message="Your payout of USD 100 is ready.",
            )

        assert _is_uuid(message_id)
        # client built with a timeout
        _, kwargs = fake_httpx.AsyncClient.call_args
        assert kwargs["timeout"] == 10.0
        # POST to the gateway with the expected JSON body
        http_instance.post.assert_awaited_once()
        post_args, post_kwargs = http_instance.post.await_args
        assert post_args[0] == "https://gw.test/send"
        assert post_kwargs["json"] == {
            "to": "+15559998888",
            "message": "Your payout of USD 100 is ready.",
        }
        response.raise_for_status.assert_called_once()

    async def test_gateway_error_propagates(self):
        client = SmsClient()

        response = MagicMock()
        response.raise_for_status = MagicMock(side_effect=RuntimeError("502 bad gateway"))
        http_instance = MagicMock()
        http_instance.post = AsyncMock(return_value=response)
        http_ctx = MagicMock()
        http_ctx.__aenter__ = AsyncMock(return_value=http_instance)
        http_ctx.__aexit__ = AsyncMock(return_value=False)
        fake_httpx = types.ModuleType("httpx")
        fake_httpx.AsyncClient = MagicMock(return_value=http_ctx)

        with patch.object(sms_mod.settings, "sms_mock", False), \
             patch.object(sms_mod.settings, "sms_gateway_url", "https://gw.test/send"), \
             patch.dict(sys.modules, {"httpx": fake_httpx}):
            with pytest.raises(RuntimeError, match="502 bad gateway"):
                await client.send_sms(to_number="+1555", message="m")
