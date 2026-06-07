# Telco Distribution & Commission System — Operations Manual

## Who Should Read This

| Section | Audience |
|---|---|
| [Business Operations](#business-operations) | Branch managers, cashiers, warehouse staff, finance officers |
| [Technical Operations](#technical-operations) | DevOps engineers, backend developers, system administrators |

---

## Business Operations

### Daily Workflow Overview

```
Morning                     Day                         Evening
─────────────────────────────────────────────────────────────────
Open POS Session        →   Record sales / returns   →  Close POS Session
Assign pick lists       →   Pack & dispatch orders   →  Reconcile payout requests
Review inventory levels →   Handle sell-in orders    →  Review commission statements
```

---

### 1. POS Session Management

**Who:** Cashier / Branch Manager  
**Where:** `http://localhost:3000/sales/sessions`

#### Opening a Session

1. Navigate to **POS Sessions** in the left sidebar.
2. Enter your **Terminal ID** (e.g. `POS-01`), your **name**, and the **opening cash** amount in the till.
3. Click **Open Session**.
4. The session ID is stored in your browser. All sales made from this terminal will link to this session.

#### Closing a Session

1. Go to **POS Sessions** — the active session panel is shown at the top.
2. Review the **total transactions** and **total amount** recorded during the shift.
3. Count your physical cash and enter it as **Closing Cash**.
4. Click **Close Session**. The system records the variance between opening and closing cash.

> **Tip:** A session must be open before staff record sales. If the POS page shows a 422 error on sale submission, check whether a session is open first.

---

### 2. Recording a Sale (POS Sell-Out)

**Who:** Cashier  
**Where:** `http://localhost:3000/sales/pos`

1. Select the **Channel** (Retail, Online, Agent, Kiosk).
2. Optionally enter a **Payment Method** (Cash, Card, Mobile Money, Credit) and a reference number.
3. For each product line:
   - Enter the **Product ID** (UUID from the product catalog).
   - Enter the **product name**, **quantity**, and **unit price**.
   - Enter a **discount** if applicable.
   - The subtotal updates automatically.
4. Review the **Total** amount at the bottom.
5. Click **Record Sale**.
6. On success, the system:
   - Assigns a transaction number.
   - Deducts stock via the inventory service.
   - Triggers commission calculation automatically.

> **If you see a 422 error:** The stock quantity requested exceeds available stock. Reduce the quantity or confirm stock levels on the Inventory page before retrying.

---

### 3. Processing a Return / RMA

**Who:** Cashier / Customer Service  
**Where:** `http://localhost:3000/sales/returns`

1. Click **+ New Return**.
2. Enter the **Original Transaction ID** (visible on the sale receipt; optional if unknown).
3. Enter the **return reason** and the name of the person handling the return.
4. For each returned item: Product ID, quantity, and condition (Good / Damaged / Faulty).
5. Click **Submit Return** — the return is created with status **PENDING**.
6. A manager then approves or rejects it:
   - **Approve** → publishes a return event; inventory is restocked.
   - **Reject** → recorded for audit; no stock movement.

---

### 4. Inventory Management

**Who:** Warehouse Manager / Inventory Controller  
**Where:** `http://localhost:3000/inventory`

#### Checking Stock Levels

The inventory table shows every product-location combination with:
- **Quantity** on hand.
- **Status**: AVAILABLE, RESERVED (allocated to an order), or IN_TRANSIT.

#### Creating a Stock Transfer

Use this to move stock between locations (warehouse → dealer outlet, own shop → warehouse, etc.):

1. Click **Transfer Stock**.
2. Enter the Product ID, quantity, Source Location ID, and Destination Location ID.
3. Click **Create Transfer**.
4. The transfer appears in the system with status PENDING and is fulfilled by the warehouse team.

---

### 5. Warehouse Operations

**Who:** Warehouse Picker, Packing Supervisor  
**Where:** `http://localhost:3000/warehouse`

Three tabs: **Pick Lists**, **Packing Slips**, **Bin Locations**.

#### Pick Lists — Fulfilling an Order

| Step | Action |
|---|---|
| 1. Receive | Pick list created automatically when a sell-out or replenishment order is submitted. |
| 2. Assign | Manager clicks **Assign** on a PENDING pick list and enters the picker's worker ID. |
| 3. Pick | Picker walks the warehouse and collects items from the bin locations shown. |
| 4. Complete | Supervisor clicks **Complete** to confirm quantities picked. Short picks are recorded automatically. |

#### Packing Slips — Dispatching an Order

1. Once a pick list is **COMPLETED**, go to **Packing Slips** → **+ New Packing Slip**.
2. Enter the **Pick List ID**, the packer's name, and each item quantity.
3. Click **Create Slip**.
4. When ready to ship, click **Dispatch** → enter the **carrier** (DHL, FedEx, etc.) and **tracking number**.
5. Status changes to **DISPATCHED** and a warehouse dispatch event is published.

#### Bin Locations — Registering Storage Locations

1. Go to **Bin Locations** tab → **+ New Bin**.
2. Enter the warehouse **Location ID**, and the **Zone / Aisle / Rack / Bin** codes.
3. The system generates a bin code automatically (e.g. `A-01-02-03`).

---

### 6. Sell-In Orders (Purchasing from Distributors)

**Who:** Purchasing Officer / Branch Manager  
**Where:** `http://localhost:3000/sellin`

1. Click **+ New Order**.
2. Enter the **Supplier Party ID**, **Delivery Location ID**, and **Requested Delivery Date**.
3. Add line items: Product ID, quantity, and unit cost for each.
4. Click **Create Order** (status: PENDING).
5. Finance or management confirms: click **Confirm** → status changes to CONFIRMED.
6. When goods arrive at the warehouse, the system's Kafka consumer (`SALES_SELLIN_DELIVERED`) automatically creates a goods receipt in inventory.

---

### 7. Product Catalog

**Who:** Product Manager / Admin  
**Where:** `http://localhost:3000/catalog`

- Use the **search bar** to find products by name.
- Click **+ Add Product** to register a new SKU with barcode, category, unit price, and tax rate.
- The barcode field enables POS scan lookup — cashiers can scan a barcode to autofill product details.

---

### 8. Party / Dealer Management

**Who:** Channel Administrator / Finance  
**Where:** `http://localhost:3000/parties`

- View and filter parties by type: **Dealer**, **Distributor**, **Employee**, or **Customer**.
- Click **+ Add Party** to onboard a new dealer or distributor with contact details and tax ID.
- Newly onboarded dealers automatically receive a default commission agreement (via the party onboarded Kafka event).

---

### 9. Commission Rules & Agreements

**Who:** Finance Manager / Commercial Director  
**Where:** `http://localhost:3000/commission/rules`

Two tabs:

**Agreements** — Shows all active commission agreements between the telco and its dealers. Each agreement is bound to a party, a channel (Retail, Online, etc.), and a product category.

**Commission Rules** — Shows the tier rules within each agreement:
- **FLAT** — fixed amount per unit sold.
- **PERCENTAGE** — percentage of transaction value.
- **TIERED** — escalating rate based on volume thresholds (tier_min_qty to tier_max_qty).

> Rules are read-only in the UI. To create or modify rules, use the commission-rules-service API directly (POST `/api/v1/agreementManagement/commissionRule`).

---

### 10. Commission Statements

**Who:** Finance Officer / Dealer  
**Where:** `http://localhost:3000/commission/statements`

- Shows monthly commission statements per dealer.
- **DRAFT** → commission calculated but not yet approved.
- Click **Confirm** to lock the statement → status becomes **CONFIRMED**.
- Confirmed statements trigger the payout pipeline automatically.

---

### 11. Payouts

**Who:** Finance Officer  
**Where:** `http://localhost:3000/payouts`

- Shows all pending and completed payout requests.
- The **Pending** total is shown at the top of the page.
- Click **Process** to initiate payment for a pending request.
- Once processed, the status changes to **COMPLETED** and a notification is sent to the dealer.

---

### 12. Performance Dashboard

**Who:** Branch Manager / Regional Director  
**Where:** `http://localhost:3000/performance`

- Displays KPI cards for the current month: sell-out units, sell-out revenue, etc.
- Green border = target achieved; red border = target missed.
- The bar chart shows target vs actual side by side.
- Period defaults to the current month (YYYY-MM format).

---

### 13. Audit Log

**Who:** Compliance Officer / Senior Manager  
**Where:** `http://localhost:3000/audit`

- View an immutable log of all business events across all services.
- Filter by **Service**, **Entity Type**, and **From Date**.
- Click the **▼** button on any row to expand the full JSON event payload.
- Audit logs are append-only — no record can be edited or deleted.

---

## Technical Operations

### Prerequisites

| Tool | Version |
|---|---|
| Docker | 24+ |
| Docker Compose | v2 |
| Python | 3.12+ |
| Node.js | 20+ |
| Make | GNU 4+ |

---

### Starting the System

```bash
# 1. Start infrastructure (Postgres, Kafka, Redis, Keycloak)
make infra-up

# 2. Create Kafka topics (done automatically by infra-up)
make topics

# 3. Start all services + frontend
make up

# 4. Run database migrations
make migrate

# 5. Load seed data (parties, locations, commission rules)
make seed
```

**Service startup order** (enforced by Docker Compose `depends_on`):
```
postgres → kafka → [all services] → frontend
```

---

### Service Port Map

| Service | Port | Database |
|---|---|---|
| inventory-service | 8001 | `postgres:5432/inventory` |
| party-service | 8002 | `postgres:5432/party` |
| sell-out-service | 8003 | `postgres:5432/sellout` |
| sell-in-service | 8004 | `postgres:5432/sellin` |
| stock-query-service | 8005 | Redis |
| performance-service | 8006 | `postgres:5432/performance` |
| commission-rules-service | 8007 | `postgres:5432/commission_rules` |
| commission-calculation-service | 8008 | `postgres:5432/commission_calc` |
| payout-service | 8009 | `postgres:5432/payout` |
| notification-service | 8010 | — |
| audit-service | 8011 | `postgres:5432/audit` |
| warehouse-service | 8012 | `postgres:5432/warehouse` |
| product-catalog-service | 8013 | `postgres:5432/product_catalog` |
| Frontend | 3000 | — |
| PostgreSQL | 5432 | shared instance |
| Kafka | 9092 | — |
| Kafka UI | 8090 | — |
| Redis | 6379 | — |
| Keycloak | 8080 | — |

---

### Running Tests

```bash
# All unit tests (all 13 services)
make test

# Single service
make test-sell-out-service
make test-warehouse-service
make test-inventory-service

# Commission rule evaluator (deterministic, fast)
make test-rules

# Integration tests (requires infra running)
make test-integration
```

---

### Database Migrations

```bash
# Migrate all services
make migrate

# Migrate a single service
make migrate-inventory-service
make migrate-warehouse-service
make migrate-sell-out-service

# Roll back (via alembic directly)
docker compose run --rm inventory-service alembic downgrade -1
```

---

### Kafka Topics Reference

| Topic | Publisher | Consumers |
|---|---|---|
| `telco.sales.sellout.completed` | sell-out-service | commission-calc, inventory, performance, audit |
| `telco.sales.return.processed` | sell-out-service | inventory, audit |
| `telco.sales.sellin.delivered` | sell-in-service | warehouse (auto-GRN), inventory, audit |
| `telco.inventory.stock.transferred` | inventory-service | audit |
| `telco.inventory.stock.received` | inventory-service | audit |
| `telco.warehouse.picklist.created` | warehouse-service | audit |
| `telco.warehouse.picklist.completed` | warehouse-service | audit |
| `telco.warehouse.dispatch.created` | warehouse-service | audit, notification |
| `telco.commission.event.calculated` | commission-calc | payout, audit |
| `telco.commission.statement.confirmed` | commission-calc | payout |
| `telco.payout.request.created` | payout-service | notification |
| `telco.payout.request.completed` | payout-service | notification |
| `telco.party.dealer.onboarded` | party-service | commission-rules, notification |

Dead letter queues follow the pattern `telco.dlq.{service}.{topic}` with a 3-retry policy before routing.

---

### Logs

```bash
# All services
make logs

# Single service
make logs-sell-out-service
make logs-warehouse-service
make logs-commission-calculation-service

# Follow with timestamps
docker compose logs -f --timestamps sell-out-service
```

---

### Health Checks

Every service exposes `GET /health`. Check all at once:

```bash
for port in 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011 8012 8013; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)
  echo "Port $port: $status"
done
```

Expected: all `200`.

---

### OpenAPI Documentation

Every service serves interactive Swagger UI at `/docs`:

```
http://localhost:8001/docs   # inventory-service
http://localhost:8003/docs   # sell-out-service
http://localhost:8012/docs   # warehouse-service
http://localhost:8013/docs   # product-catalog-service
# etc.
```

Generate static OpenAPI JSON files:

```bash
make generate-openapi
# outputs to: docs/api/openapi/{service}.json
```

---

### Common Troubleshooting

#### A service fails to start

```bash
# Check logs
make logs-{service-name}

# Most common cause: database not ready
docker compose restart {service-name}

# If migration hasn't run
make migrate-{service-name}
```

#### Kafka consumer is stuck / high lag

```bash
# View lag in Kafka UI at http://localhost:8090
# Or via CLI:
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --describe --all-groups

# Reset a consumer group offset (use with caution)
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --group {service}-group \
  --topic telco.sales.sellout.completed \
  --reset-offsets --to-latest --execute
```

#### Commission not calculated after a sale

1. Check that `telco.sales.sellout.completed` was published (Kafka UI → topic browser).
2. Check `commission-calculation-service` logs for processing errors.
3. Check the `processed_event_ids` table — if the event ID is already there, it was processed (idempotency guard); look for the commission_event row instead.
4. Check that an active agreement exists for the dealer and product category.

#### Stock not deducted after sale

1. Confirm `telco.sales.sellout.completed` was consumed by `inventory-service` (check consumer group lag).
2. Check `inventory-service` logs for the sell-out consumer.
3. Verify a `ProductInventory` record exists for the product at the dealer's location.

#### 422 on sale submission (stock validation)

1. Open `http://localhost:8001/docs` → `GET /api/v1/inventory/stockAvailability`.
2. Query with the product and location IDs.
3. If `net_quantity` is 0 or negative, stock must be replenished before the sale can proceed.

#### Dead-letter queue messages

```bash
# List DLQ topics
docker compose exec kafka kafka-topics.sh \
  --bootstrap-server kafka:9092 --list | grep dlq

# Read failed messages
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 \
  --topic telco.dlq.commission-calculation-service.telco.sales.sellout.completed \
  --from-beginning --max-messages 10
```

---

### Code Quality

```bash
# Lint all services
make lint

# Auto-format all services
make fmt

# Type-check all services
make typecheck

# Frontend
cd frontend && npm run build   # TypeScript check + production bundle
```

---

### Seed Data Reference

After `make seed`, the following demo data exists:

| Entity | ID | Description |
|---|---|---|
| Party (Dealer) | `00000000-0000-0000-0000-000000000001` | Demo dealer used by frontend |
| Location (Warehouse) | _(seed.sql)_ | Main warehouse |
| Location (Own Shop) | _(seed.sql)_ | Demo retail shop |
| Commission Agreement | _(seed.sql)_ | Default PERCENTAGE rule for demo dealer |

---

### Production Deployment Notes

- Use **CloudNativePG** for PostgreSQL HA (1 primary + 2 read replicas per domain cluster).
- Use **Strimzi** for Kafka (3 brokers, replication factor 3, min.insync.replicas 2).
- All `DATABASE_URL` and `KAFKA_BOOTSTRAP_SERVERS` values come from Kubernetes Secrets — never hardcode.
- Row-Level Security is defined per service's Alembic migrations; ensure `SET app.tenant_id = '{tenant}'` is issued per request via the `TenantMixin` middleware in `telco-common`.
- Keycloak realm configuration is in `infrastructure/keycloak/` — import this before first use in any environment.
- Kong declarative config is in `infrastructure/kong/` — apply with `deck sync`.

See `infrastructure/kubernetes/` for full K8s manifests and `infrastructure/terraform/` for cloud IaC.
