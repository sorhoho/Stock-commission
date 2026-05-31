"""Async SMS gateway client.

In mock mode (sms_mock=True, the default) messages are logged via structlog.
Set sms_mock=False and configure sms_gateway_url to enable real delivery via
an HTTP-based SMS gateway (e.g. Twilio, Vonage, Africa's Talking).
"""

from __future__ import annotations

import uuid

import structlog

from app.config import settings

log = structlog.get_logger(__name__)


class SmsClient:
    """Sends SMS messages via an HTTP gateway with mock support."""

    async def send_sms(self, to_number: str, message: str) -> str:
        """Send an SMS and return a synthetic message-id.

        When ``sms_mock`` is True the SMS is not actually sent; the content
        is logged at INFO level.
        """
        message_id = str(uuid.uuid4())

        if settings.sms_mock or not settings.sms_gateway_url:
            log.info(
                "[MOCK SMS] Would send SMS",
                to=to_number,
                message_preview=message[:120],
                message_id=message_id,
            )
            return message_id

        # Real gateway delivery (production path)
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.sms_gateway_url,
                json={"to": to_number, "message": message},
            )
            response.raise_for_status()

        log.info("SMS sent", to=to_number, message_id=message_id)
        return message_id
