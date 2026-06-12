"""Domain handlers for notification events.

Each handler receives a raw CloudEvent ``data`` dict, extracts the relevant
fields, constructs a ``NotificationEvent``, and dispatches it through the
appropriate channel clients.

All external integrations (SMTP, SMS) are mocked by default — see
app/infrastructure/email/smtp_client.py and app/infrastructure/sms/sms_client.py.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.domain.models import NotificationChannel, NotificationEvent, NotificationResult
from app.infrastructure.email.smtp_client import SmtpClient
from app.infrastructure.sms.sms_client import SmsClient

log = structlog.get_logger(__name__)

_email_client = SmtpClient()
_sms_client = SmsClient()


async def _dispatch(notification: NotificationEvent) -> list[NotificationResult]:
    """Send a notification across all requested channels."""
    results: list[NotificationResult] = []
    notification_id = str(uuid.uuid4())

    for channel in notification.channel:
        try:
            if channel == NotificationChannel.EMAIL:
                if not notification.party_email:
                    log.warning("EMAIL channel requested but no email address", party_id=notification.party_id)
                    continue
                await _email_client.send_email(
                    to_address=notification.party_email,
                    subject=notification.subject,
                    body=notification.message,
                )
                results.append(
                    NotificationResult(
                        notification_id=notification_id,
                        party_id=notification.party_id,
                        channel=channel,
                        status="mocked",
                        detail=f"Email to {notification.party_email}",
                    )
                )

            elif channel == NotificationChannel.SMS:
                if not notification.party_phone:
                    log.warning("SMS channel requested but no phone number", party_id=notification.party_id)
                    continue
                await _sms_client.send_sms(
                    to_number=notification.party_phone,
                    message=notification.message,
                )
                results.append(
                    NotificationResult(
                        notification_id=notification_id,
                        party_id=notification.party_id,
                        channel=channel,
                        status="mocked",
                        detail=f"SMS to {notification.party_phone}",
                    )
                )

            elif channel == NotificationChannel.WEBHOOK:
                # Webhook dispatch is handled by the webhook_base_url config
                log.info(
                    "[MOCK WEBHOOK] Would POST notification",
                    party_id=notification.party_id,
                    subject=notification.subject,
                )
                results.append(
                    NotificationResult(
                        notification_id=notification_id,
                        party_id=notification.party_id,
                        channel=channel,
                        status="mocked",
                        detail="Webhook mock",
                    )
                )

        except Exception as exc:
            log.exception(
                "Notification dispatch failed",
                channel=channel,
                party_id=notification.party_id,
                error=str(exc),
            )
            results.append(
                NotificationResult(
                    notification_id=notification_id,
                    party_id=notification.party_id,
                    channel=channel,
                    status="failed",
                    detail=str(exc),
                )
            )

    return results


# ---------------------------------------------------------------------------
# Per-event handlers
# ---------------------------------------------------------------------------


async def handle_dealer_onboarded(event_data: dict[str, Any]) -> None:
    """Send a welcome email/SMS when a new dealer is onboarded.

    Expected event_data shape: PartyOnboardedData
    """
    log.info("Handling dealer_onboarded notification", event_data=event_data)

    party_id = event_data.get("party_id", "unknown")
    name = event_data.get("name", "Dealer")
    email = event_data.get("email")  # may not be in base schema — best-effort
    phone = event_data.get("phone")
    tenant_id = event_data.get("tenant_id", "")

    notification = NotificationEvent(
        party_id=party_id,
        party_email=email,
        party_phone=phone,
        subject="Welcome to Telco Distribution Network",
        message=(
            f"Dear {name},\n\n"
            "Welcome to the Telco Distribution Network. Your dealer account has been "
            "successfully created. You can now log in to the portal to manage your "
            "inventory, view commission statements, and track payouts.\n\n"
            "If you have any questions, please contact your regional manager.\n\n"
            "Best regards,\nTelco Distribution Team"
        ),
        channel=[NotificationChannel.EMAIL],
        metadata={"tenant_id": tenant_id, "event": "dealer_onboarded"},
    )

    results = await _dispatch(notification)
    log.info(
        "dealer_onboarded notification dispatched",
        party_id=party_id,
        results=[r.model_dump() for r in results],
    )


async def handle_payout_completed(event_data: dict[str, Any]) -> None:
    """Notify a dealer that their payout has been processed.

    Expected event_data shape: PayoutRequestCompletedData
    """
    log.info("Handling payout_completed notification", event_data=event_data)

    party_id = event_data.get("party_id", "unknown")
    amount = event_data.get("amount", 0)
    currency = event_data.get("currency", "THB")
    external_ref = event_data.get("external_reference", "N/A")
    processed_at = event_data.get("processed_at", "")
    email = event_data.get("email")
    phone = event_data.get("phone")
    tenant_id = event_data.get("tenant_id", "")

    notification = NotificationEvent(
        party_id=party_id,
        party_email=email,
        party_phone=phone,
        subject=f"Payout Confirmed: {currency} {amount:,.2f}",
        message=(
            f"Dear Dealer,\n\n"
            f"Your payout of {currency} {amount:,.2f} has been successfully processed.\n\n"
            f"Reference: {external_ref}\n"
            f"Processed at: {processed_at}\n\n"
            "If you have any questions, please contact support.\n\n"
            "Best regards,\nTelco Distribution Team"
        ),
        channel=[NotificationChannel.EMAIL, NotificationChannel.SMS],
        metadata={
            "tenant_id": tenant_id,
            "event": "payout_completed",
            "amount": amount,
            "currency": currency,
        },
    )

    results = await _dispatch(notification)
    log.info(
        "payout_completed notification dispatched",
        party_id=party_id,
        results=[r.model_dump() for r in results],
    )


async def handle_commission_statement_confirmed(event_data: dict[str, Any]) -> None:
    """Notify a dealer that their commission statement for the period is ready.

    Expected event_data shape: CommissionStatementConfirmedData
    """
    log.info("Handling commission_statement_confirmed notification", event_data=event_data)

    party_id = event_data.get("party_id", "unknown")
    statement_id = event_data.get("statement_id", "")
    period_year = event_data.get("period_year", "")
    period_month = event_data.get("period_month", "")
    total_commission = event_data.get("total_commission", 0)
    currency = event_data.get("currency", "THB")
    email = event_data.get("email")
    tenant_id = event_data.get("tenant_id", "")

    notification = NotificationEvent(
        party_id=party_id,
        party_email=email,
        subject=f"Commission Statement Ready — {period_year}/{period_month:02d}",
        message=(
            f"Dear Dealer,\n\n"
            f"Your commission statement for {period_year}/{period_month:02d} is now available.\n\n"
            f"Statement ID: {statement_id}\n"
            f"Total Commission: {currency} {total_commission:,.2f}\n\n"
            "Log in to the portal to view and download your statement.\n\n"
            "Best regards,\nTelco Distribution Team"
        ),
        channel=[NotificationChannel.EMAIL],
        metadata={
            "tenant_id": tenant_id,
            "event": "commission_statement_confirmed",
            "statement_id": statement_id,
        },
    )

    results = await _dispatch(notification)
    log.info(
        "commission_statement_confirmed notification dispatched",
        party_id=party_id,
        results=[r.model_dump() for r in results],
    )


async def handle_stock_transfer_completed(event_data: dict[str, Any]) -> None:
    """Notify the receiving location manager that a stock transfer has arrived.

    Expected event_data shape: StockTransferredData
    """
    log.info("Handling stock_transfer_completed notification", event_data=event_data)

    transfer_id = event_data.get("transfer_id", "unknown")
    transfer_order_number = event_data.get("transfer_order_number", "unknown")
    product_id = event_data.get("product_id", "")
    destination_location_id = event_data.get("destination_location_id", "")
    quantity = event_data.get("quantity", 0)
    tenant_id = event_data.get("tenant_id", "")
    # In real usage, the receiving location manager's contact details would be
    # looked up from the party-service. Here we log a mock notification.
    recipient_email = event_data.get("destination_contact_email")

    notification = NotificationEvent(
        party_id=destination_location_id or "system",
        party_email=recipient_email,
        subject=f"Stock Transfer Received — Order {transfer_order_number}",
        message=(
            f"Stock transfer {transfer_order_number} (ID: {transfer_id}) has been delivered "
            f"to your location.\n\n"
            f"Product ID : {product_id}\n"
            f"Quantity   : {quantity} units\n"
            f"Location   : {destination_location_id}\n\n"
            "Please verify receipt in the inventory portal.\n\n"
            "Best regards,\nTelco Distribution Logistics"
        ),
        channel=[NotificationChannel.EMAIL],
        metadata={
            "tenant_id": tenant_id,
            "event": "stock_transfer_completed",
            "transfer_id": transfer_id,
        },
    )

    results = await _dispatch(notification)
    log.info(
        "stock_transfer_completed notification dispatched",
        transfer_id=transfer_id,
        results=[r.model_dump() for r in results],
    )
