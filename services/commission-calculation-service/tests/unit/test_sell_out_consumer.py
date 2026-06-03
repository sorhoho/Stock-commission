"""
Regression tests for the sell-out consumer's commission-calculation path.

This path had zero coverage, which let a repository-signature mismatch
(passing a positional ORM object to a keyword-only create()) ship as a
latent runtime crash. These tests use autospec mocks so the repository
call signatures are enforced — a future drift fails the test instead of
production.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.kafka.consumers import sell_out_consumer as consumer


def _event(commission_type: str, commission_value: float, *, quantity: int = 5,
           tier_min: int = 0, tier_max: int | None = None) -> dict:
    return {
        "tenantid": "tenant-test-001",
        "correlationid": "corr-1",
        "data": {
            "transaction_id": "11111111-1111-1111-1111-111111111111",
            "transaction_number": "TXN-1",
            "dealer_party_id": "22222222-2222-2222-2222-222222222222",
            "dealer_name": "Dealer A",
            "channel": "RETAIL",
            "sale_date": "2026-01-15T10:00:00+00:00",
            "total_amount": 100.0,
            "currency": "USD",
            "items": [
                {
                    "product_id": "33333333-3333-3333-3333-333333333333",
                    "product_name": "SIM",
                    "quantity": quantity,
                    "unit_price": 10.0,
                    "serial_numbers": [],
                    "commission_eligible": True,
                }
            ],
            "tenant_id": "tenant-test-001",
        },
    }


def _agreement(commission_type: str, commission_value: float,
               tier_min: int = 0, tier_max: int | None = None) -> dict:
    return {
        "id": "44444444-4444-4444-4444-444444444444",
        "rules": [
            {
                "id": "55555555-5555-5555-5555-555555555555",
                "product_category": "*",
                "channel_type": None,
                "tier_min_qty": tier_min,
                "tier_max_qty": tier_max,
                "commission_type": commission_type,
                "commission_value": commission_value,
                "currency": "USD",
                "priority": 100,
            }
        ],
    }


@pytest.fixture
def patched_repos():
    """Autospec the three repositories so call signatures are enforced."""
    with patch.object(consumer, "CommissionEventRepository", autospec=True) as ev, \
         patch.object(consumer, "CommissionStatementRepository", autospec=True) as st, \
         patch.object(consumer, "ProcessedEventLogRepository", autospec=True) as lg:
        ev_inst = ev.return_value
        ev_inst.create.return_value = MagicMock(id="event-id-1")
        lg_inst = lg.return_value
        lg_inst.is_processed = AsyncMock(return_value=False)
        lg_inst.mark_processed = AsyncMock()
        st_inst = st.return_value
        st_inst.add_commission_to_draft = AsyncMock()
        yield ev_inst, st_inst, lg_inst


async def test_percentage_commission_persists_and_publishes(patched_repos, mock_kafka_producer):
    ev_inst, st_inst, lg_inst = patched_repos
    with patch.object(consumer, "_fetch_agreement_with_rules",
                      AsyncMock(return_value=_agreement("PERCENTAGE", 0.10))):
        await consumer.handle_sell_out_completed(
            _event("PERCENTAGE", 0.10), MagicMock(), mock_kafka_producer, "http://rules"
        )

    # create() must be called with keyword args matching the repo signature.
    # autospec raises TypeError here if a caller regresses to positional misuse.
    ev_inst.create.assert_awaited_once()
    kwargs = ev_inst.create.await_args.kwargs
    assert kwargs["commission_amount"] == 5.0  # 0.10 * 5 * 10.0
    assert kwargs["base_amount"] == 50.0
    lg_inst.mark_processed.assert_awaited_once()
    mock_kafka_producer.send.assert_awaited_once()


async def test_tiered_commission_uses_progressive_brackets(mock_kafka_producer):
    # Two tiered bands; quantity 70 -> 50@1.00 + 20@1.50 = 80.00
    agreement = {
        "id": "44444444-4444-4444-4444-444444444444",
        "rules": [
            {"id": "b1", "product_category": "*", "channel_type": None,
             "tier_min_qty": 1, "tier_max_qty": 50, "commission_type": "TIERED",
             "commission_value": 1.00, "currency": "USD", "priority": 100},
            {"id": "b2", "product_category": "*", "channel_type": None,
             "tier_min_qty": 51, "tier_max_qty": 100, "commission_type": "TIERED",
             "commission_value": 1.50, "currency": "USD", "priority": 100},
        ],
    }
    with patch.object(consumer, "CommissionEventRepository", autospec=True) as ev, \
         patch.object(consumer, "CommissionStatementRepository", autospec=True) as st, \
         patch.object(consumer, "ProcessedEventLogRepository", autospec=True) as lg, \
         patch.object(consumer, "_fetch_agreement_with_rules", AsyncMock(return_value=agreement)):
        ev.return_value.create.return_value = MagicMock(id="event-id-1")
        lg.return_value.is_processed = AsyncMock(return_value=False)
        lg.return_value.mark_processed = AsyncMock()
        st.return_value.add_commission_to_draft = AsyncMock()

        await consumer.handle_sell_out_completed(
            _event("TIERED", 0.0, quantity=70), MagicMock(), mock_kafka_producer, "http://rules"
        )

        assert ev.return_value.create.await_args.kwargs["commission_amount"] == 80.0


async def test_already_processed_event_is_skipped(patched_repos, mock_kafka_producer):
    ev_inst, st_inst, lg_inst = patched_repos
    lg_inst.is_processed = AsyncMock(return_value=True)  # idempotency: already done
    with patch.object(consumer, "_fetch_agreement_with_rules",
                      AsyncMock(return_value=_agreement("PERCENTAGE", 0.10))):
        await consumer.handle_sell_out_completed(
            _event("PERCENTAGE", 0.10), MagicMock(), mock_kafka_producer, "http://rules"
        )

    ev_inst.create.assert_not_awaited()
    mock_kafka_producer.send.assert_not_awaited()


async def test_no_agreement_skips_calculation(patched_repos, mock_kafka_producer):
    ev_inst, _, _ = patched_repos
    with patch.object(consumer, "_fetch_agreement_with_rules", AsyncMock(return_value=None)):
        await consumer.handle_sell_out_completed(
            _event("PERCENTAGE", 0.10), MagicMock(), mock_kafka_producer, "http://rules"
        )
    ev_inst.create.assert_not_awaited()
