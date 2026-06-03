#!/usr/bin/env bash
# True HTTP-driven end-to-end test:
#   Keycloak token -> POST sale via sell-out API -> Kafka ->
#   commission-calculation-service fetches agreement -> commission persisted.
#
# Requires: make up && make seed, and the telco realm imported (Keycloak).
set -euo pipefail

KC=http://localhost:8080/realms/telco/protocol/openid-connect/token
SELL_OUT=http://localhost:8003/api/v1/salesManagement/saleTransaction
DEALER_ID="22222222-2222-2222-2222-222222222222"
TENANT="tenant-demo"
EXPECTED="4.0"   # 8% tier x 5 units x $10

echo "==> Acquiring access token (admin@telco.local via telco-frontend)"
TOK=$(curl -s -X POST "$KC" \
  -d "grant_type=password" -d "client_id=telco-frontend" \
  -d "username=admin@telco.local" -d "password=admin123" -d "scope=openid" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
if [ -z "$TOK" ]; then echo "FAIL: could not obtain token"; exit 1; fi

echo "==> POST sell-out transaction via authenticated API"
RESP=$(curl -s -X POST "$SELL_OUT" \
  -H "Authorization: Bearer $TOK" -H "X-Tenant-ID: $TENANT" -H "Content-Type: application/json" \
  -d "{\"dealer_party_id\":\"$DEALER_ID\",\"channel\":\"RETAIL\",\"items\":[{\"product_id\":\"33333333-3333-3333-3333-333333333333\",\"product_name\":\"SIM\",\"quantity\":5,\"unit_price\":10.0}]}")
TXN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)
if [ -z "$TXN" ]; then echo "FAIL: sale not created. Response: $RESP"; exit 1; fi
echo "    sale created: $TXN"

echo "==> Waiting for commission-calculation-service to process the Kafka event..."
AMT=""
for i in $(seq 1 20); do
  sleep 1
  AMT=$(docker compose exec -T postgres psql -U postgres -d commission_calc -tAc \
    "SELECT commission_amount FROM commission_event WHERE source_transaction_id='$TXN';" 2>/dev/null | tr -d '[:space:]')
  [ -n "$AMT" ] && break
done

if [ -z "$AMT" ]; then
  echo "FAIL: no commission calculated for sale $TXN after 20s"
  docker compose logs commission-calculation-service --tail=15 | grep -v "^time="
  exit 1
fi

if awk "BEGIN{exit !($AMT == $EXPECTED)}"; then
  echo "PASS: HTTP-driven pipeline works (token -> API sale $TXN -> commission=$AMT)"
  exit 0
else
  echo "FAIL: commission $AMT != expected $EXPECTED"
  exit 1
fi
