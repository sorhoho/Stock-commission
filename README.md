# True Corporation — Distribution & Commission System

Production-ready, TMForum-compliant microservices platform for True Corporation (Thailand), covering end-to-end telco distribution, retail POS, warehouse operations, and dealer commission. All monetary values in THB (VAT 7%); demo data covers TrueMove H SIMs and refill cards, TrueVisions set-top boxes, TrueID TV boxes, True Gigatex fiber CPE, True IoT/CCTV, and flagship handsets. 573 unit tests across 13 services.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      Kong API Gateway                            │
│           (JWT validation · Rate limiting · Routing)             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
      ┌──────────────────────┼────────────────────┐
      ▼                      ▼                    ▼
┌───────────────┐  ┌──────────────────┐  ┌─────────────────────┐
│  Inventory    │  │  Sales Channel   │  │  Commission Domain  │
│  Domain       │  │  Domain          │  │                     │
│               │  │                  │  │  commission-rules   │
│  inventory    │  │  sell-out-svc    │  │  commission-calc    │
│  warehouse    │  │  sell-in-svc     │  │  payout-service     │
│  product-cat  │  │  stock-query     │  │                     │
│  party-svc    │  │                  │  │                     │
└──────┬────────┘  └───────┬──────────┘  └──────────┬──────────┘
       │                   │                        │
       └───────────────────┴────────────────────────┘
                           │ Apache Kafka (19 topics)
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌────────────────────┐   ┌──────────────────────┐
   │  Performance &     │   │  Cross-cutting        │
   │  Analytics Domain  │   │  Services             │
   │                    │   │                       │
   │  performance-svc   │   │  audit-service        │
   │                    │   │  notification-svc     │
   └────────────────────┘   └──────────────────────┘
```

## Services

| Domain | Service | Port | TMForum API | Tests |
|--------|---------|------|-------------|-------|
| Inventory | `inventory-service` | 8001 | TMF637 Product Inventory + TMF639 Resource Inventory | 90 |
| Inventory | `warehouse-service` | 8012 | WMS — bin locations, pick lists, packing, dispatch | 20 |
| Inventory | `product-catalog-service` | 8013 | TMF620 Product Catalog | — |
| Inventory | `stock-query-service` | 8005 | TMF637 (CQRS read, Redis-backed) | 54 |
| Sales | `sell-out-service` | 8003 | TMF699 Sales Management + POS sessions + returns | 71 |
| Sales | `sell-in-service` | 8004 | TMF622 Product Ordering | 62 |
| Platform | `party-service` | 8002 | TMF632 Party Management | 69 |
| Performance | `performance-service` | 8006 | TMF628 Performance Management | 60 |
| Commission | `commission-rules-service` | 8007 | TMF651 Agreement Management | 47 |
| Commission | `commission-calculation-service` | 8008 | TMF666 Account & Finance | 88 |
| Commission | `payout-service` | 8009 | TMF666 Account & Finance | 43 |
| Platform | `notification-service` | 8010 | Event-driven (multi-topic consumer) | 45 |
| Platform | `audit-service` | 8011 | Append-only audit log | 24 |

**Total: 573 unit tests across 46 test files.**

## Quick Start

### Prerequisites
- Docker 24+ with Docker Compose v2
- Python 3.12+ (for local service development)
- Node.js 20+ (for frontend)

### 1. Start Infrastructure

```bash
make infra-up
```

Starts: PostgreSQL 16 (single shared instance, 11 logical databases), Kafka + Zookeeper, Redis, Keycloak.

### 2. Create Kafka Topics

```bash
make topics
```

### 3. Start All Services

```bash
make up
```

### 4. Run Migrations

```bash
make migrate
```

### 5. Seed Demo Data

```bash
make seed
```

### 6. Access the System

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| Keycloak Admin | http://localhost:8080/admin (admin / admin) |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin / admin) |
| inventory-service API docs | http://localhost:8001/docs |
| party-service API docs | http://localhost:8002/docs |
| sell-out-service API docs | http://localhost:8003/docs |
| sell-in-service API docs | http://localhost:8004/docs |
| stock-query-service API docs | http://localhost:8005/docs |
| performance-service API docs | http://localhost:8006/docs |
| commission-rules-service API docs | http://localhost:8007/docs |
| commission-calculation-service API docs | http://localhost:8008/docs |
| payout-service API docs | http://localhost:8009/docs |
| notification-service API docs | http://localhost:8010/docs |
| audit-service API docs | http://localhost:8011/docs |
| warehouse-service API docs | http://localhost:8012/docs |
| product-catalog-service API docs | http://localhost:8013/docs |

### Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin@telco.local | admin123 |
| Dealer | dealer1@telco.local | dealer123 |
| Finance | finance@telco.local | finance123 |

## Key Event Flow: Sell-Out → Commission

```
1. POST /api/v1/salesManagement/saleTransaction
   ├─► validates stock via stock-query-service (422 if insufficient)
   └─► persists transaction (with optional pos_session_id, payment_method)
   └─► publishes: telco.sales.sellout.completed

2. commission-calculation-service (Kafka consumer)
   └─► fetches active agreement from commission-rules-service
   └─► evaluates CommissionRule (tiered / flat / percentage)
   └─► persists CommissionEvent (idempotency key: transactionId + agreementId)
   └─► upserts monthly CommissionStatement
   └─► publishes: telco.commission.event.calculated

3. inventory-service (Kafka consumer)
   └─► decrements stock-on-hand at dealer location

4. performance-service (Kafka consumer)
   └─► records MONTHLY_SELL_OUT_UNITS and MONTHLY_SELL_OUT_REVENUE
   └─► evaluates PerformanceTarget achievement

5. audit-service (Kafka consumer)
   └─► appends all events to audit_log (immutable)

6. POST /api/v1/accountManagement/commissionStatement/{id}/confirm
   └─► publishes: telco.commission.statement.confirmed

7. payout-service (Kafka consumer)
   └─► creates PayoutRequest (PENDING)
   └─► publishes: telco.payout.request.created

8. POST /api/v1/payout/payoutRequest/{id}/process
   └─► calls payment gateway (mocked in dev)
   └─► publishes: telco.payout.request.completed

9. notification-service (Kafka consumer)
   └─► sends payout confirmation to dealer
```

## Warehouse Management Flow

```
1. POST /api/v1/warehouseManagement/binLocation
   └─► register zone / aisle / rack / bin within a warehouse location

2. POST /api/v1/warehouseManagement/pickList
   └─► create pick list for a sell-out or replenishment order

3. POST /api/v1/warehouseManagement/pickList/{id}/assign
   └─► assign pick list to a warehouse worker

4. POST /api/v1/warehouseManagement/pickList/{id}/complete
   └─► confirm picked quantities per item (supports short-picks)
   └─► publishes: telco.warehouse.picklist.completed

5. POST /api/v1/warehouseManagement/packingSlip
   └─► create packing slip from a completed pick list

6. POST /api/v1/warehouseManagement/packingSlip/{id}/dispatch
   └─► record shipping carrier + tracking number
   └─► publishes: telco.warehouse.dispatch.created

7. telco.sales.sellin.delivered (Kafka consumer in warehouse-service)
   └─► auto-creates goods receipt in inventory-service for each delivered item
```

## Retail POS Flow

```
1. POST /api/v1/salesManagement/posSession
   └─► open shift: terminal_id, opened_by, opening_cash

2. POST /api/v1/salesManagement/saleTransaction  (with pos_session_id)
   └─► pre-sale stock check → 422 if stock insufficient
   └─► records payment_method (CASH | CARD | MOBILE_MONEY | CREDIT)
   └─► records payment_reference (card auth code, mobile money ref, etc.)

3. POST /api/v1/salesManagement/returnTransaction
   └─► initiate return against an original transaction

4. POST /api/v1/salesManagement/returnTransaction/{id}/approve
   └─► approve return → publishes: telco.sales.return.processed

5. POST /api/v1/salesManagement/posSession/{id}/close
   └─► close shift: closing_cash, reconcile total_transactions / total_amount
```

## Inventory Capabilities

`inventory-service` implements both TMF637 and TMF639:

| Capability | Endpoint prefix |
|-----------|-----------------|
| Product inventory (SOH) | `/api/v1/inventory/productInventory` |
| Location management | `/api/v1/inventory/location` |
| Stock transfers | `/api/v1/inventory/stockTransfer` |
| Stock adjustments | `/api/v1/inventory/stockAdjustment` |
| Stock reservations | `/api/v1/inventory/stockReservation` |
| Goods receipts (GRN) | `/api/v1/inventory/goodsReceipt` |
| Stock reconciliation | `/api/v1/inventory/stockReconciliation` |
| Resource inventory (IMEI/SN) | `/api/v1/resourceInventory/resource` |

Location types: `WAREHOUSE`, `DISTRIBUTION_CENTER`, `DEALER_OUTLET`, `OWN_SHOP`.

## Kafka Topics

| Topic | Publisher | Consumers |
|-------|-----------|-----------|
| `telco.sales.sellout.completed` | sell-out-service | commission-calc, inventory, performance, audit |
| `telco.sales.sellout.reversed` | sell-out-service | inventory, audit |
| `telco.sales.return.processed` | sell-out-service | inventory, audit |
| `telco.sales.sellin.ordered` | sell-in-service | audit |
| `telco.sales.sellin.delivered` | sell-in-service | warehouse (auto-GRN), audit |
| `telco.inventory.stock.transferred` | inventory-service | audit |
| `telco.inventory.stock.adjusted` | inventory-service | audit |
| `telco.inventory.stock.reserved` | inventory-service | audit |
| `telco.inventory.stock.received` | inventory-service | audit |
| `telco.inventory.resource.allocated` | inventory-service | audit |
| `telco.warehouse.picklist.created` | warehouse-service | audit |
| `telco.warehouse.picklist.completed` | warehouse-service | audit |
| `telco.warehouse.dispatch.created` | warehouse-service | audit, notification |
| `telco.commission.event.calculated` | commission-calc | payout, audit |
| `telco.commission.statement.confirmed` | commission-calc | payout |
| `telco.payout.request.created` | payout-service | notification, audit |
| `telco.payout.request.completed` | payout-service | notification |
| `telco.party.dealer.onboarded` | party-service | commission-rules (auto-bind), notification |
| `telco.performance.measurement.recorded` | performance-service | audit |

All events use CloudEvents 1.0 envelope. Schema definitions in `shared/telco-common/telco_common/events/schemas/`.

## Frontend

React 18 + TypeScript + Vite + RTK Query. Ten feature modules covering all service domains:

| Module | Covers |
|--------|--------|
| POS / Sell-Out | Sale entry, line items, commission-eligible flag |
| POS Sessions | Open / close shift, cash reconciliation |
| Returns | Initiate return, approve / reject, link to original transaction |
| Inventory | SOH table, stock transfer form |
| Warehouse | Pick lists (create / assign / complete), packing slips (create / dispatch), bin locations |
| Sell-In | Distributor orders (create / confirm / mark delivered) |
| Product Catalog | Product CRUD, barcode lookup |
| Parties / Dealers | Party table, type filter |
| Commission Rules | Agreements and tiered rule viewer |
| Commission Statements | Monthly statement table, Confirm action |
| Payouts | Payout request list, Process action |
| Performance | KPI card grid + target vs. actual bar chart |
| Audit Log | Filterable log table with expandable JSON payload |

## Project Structure

```
Stock-commission/
├── services/
│   ├── inventory-service/        # TMF637 + TMF639 — SOH, transfers, GRN, reconciliation, IMEI
│   ├── warehouse-service/        # WMS — bin locations, pick lists, packing, dispatch
│   ├── product-catalog-service/  # TMF620 — product CRUD, barcode POS lookup
│   ├── party-service/            # TMF632 — dealers, distributors, characteristics
│   ├── sell-out-service/         # TMF699 — POS transactions, sessions, returns
│   ├── sell-in-service/          # TMF622 — distributor orders
│   ├── stock-query-service/      # CQRS read model (Redis-backed)
│   ├── performance-service/      # TMF628 — KPI specs, targets, measurements
│   ├── commission-rules-service/ # TMF651 — agreement specs, agreements, rules
│   ├── commission-calculation-service/  # TMF666 — calculation engine, statements
│   ├── payout-service/           # TMF666 — payout request lifecycle
│   ├── notification-service/     # Event-driven notifications (multi-topic consumer)
│   └── audit-service/            # Append-only audit log (all Kafka events)
│
├── shared/
│   └── telco-common/             # Shared pip package:
│                                 #   CloudEvents envelope + all event schemas
│                                 #   JWT bearer + RBAC scopes
│                                 #   SQLAlchemy base, UUIDMixin, TenantMixin
│                                 #   Kafka producer/consumer factories
│                                 #   Tenant + correlation middleware
│
├── infrastructure/
│   ├── kubernetes/base/          # Deployments for all 13 services + infra
│   ├── kubernetes/overlays/      # dev / staging / production overlays (Kustomize)
│   ├── kong/                     # Declarative Kong gateway config
│   ├── keycloak/                 # Realm export with demo roles
│   ├── terraform/                # Cloud IaC module skeletons (EKS, MSK, RDS)
│   └── observability/            # Prometheus rules, Tempo, Loki config
│
├── frontend/                     # React 18 + TypeScript + Vite + RTK Query
├── scripts/
│   ├── init-databases.sql        # Creates all 11 databases on shared PostgreSQL
│   ├── seed-data/seed.sql        # Demo parties, locations, agreements
│   ├── kafka/create-topics.sh    # All 19 Kafka topics
│   └── e2e-test.sh / e2e-http-test.sh
│
├── docs/
│   ├── SYSTEM-OVERVIEW.md
│   ├── BUSINESS-GUIDE.md
│   ├── DESIGN-PRINCIPLES.md
│   ├── OPERATIONS-GUIDE.md
│   ├── OPERATIONS-MANUAL.md
│   └── architecture/
│       ├── ADR-001-service-decomposition.md
│       ├── ADR-002-event-schema.md
│       └── ADR-003-multi-tenant-strategy.md
│
├── docker-compose.yml            # Full local stack (23 containers)
├── docker-compose.infra.yml      # Infrastructure only
└── Makefile                      # Developer commands (see below)
```

## Developer Commands

```bash
# Infrastructure
make infra-up           # Start PostgreSQL, Kafka, Redis, Keycloak
make infra-down         # Stop infrastructure
make topics             # Create all 19 Kafka topics

# Services
make up                 # Start all 13 services
make down               # Stop all services
make build              # Build all Docker images
make logs               # Tail all service logs
make logs-<service>     # Tail a specific service (e.g. make logs-sell-out-service)
make ps                 # Show running containers

# Database
make migrate            # Run Alembic migrations for all services
make migrate-<service>  # Run migrations for one service
make seed               # Load seed data

# Testing
make test               # Run all 573 unit tests
make test-<service>     # Run tests for one service
make test-rules         # Commission rule evaluator only (pure function, fast)
make e2e                # End-to-end Kafka flow test
make e2e-http           # End-to-end HTTP flow test
make test-integration   # Integration tests (requires infra running)

# Code quality
make lint               # ESLint + Ruff + mypy
make fmt                # Black + isort + prettier
make typecheck          # tsc + mypy
make generate-openapi   # Export OpenAPI specs for all services

# Frontend
make frontend-install   # pnpm install
make frontend-dev       # Vite dev server (port 3000)
make frontend-build     # Production build
```

## Multi-Tenancy

- `tenant_id` extracted from Keycloak JWT by Kong, forwarded to every service via `X-Tenant-ID` header
- PostgreSQL Row-Level Security on every table using `tenant_id` column
- Services never trust client-supplied `tenant_id` — always derived from JWT context
- Per-tenant rate limiting in Kong (Redis-backed)

## Production Deployment

Kubernetes manifests in `infrastructure/kubernetes/` (Kustomize overlays for dev / staging / production).

**Key requirements:**
- CloudNativePG operator — PostgreSQL HA (1 primary + 2 read replicas per domain cluster)
- Strimzi operator — Kafka 3-broker cluster (RF=3, min.insync.replicas=2)
- Keycloak with external PostgreSQL (not dev in-memory mode)
- Secrets in Kubernetes Secrets or HashiCorp Vault
- Istio service mesh for mTLS between services
- HPA on CPU >70% + Kafka consumer lag metric

## Documentation

- [System Overview](docs/SYSTEM-OVERVIEW.md) — architecture and data models
- [Business Guide](docs/BUSINESS-GUIDE.md) — workflows for business users
- [Operations Manual](docs/OPERATIONS-MANUAL.md) — daily ops and runbooks
- [Operations Guide](docs/OPERATIONS-GUIDE.md) — infrastructure and deployment
- [Design Principles](docs/DESIGN-PRINCIPLES.md) — engineering decisions
- [ADR-001: Service Decomposition](docs/architecture/ADR-001-service-decomposition.md)
- [ADR-002: Event Schema](docs/architecture/ADR-002-event-schema.md)
- [ADR-003: Multi-Tenant Strategy](docs/architecture/ADR-003-multi-tenant-strategy.md)
