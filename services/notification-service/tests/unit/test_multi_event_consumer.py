"""Unit tests for app/infrastructure/kafka/consumers/multi_event_consumer.py.

The consumer wires Kafka topics to notification handlers.  We mock the
KafkaConsumer (so no broker is contacted) and the handler functions, then
assert the routing closure dispatches each event ``type`` to the right handler
and ignores unknown types gracefully.
"""

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.kafka.consumers import multi_event_consumer as consumer
from telco_common.events import Topics


class TestTopicHandlerMapping:
    def test_all_four_topics_mapped(self):
        assert set(consumer.TOPIC_HANDLERS.keys()) == {
            Topics.PARTY_DEALER_ONBOARDED,
            Topics.PAYOUT_REQUEST_COMPLETED,
            Topics.COMMISSION_STATEMENT_CONFIRMED,
            Topics.INVENTORY_STOCK_TRANSFERRED,
        }

    def test_notification_topics_matches_handler_keys(self):
        assert consumer.NOTIFICATION_TOPICS == list(consumer.TOPIC_HANDLERS.keys())

    def test_each_topic_routes_to_expected_handler(self):
        assert (
            consumer.TOPIC_HANDLERS[Topics.PARTY_DEALER_ONBOARDED]
            is consumer.handle_dealer_onboarded
        )
        assert (
            consumer.TOPIC_HANDLERS[Topics.PAYOUT_REQUEST_COMPLETED]
            is consumer.handle_payout_completed
        )
        assert (
            consumer.TOPIC_HANDLERS[Topics.COMMISSION_STATEMENT_CONFIRMED]
            is consumer.handle_commission_statement_confirmed
        )
        assert (
            consumer.TOPIC_HANDLERS[Topics.INVENTORY_STOCK_TRANSFERRED]
            is consumer.handle_stock_transfer_completed
        )


@pytest.fixture
def routing_handler():
    """Start the consumer with a mocked KafkaConsumer and capture the
    routing closure passed to ``consume``.  All handler fns are AsyncMocks.

    The TOPIC_HANDLERS patch must stay active *while the captured closure is
    invoked* — the closure looks up TOPIC_HANDLERS at dispatch time, not at
    build time.  An ExitStack tied to the fixture lifetime keeps the patch
    open until the test finishes.
    """
    stack = contextlib.ExitStack()

    async def _build(patched_handlers: dict):
        fake_consumer = AsyncMock()
        captured = {}

        async def fake_consume(handler):
            captured["handler"] = handler

        fake_consumer.consume.side_effect = fake_consume

        stack.enter_context(
            patch.object(consumer, "KafkaConsumer", return_value=fake_consumer)
        )
        stack.enter_context(
            patch.dict(consumer.TOPIC_HANDLERS, patched_handlers, clear=False)
        )
        await consumer.start_notification_consumer()

        fake_consumer.start.assert_awaited_once()
        return captured["handler"], fake_consumer

    try:
        yield _build
    finally:
        stack.close()


class TestStartConsumerRouting:
    async def test_dealer_onboarded_event_routed(self, routing_handler):
        mock_handler = AsyncMock()
        handler, _ = await routing_handler(
            {Topics.PARTY_DEALER_ONBOARDED: mock_handler}
        )
        event = {"type": Topics.PARTY_DEALER_ONBOARDED, "party_id": "p-1"}
        await handler(event)
        mock_handler.assert_awaited_once_with(event)

    async def test_payout_event_routed(self, routing_handler):
        mock_handler = AsyncMock()
        handler, _ = await routing_handler(
            {Topics.PAYOUT_REQUEST_COMPLETED: mock_handler}
        )
        event = {"type": Topics.PAYOUT_REQUEST_COMPLETED, "amount": 10}
        await handler(event)
        mock_handler.assert_awaited_once_with(event)

    async def test_statement_event_routed(self, routing_handler):
        mock_handler = AsyncMock()
        handler, _ = await routing_handler(
            {Topics.COMMISSION_STATEMENT_CONFIRMED: mock_handler}
        )
        event = {"type": Topics.COMMISSION_STATEMENT_CONFIRMED}
        await handler(event)
        mock_handler.assert_awaited_once_with(event)

    async def test_stock_transfer_event_routed(self, routing_handler):
        mock_handler = AsyncMock()
        handler, _ = await routing_handler(
            {Topics.INVENTORY_STOCK_TRANSFERRED: mock_handler}
        )
        event = {"type": Topics.INVENTORY_STOCK_TRANSFERRED}
        await handler(event)
        mock_handler.assert_awaited_once_with(event)

    async def test_unknown_event_type_ignored(self, routing_handler):
        dealer = AsyncMock()
        handler, _ = await routing_handler(
            {Topics.PARTY_DEALER_ONBOARDED: dealer}
        )
        # An unrelated type must not invoke any handler and must not raise.
        await handler({"type": "telco.some.unknown.event"})
        dealer.assert_not_awaited()

    async def test_missing_type_key_ignored(self, routing_handler):
        dealer = AsyncMock()
        handler, _ = await routing_handler(
            {Topics.PARTY_DEALER_ONBOARDED: dealer}
        )
        # No "type" key -> event_type defaults to "" -> no handler, no error.
        await handler({"party_id": "p-1"})
        dealer.assert_not_awaited()

    async def test_consumer_started_with_correct_topics(self, routing_handler):
        with patch.object(consumer, "KafkaConsumer") as kc:
            kc.return_value = AsyncMock()
            await consumer.start_notification_consumer()
            _, kwargs = kc.call_args
            assert kwargs["group_id"] == "notification-service"
            assert kwargs["topics"] == consumer.NOTIFICATION_TOPICS
