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
│  party-svc   │  │  sell-in-svc     │  │  payout-service    │
│  stock-query │  │                  │  │  incentive-svc     │
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
| Distribution & Inventory | `inventory-service` | TMF637 Product Inventory |
| Distribution & Inventory | `stock-query-service` | TMF637 (CQRS read) |
| Support Sale Process | `sell-out-service` | TMF699 Sales Management |
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

This starts: PostgreSQL (per-service DBs), Kafka + Zookeeper, Redis, Keycloak (with demo realm).

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

### Demo Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin@telco.local | admin123 |
| Dealer | dealer1@telco.local | dealer123 |
| Finance | finance@telco.local | finance123 |

## Key Event Flow: Sell-Out → Commission

```
1. POST /api/v1/salesManagement/saleTransaction
   └─► sell-out-service persists transaction
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

## Project Structure

```
Stock-commission/
├── services/
│   ├── inventory-service/        # TMF637 — stock-on-hand, transfers
│   ├── party-service/            # TMF632 — dealers, distributors
│   ├── sell-out-service/         # TMF699 — POS transactions
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
├── scripts/                      # Kafka topics, seed data
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
make logs-commission-calculation-service
```

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
