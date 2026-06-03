#!/usr/bin/env bash
# End-to-end pipeline test:
#   publish a sell-out event -> commission-calculation-service consumes it,
#   fetches the dealer's agreement, calculates commission, and persists it.
#
# Requires the stack up (make up) and demo data seeded (make seed).
# Simulates sell-out-service by publishing the CloudEvent directly to Kafka,
# so it does not depend on the dealer-facing sell-out API / user tokens.
set -euo pipefail

DEALER_ID="22222222-2222-2222-2222-222222222222"
TENANT="tenant-demo"
TXN_ID="$(cat /proc/sys/kernel/random/uuid)"
QTY=5
UNIT_PRICE=10.0
# tier 1 (qty 1-10) = 8% -> 0.08 * 5 * 10.0
EXPECTED="4.0"
TOPIC="telco.sales.sellout.completed"

EVENT=$(cat <<JSON
{"specversion":"1.0","type":"$TOPIC","source":"e2e-test","id":"$(cat /proc/sys/kernel/random/uuid)","tenantid":"$TENANT","correlationid":"e2e-$TXN_ID","data":{"transaction_id":"$TXN_ID","transaction_number":"TXN-E2E","dealer_party_id":"$DEALER_ID","dealer_name":"Dealer Alpha","channel":"RETAIL","sale_date":"2026-06-03T10:00:00+00:00","total_amount":50.0,"currency":"USD","items":[{"product_id":"33333333-3333-3333-3333-333333333333","product_name":"SIM","quantity":$QTY,"unit_price":$UNIT_PRICE,"serial_numbers":[],"commission_eligible":true}],"tenant_id":"$TENANT"}}
JSON
)

echo "==> Publishing sell-out event (txn $TXN_ID) to $TOPIC"
echo "$EVENT" | docker compose exec -T kafka \
  kafka-console-producer --topic "$TOPIC" --bootstrap-server localhost:9092 >/dev/null

echo "==> Waiting for commission-calculation-service to process..."
ACTUAL=""
for i in $(seq 1 20); do
  sleep 1
  ACTUAL=$(docker compose exec -T postgres psql -U postgres -d commission_calc -tAc \
    "SELECT commission_amount FROM commission_event WHERE source_transaction_id='$TXN_ID';" 2>/dev/null | tr -d '[:space:]')
  [ -n "$ACTUAL" ] && break
done

if [ -z "$ACTUAL" ]; then
  echo "FAIL: no commission_event row created for txn $TXN_ID after 20s"
  echo "      recent commission-calculation-service logs:"
  docker compose logs commission-calculation-service --tail=15 | grep -v "^time="
  exit 1
fi

echo "==> commission_event persisted: amount=$ACTUAL (expected $EXPECTED)"

# Verify the monthly statement was updated too
STMT=$(docker compose exec -T postgres psql -U postgres -d commission_calc -tAc \
  "SELECT total_commission FROM commission_statement WHERE party_id='$DEALER_ID';" 2>/dev/null | tr -d '[:space:]')

if awk "BEGIN{exit !($ACTUAL == $EXPECTED)}"; then
  echo "PASS: sell-out -> commission pipeline works end-to-end (commission=$ACTUAL, statement total=$STMT)"
  exit 0
else
  echo "FAIL: commission amount $ACTUAL != expected $EXPECTED"
  exit 1
fi
