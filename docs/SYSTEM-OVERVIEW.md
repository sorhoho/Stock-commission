# Telco Distribution & Commission System — 101 Guide

> **Who this is for:** Anyone joining the project — whether you are a business analyst, product manager, new engineer, or stakeholder who wants to understand what the system does and how it works.

---

## Part 1 — Business 101

### What Problem Does This System Solve?

A telecommunications company sells products (SIM cards, devices, accessories) through a network of **dealers** and **distributors**, not directly to customers. This creates three unavoidable operational headaches:

1. **Stock chaos** — Nobody knows exactly how much inventory sits at each warehouse, distribution centre, or dealer outlet. When a dealer sells a SIM card, the stock count somewhere needs to go down.

2. **Commission disputes** — Dealers earn a commission on every sale they make. Calculating that commission correctly, proving it to the dealer, and paying it out on time is complex and error-prone when done in spreadsheets or legacy systems.

3. **Performance blindness** — The telco has no real-time view of how dealers are performing against their sales targets until the end of the month.

**This system automates all three end-to-end** — from the moment a dealer sells a product to the moment commission money lands in their account.

---

### The Four Business Domains

```
┌──────────────────────┐   ┌──────────────────────┐
│  1. DISTRIBUTION &   │   │  2. SUPPORT SALE      │
│     INVENTORY        │   │     PROCESS           │
│                      │   │                       │
│  • Track stock at    │   │  • Dealer records POS │
│    every location    │   │    sale (sell-out)    │
│  • Transfer stock    │   │  • Distributor ships  │
│    between sites     │   │    to dealer (sell-in)│
│  • Reserve stock     │   │  • Dealer checks live │
│    for orders        │   │    stock availability │
└──────────┬───────────┘   └──────────┬────────────┘
           │                          │
           │      Apache Kafka        │
           └──────────┬───────────────┘
                      │
┌──────────────────────┐   ┌──────────────────────┐
│  3. SALES,           │   │  4. COMMISSION &      │
│     PERFORMANCE &    │   │     INCENTIVE MGMT    │
│     REPORTING        │   │                       │
│                      │   │  • Calculate dealer   │
│  • KPI dashboards    │   │    commission per rule │
│  • Target vs actual  │   │  • Generate monthly   │
│  • Business reports  │   │    statement          │
│                      │   │  • Schedule & process │
│                      │   │    payout             │
└──────────────────────┘   └──────────────────────┘
```

---

### End-to-End Business Story

Here is the full journey of a single sale — from POS till to bank transfer:

#### Step 1 — Dealer Makes a Sale
A dealer at a retail outlet sells 5 SIM cards to a customer. They open the system and record the transaction: product, quantity, price, channel (retail / online / agent).

#### Step 2 — Stock Updates Automatically
The system immediately reduces the stock count at that dealer outlet. If stock falls below a threshold, an alert can trigger a replenishment order.

#### Step 3 — Commission is Calculated in Real Time
Within seconds of the sale being recorded, the system looks up the dealer's commission agreement, applies the applicable rule (flat amount, percentage, or tiered rate), and creates a commission record — no manual calculation needed.

#### Step 4 — Monthly Statement is Generated
At the end of each month, all commission records for a dealer roll up into a single statement. The dealer can view and dispute line items. Finance confirms the statement.

#### Step 5 — Payout is Scheduled and Processed
Once the statement is confirmed, a payout request is created and sent to the payment system. The dealer receives a confirmation notification.

#### Step 6 — Everything is Audited
Every event in the chain — the sale, the commission calculation, the payout — is written to an immutable audit log that satisfies financial compliance requirements (7-year retention).

---

### Key Business Concepts

| Term | Plain English |
|---|---|
| **Sell-out** | A dealer sells a product to an end customer (retail or online). |
| **Sell-in** | A distributor ships products to a dealer (a B2B order). |
| **Party** | Any organisation or person in the system — dealer, distributor, customer. |
| **Commission Agreement** | The contract between the telco and a dealer that defines how commission is earned. |
| **Commission Rule** | The specific rate inside an agreement: flat amount, percentage, or tiered by volume. |
| **Commission Statement** | A monthly summary of all commission earned, shared with the dealer for sign-off. |
| **Payout Request** | The instruction sent to the payment system to transfer the commission amount. |
| **KPI / Target** | A performance goal set for a dealer — e.g., sell 200 SIM cards this month. |
| **Tenant** | A separate telco operator running on the same platform. Data is fully isolated. |

---

### What the System Does NOT Do

- It does not process actual bank payments — it calls an external payment gateway.
- It does not manage product catalogues in depth — a separate product-catalog-service handles that.
- It does not replace a CRM — party records are lightweight channel partner data, not full CRM profiles.

---

## Part 2 — Technical 101

### Architecture in One Sentence

> **Eleven independent Python microservices communicate through Apache Kafka events, each owning its own PostgreSQL database, exposed through a Kong API Gateway, and secured by Keycloak.**

---

### The Big Picture

```
                         ┌───────────────────────────────┐
  Browser / Mobile  ────►│     Kong API Gateway          │
                         │  JWT validation · Rate limit  │
                         └───────────────┬───────────────┘
                                         │ HTTP
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
   ┌──────────▼──────────┐  ┌────────────▼───────────┐  ┌──────────▼──────────┐
   │  INVENTORY DOMAIN   │  │  SALES CHANNEL DOMAIN  │  │ COMMISSION DOMAIN   │
   │                     │  │                        │  │                     │
   │  inventory-service  │  │  sell-out-service      │  │  commission-rules   │
   │  stock-query-svc    │  │  sell-in-service       │  │  commission-calc    │
   │  party-service      │  │                        │  │  payout-service     │
   └──────────┬──────────┘  └────────────┬───────────┘  └──────────┬──────────┘
              │                          │                          │
              └──────────────────────────┼──────────────────────────┘
                                         │ Apache Kafka (events)
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
         ┌──────────▼──────────┐  ┌──────▼──────────┐  ┌─────▼───────────┐
         │  performance-svc    │  │  audit-service  │  │ notification-svc │
         └─────────────────────┘  └─────────────────┘  └─────────────────┘
```

---

### The Eleven Services

| Service | What It Does | Database |
|---|---|---|
| `inventory-service` | Tracks stock levels, locations, and transfers | `inventory` |
| `stock-query-service` | Fast read-only stock lookups (Redis cache) | Redis only |
| `party-service` | Manages dealers, distributors, customers | `party` |
| `sell-out-service` | Records POS transactions, triggers commission | `sellout` |
| `sell-in-service` | Manages distributor-to-dealer product orders | `sellin` |
| `performance-service` | Records KPI measurements, checks targets | `performance` |
| `commission-rules-service` | Stores commission agreements and rate rules | `commission_rules` |
| `commission-calculation-service` | Calculates commission from sale events | `commission_calc` |
| `payout-service` | Creates and processes payout requests | `payout` |
| `audit-service` | Writes every event to an immutable audit log | `audit` |
| `notification-service` | Sends emails/SMS on key events | none (stateless) |

---

### How Services Talk to Each Other

There are two communication patterns:

#### 1. Synchronous HTTP (request → response)
Used when a service needs an immediate answer.
- A dealer's browser calls `sell-out-service` to record a sale.
- `commission-calculation-service` calls `commission-rules-service` to fetch the applicable rule.

#### 2. Asynchronous Events via Apache Kafka (publish → subscribe)
Used when a service needs to notify others about something that happened, without waiting.

```
sell-out-service publishes ──► "telco.sales.sellout.completed"
                               │
              ┌────────────────┼─────────────────────┐
              ▼                ▼                     ▼
  commission-calc        inventory-svc         performance-svc
  (calculates            (decrements           (records KPI
   commission)            stock)               measurement)
```

All events follow the **CloudEvents 1.0 standard** — a lightweight envelope that carries the event type, source, timestamp, tenant ID, and business data.

**Key Kafka topics:**

| Topic | Published By | Consumed By |
|---|---|---|
| `telco.sales.sellout.completed` | sell-out-service | commission-calc, inventory, performance, audit |
| `telco.inventory.stock.transferred` | inventory-service | audit |
| `telco.commission.statement.confirmed` | commission-calc | payout, audit |
| `telco.payout.request.completed` | payout-service | notification, audit |
| `telco.party.dealer.onboarded` | party-service | commission-rules, notification |

---

### Technology Stack

| Layer | Technology | Why |
|---|---|---|
| **Language** | Python 3.12 + FastAPI | Async, fast to develop, strong typing |
| **Database** | PostgreSQL 16 | Reliable, supports row-level security for multi-tenancy |
| **ORM** | SQLAlchemy 2.0 (async) | Type-safe queries, Alembic migrations |
| **Message broker** | Apache Kafka | Durable, replayable, decouples services |
| **Cache / Read model** | Redis 7 | Sub-millisecond stock lookups |
| **API Gateway** | Kong | JWT validation, rate limiting, routing in one place |
| **Auth** | Keycloak (OIDC/OAuth2) | Industry-standard JWT tokens with tenant + role claims |
| **Frontend** | React 18 + TypeScript + Vite | Component-based UI, RTK Query for API calls |
| **Observability** | Prometheus + Grafana + Loki + Tempo | Metrics, logs, and distributed traces |
| **Container runtime** | Docker Compose (local) / Kubernetes (production) | Reproducible environments |

---

### How Each Service Is Structured

Every service follows the same internal layout:

```
sell-out-service/
├── app/
│   ├── api/v1/              ← HTTP route handlers (thin — just delegate)
│   ├── domain/
│   │   ├── models.py        ← Pydantic data models (the language of the domain)
│   │   └── services.py      ← Business logic (pure functions, easy to test)
│   └── infrastructure/
│       ├── db/
│       │   ├── models.py    ← SQLAlchemy ORM tables
│       │   ├── repository.py← Database queries (the only place SQL lives)
│       │   └── migrations/  ← Alembic migration scripts
│       └── kafka/
│           └── consumers/   ← Kafka event handlers
├── tests/
│   └── unit/                ← Fast tests, no real DB or Kafka needed
└── Dockerfile
```

**Layering rule:** each layer only knows about the layer below it. Business logic in `services.py` never imports SQLAlchemy. API handlers never write SQL.

---

### The Commission Calculation Engine

This is the most complex piece of business logic. When a sell-out event arrives:

1. **Fetch the agreement** — find the active commission agreement for this dealer and product category.
2. **Find the applicable rule** — match the sale quantity against tier ranges. Three rule types:
   - `FLAT_AMOUNT` — fixed dollar amount per unit sold
   - `PERCENTAGE` — percentage of the sale total
   - `TIERED` — rate depends on volume bracket (sell more, earn more per unit)
3. **Calculate** — apply the rule to the transaction amount and quantity.
4. **Idempotency check** — before writing, check if this `(transaction_id, agreement_id)` pair has already been processed. If so, skip. This means re-delivered Kafka messages never create duplicate commissions.
5. **Persist** — write a `CommissionEvent` and update the running `CommissionStatement` total.

---

### Multi-Tenancy

The system is built for multiple telco operators sharing the same deployment:

- Every database table has a `tenant_id` column.
- The Keycloak JWT token carries a `tenant_id` claim.
- Kong extracts it and sets an `X-Tenant-ID` header on every request.
- Services never trust a `tenant_id` supplied by the client — they always use the one from the JWT.
- PostgreSQL Row-Level Security (production) enforces that a tenant can only ever see their own rows, even if application code has a bug.

---

### Local Development in 4 Commands

```bash
make infra-up    # Start Postgres, Kafka, Redis, Keycloak
make up          # Build and start all 11 services + frontend
make migrate     # Run database migrations
make seed        # Load demo dealers, products, commission rules
```

The entire stack runs on a single laptop. One shared PostgreSQL container hosts all 9 databases (saves ~550 MB RAM vs 9 separate containers).

---

### Testing Strategy

| Layer | Tool | What It Tests |
|---|---|---|
| Unit | pytest + AsyncMock | Business logic and API handlers in isolation — no real DB or Kafka |
| Integration | pytest + SQLite | Repository queries against a real (in-memory) database |
| E2E (Kafka) | bash script | Inject a sell-out event → assert commission record created |
| E2E (HTTP) | bash script | Keycloak token → POST sale via HTTP → assert commission + stock update |

All 11 services maintain **≥ 80% unit test coverage**.

```bash
make test              # Run all unit tests
make test-rules        # Run commission rule evaluator tests (pure logic, no dependencies)
make test-integration  # Requires infra running
```

---

### Folder Map

```
Stock-commission/
│
├── services/               ← 11 microservices (each independently deployable)
├── shared/telco-common/    ← Shared Python package: JWT auth, CloudEvents, Kafka, DB mixins
├── infrastructure/
│   ├── kubernetes/         ← K8s manifests for production (Kustomize overlays)
│   ├── kong/               ← API Gateway declarative config
│   ├── keycloak/           ← Auth realm export
│   ├── terraform/          ← Cloud infra (EKS/GKE, MSK, RDS)
│   └── observability/      ← Prometheus rules, Grafana dashboards
├── frontend/               ← React 18 SPA (inventory, sales, commission, performance views)
├── scripts/                ← Kafka topic setup, database seed data
├── docker-compose.yml      ← Full local stack
├── docker-compose.infra.yml← Infrastructure only (no services)
└── Makefile                ← All developer commands in one place
```

---

### Production Deployment (Overview)

In production, the system runs on Kubernetes:

- **Database:** CloudNativePG operator — 1 primary + 2 replicas per domain, synchronous replication, point-in-time recovery.
- **Kafka:** Strimzi operator — 3-broker cluster, replication factor 3, minimum 2 in-sync replicas.
- **Services:** Minimum 3 replicas per service, auto-scaled by CPU and Kafka consumer lag.
- **Security:** CloudFlare WAF → TLS load balancer → Kong → Istio mTLS between services.
- **Secrets:** Kubernetes Secrets or HashiCorp Vault (never in environment variables or code).

---

## Quick Reference Card

| I want to... | Command / URL |
|---|---|
| Start everything locally | `make up` |
| Run all tests | `make test` |
| See all available commands | `make help` |
| Open the frontend | http://localhost:3000 |
| Browse sell-out-service API | http://localhost:8003/docs |
| Browse commission API | http://localhost:8008/docs |
| See Kafka messages | http://localhost:8090 |
| See metrics & dashboards | http://localhost:3001 (Grafana) |
| Check logs for a service | `make logs-sell-out-service` |
| Run a migration | `make migrate-inventory-service` |

---

*Last updated: June 2026*
