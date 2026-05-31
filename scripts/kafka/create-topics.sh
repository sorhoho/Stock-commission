#!/usr/bin/env bash
# Creates all Kafka topics for the Telco Distribution & Commission system

set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9093}"
REPLICATION="${KAFKA_REPLICATION_FACTOR:-1}"

echo "Creating Kafka topics on $BOOTSTRAP..."

create_topic() {
  local topic="$1"
  local partitions="${2:-3}"
  local retention_ms="${3:-604800000}"  # 7 days default

  docker exec "$(docker-compose ps -q kafka 2>/dev/null || echo kafka)" \
    kafka-topics --bootstrap-server localhost:9092 \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions "$partitions" \
    --replication-factor "$REPLICATION" \
    --config "retention.ms=$retention_ms" \
    2>&1 || echo "  (topic may already exist)"

  echo "  ✓ $topic"
}

# Retention constants
WEEK_MS=604800000
MONTH_MS=2592000000
YEAR_7_MS=220752000000

echo "--- Inventory topics ---"
create_topic "telco.inventory.stock.transferred"   3 "$MONTH_MS"
create_topic "telco.inventory.stock.adjusted"      3 "$MONTH_MS"
create_topic "telco.inventory.stock.reserved"      3 "$WEEK_MS"

echo "--- Sales topics ---"
create_topic "telco.sales.sellout.completed"       6 "$YEAR_7_MS"
create_topic "telco.sales.sellout.reversed"        3 "$YEAR_7_MS"
create_topic "telco.sales.sellin.ordered"          3 "$MONTH_MS"
create_topic "telco.sales.sellin.delivered"        3 "$MONTH_MS"

echo "--- Commission topics ---"
create_topic "telco.commission.event.calculated"   3 "$YEAR_7_MS"
create_topic "telco.commission.statement.confirmed" 3 "$YEAR_7_MS"

echo "--- Payout topics ---"
create_topic "telco.payout.request.created"        3 "$YEAR_7_MS"
create_topic "telco.payout.request.completed"      3 "$YEAR_7_MS"

echo "--- Party topics ---"
create_topic "telco.party.dealer.onboarded"        3 "$MONTH_MS"

echo "--- Performance topics ---"
create_topic "telco.performance.measurement.recorded" 3 "$MONTH_MS"

echo "--- DLQ topics ---"
create_topic "telco.dlq.commission-calculation.telco.sales.sellout.completed" 1 "$YEAR_7_MS"
create_topic "telco.dlq.audit.telco.sales.sellout.completed" 1 "$YEAR_7_MS"
create_topic "telco.dlq.payout.telco.commission.statement.confirmed" 1 "$YEAR_7_MS"

echo ""
echo "All topics created successfully."
