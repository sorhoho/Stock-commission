"""Consumes all telco domain events and persists them to the append-only audit log."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.infrastructure.db.models import AuditLog
from app.infrastructure.db.repository import AuditLogRepository

logger = structlog.get_logger(__name__)


async def handle_any_event(event: dict, session) -> None:
    event_id = event.get("id", str(uuid.uuid4()))
    repo = AuditLogRepository(session)

    entry = AuditLog(
        id=uuid.uuid4(),
        event_id=event_id,
        event_type=event.get("type", "unknown"),
        event_source=event.get("source", "unknown"),
        tenant_id=event.get("tenantid", ""),
        correlation_id=event.get("correlationid", ""),
        event_time=event.get("time", datetime.now(UTC).isoformat()),
        payload=event,
    )
    await repo.insert(entry)
    logger.debug("Audit event persisted", event_id=event_id, event_type=event.get("type"))
