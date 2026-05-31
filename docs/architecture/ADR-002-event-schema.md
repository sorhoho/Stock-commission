# ADR-002: Event-Driven Architecture with CloudEvents on Apache Kafka

**Status:** Accepted  
**Date:** 2026-05-31  
**Deciders:** Architecture Team  

---

## Context

Eleven services must communicate across domain boundaries. When a dealer records a sale, at least four downstream effects must happen: commission must be calculated, stock-on-hand must be decremented, performance KPIs must be updated, and an audit record must be written. These effects are logically sequential from a business perspective but must not create a chain of synchronous dependencies that brings the POS to its knees if any one of them is slow.

The question was: how do services communicate with each other?

---

## Decision

Use **Apache Kafka** as the inter-service event bus. All cross-domain events use the **CloudEvents 1.0** specification as the envelope format. Topics follow the naming convention `telco.{domain}.{entity}.{action}`. Every consumer implements **idempotency** via a deduplicated event log.

### Topic Inventory

| Topic | Published By | Consumed By |
|---|---|---|
| `telco.sales.sellout.completed` | sell-out-service | commission-calculation-service, inventory-service, performance-service, audit-service |
| `telco.inventory.stock.transferred` | inventory-service | stock-query-service, audit-service |
| `telco.party.dealer.onboarded` | party-service | commission-rules-service, notification-service |
| `telco.commission.event.calculated` | commission-calculation-service | audit-service, notification-service |
| `telco.commission.statement.confirmed` | commission-calculation-service | payout-service |
| `telco.payout.request.completed` | payout-service | notification-service, audit-service |
| `telco.dlq.*` | Any service (on failure) | Operations / admin replay |

### CloudEvents Envelope

```json
{
  "specversion": "1.0",
  "type": "telco.sales.sellout.completed",
  "source": "/telco/sell-out-service",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "time": "2026-01-15T14:23:01Z",
  "tenantid": "tenant-abc",
  "correlationid": "req-xyz",
  "datacontenttype": "application/json",
  "data": { ... }
}
```

### Idempotency Contract

Every consumer that performs a write (commission calculation, stock update, audit insert) maintains a `processed_event_log` table:

```sql
CREATE TABLE processed_event_log (
    event_id          UUID PRIMARY KEY,
    source_topic      TEXT NOT NULL,
    processed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Before processing, the consumer attempts to insert the event ID. A `UniqueViolation` means the event was already processed; the consumer discards it without error. This guarantees exactly-once business-logic execution regardless of Kafka delivery semantics (at-least-once).

### Dead Letter Queue Strategy

After 3 failed processing attempts, a message is routed to `telco.dlq.{service}.{original-topic}`. Each service exposes an admin endpoint (`POST /admin/dlq/replay`) to replay DLQ messages after a fix is deployed.

### Retention Policy

| Topic Category | Retention |
|---|---|
| Commission events, audit | 7 years (financial regulation) |
| Sell-out transactions | 5 years |
| Inventory / stock transfers | 3 years |
| Notifications, DLQ | 30 days |

---

## Rationale

### 1. Temporal decoupling prevents cascading failures

If the commission calculation service is restarting during a deployment, sell-out-service can still accept sales. The events queue on Kafka; commission is calculated when the service recovers. With synchronous REST calls, a slow commission service would add latency to every sale.

### 2. Fan-out to multiple consumers without coordination

When a sale is recorded, four services need to react. With Kafka, each consumer has its own consumer group and reads the event independently. Adding a fifth consumer (e.g., a fraud detection service) requires no change to sell-out-service — it simply creates a new consumer group on the existing topic.

With synchronous calls, sell-out-service would need to know about every downstream service and call each one. Adding a new downstream requires changing sell-out-service.

### 3. CloudEvents standardises the envelope

Without a standard envelope, each service team invents its own metadata conventions: some put `tenant_id` in headers, some in the body, some in a `meta` field. CloudEvents defines where `id`, `source`, `type`, `time`, and extension attributes live. Any service (or external integration) that understands CloudEvents 1.0 can immediately parse the envelope without service-specific documentation.

### 4. Exactly-once commission via application-level idempotency

Kafka provides at-least-once delivery. At-exactly-once Kafka transactions are available but require all producers and consumers to use Kafka transactions, which constrains the consumer implementation significantly (no async database writes outside the transaction).

Application-level idempotency via a deduplicated event log is simpler, database-agnostic, and gives the same correctness guarantee for the commission use case: if an event is delivered twice, the second delivery finds its event_id already in the log and is discarded.

### 5. Topic naming makes the event schema self-documenting

`telco.sales.sellout.completed` unambiguously identifies:
- The organisation namespace: `telco`
- The business domain: `sales`
- The entity: `sellout`
- The action and lifecycle state: `completed`

An engineer debugging Kafka UI can immediately understand what a topic contains without opening code.

---

## Alternatives Considered

### A. Synchronous REST callbacks (webhooks from publisher to subscribers)

sell-out-service calls commission-calculation-service, inventory-service, etc. in sequence after recording a sale.

**Pros:** Simple; no message broker to operate; easy to trace.

**Cons:** Fan-out to 4 services adds their latency to the sale API response time; any one slow or failed service blocks the sale; adding a new consumer requires changing sell-out-service; there is no replay mechanism if a consumer was down.

**Rejected:** Fails the latency requirement (p99 <500ms) and the resilience requirement (POS must work even if commission service is slow).

### B. RabbitMQ / AMQP

Traditional message queue with exchanges and queues.

**Pros:** Widely understood; good client libraries; flexible routing via exchange types.

**Cons:** RabbitMQ is not designed for log retention — messages are deleted after consumption. Replaying 7 years of commission events for an audit or regulatory review is not supported without additional archival infrastructure. Kafka's log compaction and configurable retention natively support this.

**Rejected:** 7-year commission event retention is a regulatory requirement; Kafka's log-based storage is purpose-built for this.

### C. Database polling (outbox pattern without a broker)

sell-out-service writes to an `outbox` table; a polling job reads new rows and calls downstream services.

**Pros:** No external broker dependency; transactional writes to both business table and outbox.

**Cons:** Polling adds latency (seconds minimum); the outbox table becomes a bottleneck; implementing fan-out requires polling N times or a separate fan-out step; operational complexity moves into custom code.

**Rejected:** The commission-calculation latency requirement (<5 seconds after sale) is achievable with polling, but at the cost of bespoke infrastructure. Kafka natively provides the semantics needed.

### D. Google Cloud Pub/Sub or AWS SNS/SQS

Managed cloud-native message services.

**Pros:** No infrastructure to operate; native cloud integration.

**Cons:** 7-year retention is not supported by Pub/Sub (maximum 7 days) or SNS/SQS without an archival sink; vendor lock-in; local development requires emulators with partial compatibility.

**Rejected:** Retention requirements and the on-premises deployment option (some telco operators cannot use public cloud) make cloud-native brokers non-universal.

---

## Consequences

**Positive:**
- sell-out-service latency is not affected by commission or inventory processing speed
- Adding new consumers to an existing topic requires zero changes to the publisher
- The full event history is available for audit, replay, and retroactive re-calculation
- DLQ + replay provides a recovery path for any consumer failure

**Negative:**
- Operating Kafka (ZooKeeper, brokers, topic configuration, consumer lag monitoring) adds infrastructure complexity
- Debugging requires correlating logs across services using the `correlation_id` in the CloudEvents extension attribute
- Eventual consistency means a dealer refreshing their commission dashboard immediately after a sale may see a 1–2 second delay before the commission appears

**Mitigations:**
- Kafka UI (port 8090 in dev, Grafana dashboard in production) provides consumer lag visibility
- `correlation_id` propagated through CloudEvents → service logs → Tempo traces enables end-to-end trace reconstruction
- Kafka consumer lag alert fires when any consumer is >1,000 messages behind, giving operations time to react before dealers notice
