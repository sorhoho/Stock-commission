# ADR-001: Service Decomposition into Bounded Contexts

**Status:** Accepted  
**Date:** 2026-05-31  
**Deciders:** Architecture Team  

---

## Context

The system must cover four business domains simultaneously: distribution and inventory management, sales channel operations, performance and reporting, and commission/incentive management. These domains are operated by different teams (warehouse staff, field dealers, finance, regional managers) with different access patterns, deployment cadences, and reliability requirements.

The question was: build one application or many?

---

## Decision

Decompose the system into 11 independently deployable services, each aligned to a TMForum Open API specification and a well-defined DDD bounded context. Each service owns its own database schema (database-per-service pattern).

```
Domain               Service(s)                       TMForum Spec
─────────────────────────────────────────────────────────────────────
Inventory            inventory-service                 TMF637
                     stock-query-service (CQRS)        TMF637 read
Sales Channel        sell-in-service                   TMF622
                     sell-out-service                  TMF699
Performance          performance-service               TMF628
Commission           commission-rules-service          TMF651
                     commission-calculation-service    TMF666
                     payout-service                    TMF666
Platform             party-service                     TMF632
                     notification-service              Internal
                     audit-service                     Internal
```

---

## Rationale

### 1. Domain alignment beats technical alignment

Grouping by technical function (e.g., "all database access in one service") creates services that have no coherent business identity. Grouping by business domain means that when finance wants to add a commission rule type, only `commission-rules-service` changes — it does not ripple into inventory code.

### 2. Independent deployability

A change to the payout scheduler must not require redeploying the POS. Services that deploy independently can release on their own cadence. Finance's month-end commission changes deploy on month-end; the warehouse stock system deploys whenever a new scanner integration is ready. These are different teams with different risk tolerances.

### 3. Independent scaling

December brings a surge of sell-out transactions. Selling SIM cards at year-end does not suddenly require more capacity in the party management service. With separate services, only `sell-out-service` and `commission-calculation-service` receive additional replicas via HPA (Horizontal Pod Autoscaler). A monolith would scale everything or nothing.

### 4. Failure isolation

A bug in the reporting query that exhausts database connection pool connections should not prevent dealers from recording sales. Service isolation means a failure in one domain degrades only that domain's functionality.

### 5. TMForum alignment reduces integration risk

Using TMForum Open API specifications as the API contract means:
- Future system integrations (ERP, payment gateways, carrier billing systems) have a standard interface to integrate against
- Internal developers working on one service can understand another service's API from the TMForum spec, not just internal documentation
- Compliance audits against TM Forum eTOM/SID frameworks are demonstrably satisfied

---

## Alternatives Considered

### A. Layered monolith

One FastAPI application with separate packages for each domain, sharing a single PostgreSQL database.

**Pros:** Simpler to develop initially; no inter-service network calls; easy to run locally.

**Cons:** A schema change in any domain requires coordinated migration across all teams; a single slow query can impact all traffic; all domains scale together; deployment of one change requires deploying everything.

**Rejected:** The operational coupling outweighs the initial simplicity. Experience in similar systems shows that monoliths in this domain accumulate cross-cutting dependencies that make independent scaling and deployment practically impossible within 18 months.

### B. Domain-cluster services (4 services, one per domain)

Four services: Inventory, Sales, Performance, Commission.

**Pros:** Simpler than 11 services; fewer network hops for intra-domain operations.

**Cons:** `sell-in` (distributor ordering) and `sell-out` (POS transactions) have different latency requirements and write volumes; mixing them forces one to accommodate the other's NFRs. Commission rules (rarely changed by finance) and commission calculation (high-volume event consumer) have completely different operational profiles.

**Rejected:** The domains identified in requirements have enough internal divergence that the 4-service cluster would itself need to be split within one year of production load.

### C. Serverless functions per operation

Each API operation (e.g., POST /sale, GET /stock, POST /commission) as a separate Lambda/Cloud Function.

**Pros:** Fine-grained scaling; pay-per-use cost.

**Cons:** Cold starts are incompatible with the <500ms p99 API latency requirement; stateful Kafka consumer groups are architecturally awkward with functions; local development requires function emulators; distributed tracing becomes extremely complex.

**Rejected:** The latency and operational complexity requirements rule this out for this workload.

---

## Consequences

**Positive:**
- Each service can be maintained, tested, and deployed by one team independently
- TMForum compliance is built into the API surface, not retrofitted
- The boundary between "commission rules" (what the rule is) and "commission calculation" (applying the rule to a transaction) makes the system auditable — the rule that applied to a transaction is always traceable

**Negative:**
- 11 services require 11 Dockerfiles, 11 pyproject.toml files, 11 Alembic migration histories, and 11 health endpoints — the operational surface area is larger than a monolith
- Inter-service operations (e.g., "what is dealer X's active commission agreement for product category Y while recording their sale?") require careful API design or event-driven patterns rather than a JOIN

**Mitigations:**
- `shared/telco-common` package provides common FastAPI middleware, Kafka producer/consumer factory, SQLAlchemy base classes, and JWT dependency injection — services share boilerplate, not data
- `Makefile` targets (`make up`, `make migrate`, `make test`) abstract the multi-service complexity for local development
- Kubernetes Kustomize overlays manage the deployment differences per environment without duplicating manifests
