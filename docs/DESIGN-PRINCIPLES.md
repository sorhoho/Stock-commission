# Telco Distribution & Commission System — Design Principles & Rationale

> **Who this is for:** Business stakeholders, product managers, finance leads, and senior IT staff who want to understand *why* the system is built the way it is — not just how it works.

---

## The North Star

Every design decision in this system was made against a single question:

> **"Can we tell, with certainty and speed, who sold what, how much commission they earned, and confirm that we haven't paid it twice?"**

Everything else — the microservices, the event bus, the audit log, the real-time stock tracking — flows from that requirement.

---

## Principle 1: Events Are the Source of Truth

### What this means
Every business-significant action — a sale, a stock transfer, a commission calculation, a payout — is recorded as an **immutable event** on Apache Kafka before any downstream processing happens. The database stores current state; the event log stores what happened and when.

### Why
In the old Excel world, a finance analyst would correct a spreadsheet and the previous number would disappear. Disputes were impossible to investigate because there was no history.

With events as truth:
- Every commission can be traced back to the exact sale event that triggered it
- If a service restarts, it can replay events and rebuild its state — no data is lost
- The audit trail is not a separate system bolted on after the fact; it is the system

### The trade-off accepted
Eventual consistency: when a sale is recorded, stock-on-hand and the commission figure are not updated in the same database transaction. They appear within seconds — not instantly at the moment of commit. For this business (where "real-time" means seconds, not microseconds), this is an acceptable trade-off for the resilience and auditability it buys.

---

## Principle 2: Each Business Domain Owns Its Data

### What this means
The system is split into 11 independent services. Inventory data lives only in the inventory service database. Commission data lives only in the commission service database. No service reaches into another service's database — they communicate exclusively through events and APIs.

### Why
In a monolith, everything is connected to everything. Changing the commission rules table could accidentally break the stock transfer logic because they share the same schema. Teams step on each other.

By giving each domain its own database:
- The inventory team can add a new field without asking the commission team for permission
- A database failure in the commission service does not bring down the POS (sell-out service)
- Each service can be scaled independently — if December brings a surge of sales, only the sell-out and commission services need more capacity; the party management service does not

### The trade-off accepted
Joining data across domains requires API calls or Kafka consumers rather than a SQL JOIN. Reports that span multiple domains are slightly more complex to build. We accept this because the alternative — a shared monolith database — has historically been the single biggest cause of fragility in enterprise systems.

---

## Principle 3: Commission Calculation Must Be Idempotent

### What this means
If the same sale event is processed twice — because of a network retry, a service restart, a Kafka re-delivery — the commission must be calculated exactly once. The system actively detects duplicates and discards them.

### Why
Paying a dealer double commission is not just a financial loss. It erodes trust in the entire platform. Every operator will spend time double-checking the figures rather than trusting them.

The implementation records every processed sale event in a dedicated table with a unique constraint on `(sale_transaction_id, agreement_id)`. Any duplicate triggers a database constraint violation, which is caught and silently discarded. The dealer gets paid once.

### The trade-off accepted
There is a small write overhead for every commission calculation — an extra row in the idempotency log. This is a deliberate, cheap insurance policy against a very expensive error.

---

## Principle 4: Commission Rules Are Pure Functions

### What this means
The rule evaluator — the code that takes a sale and a commission agreement and produces a commission amount — is a **pure function**: given the same inputs, it always produces the same output. It has no side effects, no database calls, no randomness.

### Why
Commission disputes are inevitable. A dealer will say "I should have earned RM 15 per unit, not RM 10." Finance needs to be able to re-run the exact calculation that produced a number, verify it against the rule that was active at the time, and show the dealer a deterministic result.

Because the evaluator is pure:
- It can be tested exhaustively without setting up a database
- It can be run in isolation in a dispute investigation
- The same rule evaluated against the same sale will always produce the same number, years later

### The trade-off accepted
Rules are evaluated at transaction time using the agreement that was active then. Changing a rule does not retroactively change old commissions. This is both a technical constraint and a deliberate business policy: dealers need predictability. A rule change should not retroactively reduce what a dealer earned last month.

---

## Principle 5: Stock Queries Must Never Slow Down the POS

### What this means
The `stock-query-service` is a separate service that answers "how many units are at location X?" It reads from Redis (an in-memory cache) — not from the inventory database. Stock levels in Redis are updated in near-real-time from Kafka events.

### Why
A dealer at the point of sale needs to check stock availability instantly. If that query hits the same PostgreSQL database that is processing stock transfer writes, a slow transfer operation could make the stock check slow too — the POS hangs, the customer waits, the dealer is frustrated.

By separating reads from writes (CQRS — Command Query Responsibility Segregation), the stock-check path has zero contention with write operations. Redis reads are microsecond-fast regardless of how many transfers are being processed simultaneously.

### The trade-off accepted
Redis is not durable by design (in this system). If Redis is cleared, stock levels must be rebuilt from Kafka events. This is handled automatically on service restart. The data is never permanently lost — it is derived from the event log.

---

## Principle 6: The Platform Never Trusts the Client

### What this means
When a dealer logs in and makes an API call, that call carries a JWT token issued by Keycloak (the identity system). The token contains a `tenant_id` claim — identifying which dealer organisation the user belongs to.

No API call is allowed to say "show me data for tenant X" in the request body. The tenant identity comes exclusively from the verified token. Even if a caller knows another dealer's tenant ID, they cannot access that dealer's data.

### Why
Channel distribution involves competing dealers. If one dealer could accidentally (or intentionally) query another dealer's commission statements or stock levels, trust in the platform collapses immediately.

Two layers enforce isolation:
1. **Kong API Gateway** validates the JWT and injects the `X-Tenant-ID` header — untrusted clients cannot forge this header
2. **PostgreSQL Row-Level Security (RLS)** enforces tenant filtering at the database level — even if a bug in service code constructed the wrong query, the database itself would return only the calling tenant's rows

Neither layer alone is sufficient. Together they provide defence-in-depth.

### The trade-off accepted
Multi-tenancy adds complexity to every query. Every table has a `tenant_id` column; every RLS policy must be correct. The complexity is justified: a single data isolation failure would be a critical incident.

---

## Principle 7: Observability Is Not Optional

### What this means
Every service emits structured logs (Loki), metrics (Prometheus), and distributed traces (Tempo). A single Grafana dashboard correlates all three. An engineer investigating a slow commission calculation can trace the exact path of a specific event through every service it touched.

### Why
Distributed systems fail in distributed ways. A commission not being calculated might be because the sell-out service didn't publish the event, or Kafka is behind, or the commission service's database is slow, or the idempotency check flagged it as a duplicate.

Without end-to-end tracing, diagnosing this requires manually correlating logs across 4 services. With Tempo traces, a single trace ID links every log line and span in the entire pipeline.

### The trade-off accepted
There is a small latency overhead (typically <1ms) for each trace span. The Prometheus metrics scrape and Loki log shipping add network I/O. These costs are negligible compared to the hours saved during an incident.

---

## Principle 8: Design for the Business Cycle, Not Just the Technical Load

### What this means
Month-end is the most critical period: commission statements are reviewed, disputes are raised, the payout job runs on the 1st of each month at 02:00. The system is designed for this rhythm.

Specific decisions that reflect the business cycle:
- **Commission statements** accumulate as DRAFT all month, then batch-confirm at month-end — this is how finance works, not an accident
- **Payout scheduler** runs overnight (02:00) to avoid business-hours load; if it fails, it retries the next day — matching the tolerance of a disbursement job
- **Kafka retention** for commission topics is 7 years — not because Kafka recommends it, but because financial regulations require it
- **Table partitioning by month** on `commission_events` — month-end reports scan one partition, not the entire table

### Why
A system that is technically correct but ignores the rhythm of the business will be worked around. Finance will export to Excel at month-end if the system can't produce reliable statements on time.

---

## How These Principles Connect

```
Principle 3 (Idempotency)
         ↑
Principle 1 (Events as Truth) → Principle 5 (CQRS Read Model)
         ↓
Principle 4 (Pure Rule Engine) → Principle 2 (Domain Isolation)
         ↓
Principle 7 (Observability) ← Principle 8 (Business Cycle Design)
         ↑
    Principle 6 (Never Trust Client)
```

Each principle reinforces the others. Events being the source of truth only works if the event pipeline is idempotent. Domain isolation only works if queries are routed to the correct read model. Observability only delivers value if there is a trace ID connecting every part of the pipeline end-to-end.

---

## What We Chose Not to Do (and Why)

| Approach Rejected | Why |
|---|---|
| **Monolith with a shared database** | Fast to build, brittle to operate. A bug in commission code can corrupt inventory data. Teams cannot deploy independently. |
| **Synchronous API calls between services** | If the commission service is slow, the POS waits. A cascade of slow calls can bring the whole system down. Events decouple this. |
| **Batch overnight commission calculation** | Dealers only know their commission the next morning. Disputes take longer to identify. Real-time calculation removes the information lag. |
| **Single shared Kafka consumer group** | All services competing on one consumer group would create ordering and partitioning nightmares. Each service has its own consumer group with independent offset management. |
| **Row-level security via application code only** | Application bugs happen. RLS at the database level is the last line of defence and cannot be bypassed by service-layer mistakes. |
| **Mutable event log** | If events could be edited, auditors and regulators cannot trust the record. Immutability is not just a design choice; it is a compliance requirement. |

---

## For Business Stakeholders: The One-Page Summary

**Why is the system so "complicated"?**

The business requirement is deceptively simple: "calculate commissions accurately and pay them on time." But accuracy at scale means:

1. Every calculation must be traceable back to an original sale
2. No dealer can ever be paid double by accident
3. No dealer can ever see another dealer's data
4. Changing a commission rule must not retroactively alter what was already earned
5. The POS must work even if the commission engine is slow

Each of those five requirements rules out a simpler approach. The architecture is the direct consequence of the business rules.

**What does "real-time" cost?**

Real-time commission visibility requires the event pipeline (Kafka), the cache layer (Redis), and the CQRS split. Each adds complexity. The payoff is that a regional manager can see a sale and its commission impact within seconds, not the next morning — which is the difference between reacting to yesterday's performance and managing today's performance.

**What happens if the system goes down?**

Sales can still be recorded at the POS (the sell-out service is isolated). Commission events queue on Kafka and are processed when the commission service recovers — no commissions are lost, just delayed. The exact delay can be monitored on the Kafka consumer lag dashboard. This resilience is why we use an event bus rather than direct service-to-service calls.
