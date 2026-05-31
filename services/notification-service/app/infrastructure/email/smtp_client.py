"""Async SMTP email sender.

In mock mode (smtp_mock=True, the default) all messages are logged via
structlog instead of being sent to a real mail server.  Set smtp_mock=False
and configure smtp_host / smtp_port / smtp_user / smtp_password to enable
real delivery.
"""

from __future__ import annotations

import uuid

import structlog

from app.config import settings

log = structlog.get_logger(__name__)


class SmtpClient:
    """Thin async wrapper around SMTP delivery with mock support."""

    async def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        from_address: str | None = None,
    ) -> str:
        """Send an email and return a message-id string.

        When ``smtp_mock`` is True the email is not actually sent; the content
        is logged at INFO level and a synthetic message-id is returned.
        """
        from_addr = from_address or f"{settings.smtp_from_name} <{settings.smtp_user}>"
        message_id = str(uuid.uuid4())

        if settings.smtp_mock:
            log.info(
                "[MOCK EMAIL] Would send email",
                to=to_address,
                subject=subject,
                from_address=from_addr,
                body_preview=body[:120],
                message_id=message_id,
            )
            return message_id

        # Real SMTP delivery (production path)
        import aiosmtplib  # optional dep — install when smtp_mock=False

        async with aiosmtplib.SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=True,
        ) as smtp:
            await smtp.login(settings.smtp_user, settings.smtp_password)
            message = (
                f"From: {from_addr}\r\n"
                f"To: {to_address}\r\n"
                f"Subject: {subject}\r\n"
                f"Message-ID: <{message_id}>\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                f"{body}"
            )
            await smtp.sendmail(settings.smtp_user, [to_address], message)

        log.info("Email sent", to=to_address, subject=subject, message_id=message_id)
        return message_id
