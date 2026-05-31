"""Pydantic v2 domain models for the notification-service."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class NotificationChannel(StrEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEBHOOK = "WEBHOOK"


class NotificationEvent(BaseModel):
    """Internal notification request — assembled from Kafka events before dispatch."""

    party_id: str
    party_email: str | None = None
    party_phone: str | None = None
    message: str
    subject: str
    channel: list[NotificationChannel] = Field(default_factory=lambda: [NotificationChannel.EMAIL])
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationResult(BaseModel):
    """Result of sending a notification (for logging / tracing)."""

    notification_id: str
    party_id: str
    channel: NotificationChannel
    status: str  # "sent" | "failed" | "mocked"
    detail: str = ""
