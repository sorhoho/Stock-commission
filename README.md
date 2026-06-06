# Telco Distribution & Commission System

Production-ready, TMForum-compliant microservices platform covering the full end-to-end scope of a telco distribution and commission management system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Kong API Gateway                            │
│          (JWT validation · Rate limiting · Routing)             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐
│  Inventory   │  │  Sales Channel   │  │ Commission Domain  │
│  Domain      │  │  Domain          │  │                    │
│              │  │                  │  │  commission-rules  │
│  inventory   │  │  sell-out-svc    │  │  commission-calc   │
│  warehouse   │  │  sell-in-svc     │  │  payout-service    │
│  product-cat │  │  stock-query     │  │  incentive-svc     │
│  party-svc   │  │                  │  │                    │
└──────┬───────┘  └────────┬─────────┘  └────────┬───────────┘
       │                   │                     │
       └───────────────────┴─────────────────────┘
                           │ Apache Kafka
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌────────────────────┐   ┌─────────────────────┐
   │  Performance &     │   │  Cross-cutting       │
   │  Reporting Domain  │   │  Services            │
   │                    │   │                      │
   │  performance-svc   │   │  audit-service       │
   │  reporting-svc     │   │  notification-svc    │
   └────────────────────┘   └─────────────────────┘
```

## Domain Coverage & TMForum Mapping

| Domain | Service | TMForum API |
|--------|---------|-------------|
| Distribution & Inventory | `inventory-service` | TMF637 Product Inventory + TMF639 Resource Inventory |
| Distribution & Inventory | `warehouse-service` | WMS — bin locations, pick lists, packing, dispatch |
| Distribution & Inventory | `product-catalog-service` | TMF620 Product Catalog |
| Distribution & Inventory | `stock-query-service` | TMF637 (CQRS read) |
| Support Sale Process | `sell-out-service` | TMF699 Sales Management + POS sessions + returns |
| Support Sale Process | `sell-in-service` | TMF622 Product Ordering |
| Sales Performance | `performance-service` | TMF628 Performance Management |
| Commission/Incentive | `commission-rules-service` | TMF651 Agreement Management |
| Commission/Incentive | `commission-calculation-service` | TMF666 Account & Finance |
| Commission/Incentive | `payout-service` | TMF666 Account & Finance |
| Cross-cutting | `party-service` | TMF632 Party Management |
| Cross-cutting | `audit-service` | Append-only audit log |
| Cross-cutting | `notification-service` | Event-driven notifications |

## Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- Python 3.12+ (for running services locally)
- Node.js 20+ (for frontend)

### 1. Start Infrastructure

```bash
make infra-up
```

This starts: PostgreSQL (single shared instance, per-service databases), Kafka + Zookeeper, Redis, Keycloak (with demo realm).

### 2. Start All Services

```bash
make up
```

### 3. Run Database Migrations

```bash
make migrate
```

### 4. Seed Demo Data

```bash
make seed
```

### 5. Access the System

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Keycloak Admin | http://localhost:8080/admin (admin/admin) |
| Kafka UI | http://localhost:8090 |
| Grafana | http://localhost:3001 (admin/admin) |
| Prometheus | http://localhost:9090 |
| inventory-service | http://localhost:8001/docs |
| party-service | http://localhost:8002/docs |
| sell-out-service | http://localhost:8003/docs |
| sell-in-service | http://localhost:8004/docs |
| stock-query-service | http://localhost:8005/docs |
| performance-service | http://localhost:8006/docs |
| commission-rules-service | http://localhost:8007/docs |
| commission-calculation-service | http://localhost:8008/docs |
| payout-service | http://localhost:8009/docs |
| warehouse-service | http://localhost:8012/docs |
| product-catalog-service | http://localhost:8013/docs |

### Demo Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin@telco.local | admin123 |
| Dealer | dealer1@telco.local | dealer123 |
| Finance | finance@telco.local | finance123 |

## Key Event Flow: Sell-Out → Commission

```
1. POST /api/v1/salesManagement/saleTransaction
   ├─► validates stock via stock-query-service (422 if insufficient)
   └─► sell-out-service persists transaction (with optional pos_session_id)
   └─► publishes: telco.sales.sellout.completed

2. commission-calculation-service (Kafka consumer)
   └─► fetches commission agreement from commission-rules-service
   └─► evaluates CommissionRule (find_applicable_rule)
   └─► calculates commission (calculate_commission)
   └─► persists CommissionEvent (idempotency-safe)
   └─► publishes: telco.commission.event.calculated
   └─► upserts CommissionStatement (monthly running total)

3. inventory-service (Kafka consumer)
   └─► decrements stock-on-hand at dealer location

4. performance-service (Kafka consumer)
   └─► records MONTHLY_SELL_OUT_UNITS and MONTHLY_SELL_OUT_REVENUE measurements
   └─► checks if PerformanceTarget is met

5. audit-service (Kafka consumer)
   └─► persists all events to append-only audit_log table

6. POST /api/v1/accountManagement/commissionStatement/{id}/confirm
   └─► publishes: telco.commission.statement.confirmed

7. payout-service (Kafka consumer)
   └─► creates PayoutRequest (PENDING)
   └─► publishes: telco.payout.request.created

8. POST /api/v1/payout/payoutRequest/{id}/process
   └─► calls payment gateway (mocked)
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
   └─► create packing slip from completed pick list

6. POST /api/v1/warehouseManagement/packingSlip/{id}/dispatch
   └─► record shipping carrier + tracking number
   └─► publishes: telco.warehouse.dispatch.created

7. SALES_SELLIN_DELIVERED (Kafka consumer)
   └─► auto-creates goods receipt in inventory-service for delivered sell-in items
```

## Retail POS Flow

```
1. POST /api/v1/salesManagement/posSession
   └─► open shift: terminal_id, opened_by, opening_cash

2. POST /api/v1/salesManagement/saleTransaction (with pos_session_id)
   └─► pre-sale stock check → 422 if stock insufficient
   └─► records payment_method + payment_reference

3. POST /api/v1/salesManagement/returnTransaction
   └─► initiate return against an original transaction

4. POST /api/v1/salesManagement/returnTransaction/{id}/approve
   └─► approve return → publishes: telco.sales.return.processed

5. POST /api/v1/salesManagement/posSession/{id}/close
   └─► close shift: closing_cash, reconcile total_transactions / total_amount
```

## Project Structure

```
Stock-commission/
├── services/
│   ├── inventory-service/        # TMF637 + TMF639 — stock, transfers, GRN, serial tracking
│   ├── warehouse-service/        # WMS — bin locations, pick lists, packing, dispatch
│   ├── product-catalog-service/  # TMF620 — product CRUD, barcode POS lookup
│   ├── party-service/            # TMF632 — dealers, distributors
│   ├── sell-out-service/         # TMF699 — POS transactions, sessions, returns
│   ├── sell-in-service/          # TMF622 — distributor orders
│   ├── stock-query-service/      # CQRS read model (Redis)
│   ├── performance-service/      # TMF628 — KPI targets & measurements
│   ├── commission-rules-service/ # TMF651 — agreement specs & rules
│   ├── commission-calculation-service/ # TMF666 — calculation engine
│   ├── payout-service/           # TMF666 — payout scheduling
│   ├── notification-service/     # Event-driven notifications
│   └── audit-service/            # Append-only audit log
│
├── shared/
│   └── telco-common/             # Shared: CloudEvents, JWT, Kafka, SQLAlchemy mixins
│
├── infrastructure/
│   ├── kubernetes/               # K8s manifests (Kustomize)
│   ├── kong/                     # API Gateway config
│   ├── keycloak/                 # Realm export
│   ├── terraform/                # Cloud infrastructure IaC
│   └── observability/            # Prometheus, Grafana, Tempo, Loki
│
├── frontend/                     # React 18 + TypeScript + Vite
├── scripts/                      # Kafka topics, seed data, DB init
├── docker-compose.yml            # Full local stack
├── docker-compose.infra.yml      # Infrastructure only
└── Makefile                      # Developer commands
```

## Running Tests

```bash
# All unit tests
make test

# Specific service
make test-sell-out-service
make test-warehouse-service

# Commission rule evaluator (pure function, no dependencies)
make test-rules

# Integration tests (requires infra running)
make test-integration
```

## Development

```bash
# Code quality
make lint
make fmt
make typecheck

# Generate OpenAPI specs
make generate-openapi

# Tail logs
make logs
make logs-warehouse-service
make logs-sell-out-service
```

## Kafka Topics

| Topic | Publisher | Consumers |
|-------|-----------|-----------|
| `telco.sales.sellout.completed` | sell-out-service | commission-calc, inventory, performance, audit |
| `telco.sales.return.processed` | sell-out-service | inventory, audit |
| `telco.inventory.stock.transferred` | inventory-service | audit |
| `telco.inventory.stock.received` | inventory-service | audit |
| `telco.warehouse.picklist.completed` | warehouse-service | audit |
| `telco.warehouse.dispatch.created` | warehouse-service | audit, notification |
| `telco.commission.event.calculated` | commission-calc | payout, audit |
| `telco.commission.statement.confirmed` | commission-calc | payout |
| `telco.payout.request.completed` | payout-service | notification |
| `telco.sales.sellin.delivered` | sell-in-service | warehouse (auto-GRN) |

## Production Deployment

See `infrastructure/kubernetes/` for Kubernetes manifests and `infrastructure/terraform/` for cloud IaC.

**Key production requirements:**
- CloudNativePG operator for PostgreSQL HA (1 primary + 2 replicas per domain)
- Strimzi operator for Kafka (3-broker cluster, RF=3, min.insync.replicas=2)
- Keycloak with external DB (not dev-mem)
- Secrets in Kubernetes Secrets or HashiCorp Vault
- Network policies for namespace isolation
- Istio service mesh for mTLS between services

## Architecture Decision Records

- [ADR-001: Service Decomposition](docs/architecture/ADR-001-service-decomposition.md)
- [ADR-002: Event Schema](docs/architecture/ADR-002-event-schema.md)
- [ADR-003: Multi-Tenant Strategy](docs/architecture/ADR-003-multi-tenant-strategy.md)
