"""Redis-backed CQRS read model for stock availability.

Key schema:
    stock:{tenant_id}:{product_id}:{location_id}  → Redis HASH
    Fields: product_name, location_type, available_quantity,
            reserved_quantity, last_updated

Note: the Redis client is created with decode_responses=True, so all
values are native Python strings (not bytes).
"""

from __future__ import annotations

import structlog
from typing import Any

from redis.asyncio import Redis

from telco_common.events.schemas.inventory_events import (
    StockAdjustedData,
    StockTransferredData,
)

logger = structlog.get_logger(__name__)


class StockReadModel:
    """Manages the Redis hash store used as the CQRS read model.

    All writes originate from Kafka events; the REST layer is read-only.
    The Redis client MUST be created with decode_responses=True so that
    all hash field values are plain strings, not bytes.
    """

    def __init__(self, redis_client: Redis, key_ttl: int = 86400) -> None:
        self._redis = redis_client
        self._ttl = key_ttl

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_hash(raw: dict) -> dict[str, str]:
        """Decode bytes keys/values that fakeredis returns even with decode_responses=True."""
        return {
            (k.decode() if isinstance(k, bytes) else str(k)):
            (v.decode() if isinstance(v, bytes) else str(v))
            for k, v in raw.items()
        }

    def _key(self, tenant_id: str, product_id: str, location_id: str) -> str:
        return f"stock:{tenant_id}:{product_id}:{location_id}"

    def _scan_pattern(
        self,
        tenant_id: str,
        product_id: str | None = None,
        location_id: str | None = None,
    ) -> str:
        prod = product_id or "*"
        loc = location_id or "*"
        return f"stock:{tenant_id}:{prod}:{loc}"

    # ------------------------------------------------------------------
    # Write path — called by Kafka consumers
    # ------------------------------------------------------------------

    async def update_from_adjustment(self, event_data: dict[str, Any]) -> None:
        """Handle StockAdjusted event: set available_quantity to new_quantity."""
        try:
            data = StockAdjustedData.model_validate(event_data)
        except Exception as exc:
            logger.exception("Failed to parse StockAdjustedData", error=str(exc), raw=event_data)
            return

        from datetime import UTC, datetime

        key = self._key(data.tenant_id, data.product_id, data.location_id)

        # Preserve existing product_name / location_type if already set
        existing: dict[str, str] = self._decode_hash(await self._redis.hgetall(key))
        product_name = existing.get("product_name", "unknown")
        location_type = existing.get("location_type", "unknown")
        reserved = int(existing.get("reserved_quantity", "0"))

        mapping: dict[str, Any] = {
            "product_name": product_name,
            "location_type": location_type,
            "available_quantity": data.new_quantity,
            "reserved_quantity": reserved,
            "last_updated": datetime.now(UTC).isoformat(),
        }
        await self._redis.hset(key, mapping=mapping)  # type: ignore[arg-type]
        await self._redis.expire(key, self._ttl)

        logger.info(
            "Stock read model updated from adjustment",
            product_id=data.product_id,
            location_id=data.location_id,
            new_quantity=data.new_quantity,
            tenant_id=data.tenant_id,
        )

    async def update_from_transfer(self, event_data: dict[str, Any]) -> None:
        """Handle StockTransferred event: decrement source, increment destination."""
        try:
            data = StockTransferredData.model_validate(event_data)
        except Exception as exc:
            logger.exception("Failed to parse StockTransferredData", error=str(exc), raw=event_data)
            return

        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()

        # --- Decrement source ---
        src_key = self._key(data.tenant_id, data.product_id, data.source_location_id)
        src: dict[str, str] = self._decode_hash(await self._redis.hgetall(src_key))
        if src:
            src_qty = max(0, int(src.get("available_quantity", "0")) - data.quantity)
            await self._redis.hset(  # type: ignore[arg-type]
                src_key,
                mapping={"available_quantity": src_qty, "last_updated": now},
            )
            await self._redis.expire(src_key, self._ttl)
        else:
            logger.warning(
                "Source location not found in read model during transfer",
                product_id=data.product_id,
                source_location_id=data.source_location_id,
                tenant_id=data.tenant_id,
            )

        # --- Increment destination ---
        dst_key = self._key(data.tenant_id, data.product_id, data.destination_location_id)
        dst: dict[str, str] = self._decode_hash(await self._redis.hgetall(dst_key))
        if dst:
            dst_qty = int(dst.get("available_quantity", "0")) + data.quantity
            await self._redis.hset(  # type: ignore[arg-type]
                dst_key,
                mapping={"available_quantity": dst_qty, "last_updated": now},
            )
        else:
            # Bootstrap destination entry from transfer data
            await self._redis.hset(  # type: ignore[arg-type]
                dst_key,
                mapping={
                    "product_name": "unknown",
                    "location_type": data.destination_location_type,
                    "available_quantity": data.quantity,
                    "reserved_quantity": 0,
                    "last_updated": now,
                },
            )
        await self._redis.expire(dst_key, self._ttl)

        logger.info(
            "Stock read model updated from transfer",
            product_id=data.product_id,
            quantity=data.quantity,
            source=data.source_location_id,
            destination=data.destination_location_id,
            tenant_id=data.tenant_id,
        )

    # ------------------------------------------------------------------
    # Read path — called by API handlers
    # ------------------------------------------------------------------

    async def query(
        self,
        tenant_id: str,
        product_id: str | None = None,
        location_id: str | None = None,
        min_quantity: int | None = None,
    ) -> list[dict[str, Any]]:
        """SCAN Redis keys matching the pattern, optionally filter by min_quantity.

        Uses async SCAN to avoid blocking the event loop on large key sets.
        All values are strings (decode_responses=True on the client).
        """
        pattern = self._scan_pattern(tenant_id, product_id, location_id)
        results: list[dict[str, Any]] = []

        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                key = key.decode() if isinstance(key, bytes) else key
                entry: dict[str, str] = self._decode_hash(await self._redis.hgetall(key))
                if not entry:
                    continue

                available = int(entry.get("available_quantity", "0"))
                reserved = int(entry.get("reserved_quantity", "0"))

                if min_quantity is not None and (available - reserved) < min_quantity:
                    continue

                # Parse tenant_id, product_id, location_id from key
                # Key format: stock:{tenant_id}:{product_id}:{location_id}
                parts = key.split(":")
                t_id = parts[1] if len(parts) > 1 else tenant_id
                p_id = parts[2] if len(parts) > 2 else ""
                l_id = parts[3] if len(parts) > 3 else ""

                results.append(
                    {
                        "product_id": p_id,
                        "product_name": entry.get("product_name", "unknown"),
                        "location_id": l_id,
                        "location_type": entry.get("location_type", "unknown"),
                        "available_quantity": available,
                        "reserved_quantity": reserved,
                        "last_updated": entry.get("last_updated", ""),
                        "tenant_id": t_id,
                    }
                )
            if cursor == 0:
                break

        return results

    async def get_availability(
        self,
        tenant_id: str,
        product_id: str,
        location_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single stock availability entry by exact key."""
        key = self._key(tenant_id, product_id, location_id)
        entry: dict[str, str] = self._decode_hash(await self._redis.hgetall(key))
        if not entry:
            return None

        return {
            "product_id": product_id,
            "product_name": entry.get("product_name", "unknown"),
            "location_id": location_id,
            "location_type": entry.get("location_type", "unknown"),
            "available_quantity": int(entry.get("available_quantity", "0")),
            "reserved_quantity": int(entry.get("reserved_quantity", "0")),
            "last_updated": entry.get("last_updated", ""),
            "tenant_id": tenant_id,
        }
