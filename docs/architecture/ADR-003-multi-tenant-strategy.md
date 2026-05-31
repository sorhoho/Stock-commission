# ADR-003: Multi-Tenancy via JWT Claims and PostgreSQL Row-Level Security

**Status:** Accepted  
**Date:** 2026-05-31  
**Deciders:** Architecture Team  

---

## Context

The platform hosts multiple independent dealer networks (tenants) on a single infrastructure. A dealer from Network A must never see data from Network B — commission statements, stock levels, sales transactions, or any other record. This is both a regulatory requirement and a trust requirement: if one dealer can see another's commission rates, the commercial relationship breaks down.

The question was: how do we enforce data isolation between tenants?

---

## Decision

Enforce multi-tenancy at three independent layers:

1. **Identity layer (Keycloak):** Every user's JWT token contains a `tenant_id` claim set at login. Users cannot change their own `tenant_id`.
2. **Gateway layer (Kong):** Kong validates the JWT and injects an `X-Tenant-ID` header into every upstream request. Services never read `tenant_id` from the request body or query params supplied by the caller.
3. **Database layer (PostgreSQL RLS):** Every table with business data has a `tenant_id` column and a Row-Level Security policy that restricts reads and writes to rows matching the current session's `app.current_tenant_id` setting.

### Flow

```
Client Request
  → Kong (validates JWT, injects X-Tenant-ID header, strips client-supplied tenant_id)
    → TenantMiddleware (extracts X-Tenant-ID, sets request.state.tenant_id)
      → Service handler (reads tenant_id from request.state — never from body)
        → SQLAlchemy session (sets SET LOCAL app.current_tenant_id = '{tenant_id}')
          → PostgreSQL (RLS policy filters all queries to matching tenant_id rows)
```

### RLS Policy Pattern

Applied to every table with a `tenant_id` column:

```sql
ALTER TABLE sell_out_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON sell_out_transactions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Service connects as app_user (not superuser); superuser bypasses RLS by default
ALTER TABLE sell_out_transactions FORCE ROW LEVEL SECURITY;
```

The `FORCE ROW LEVEL SECURITY` is critical — it ensures even the table owner is subject to the policy, preventing a misconfigured service connection from bypassing RLS.

### Tenant Propagation in Events

CloudEvents carry `tenantid` as a CloudEvents extension attribute. Kafka consumers extract `tenantid` from the event envelope before processing and set it as the current session tenant for all downstream database operations.

---

## Rationale

### 1. Two independent enforcement layers, not one

Application-layer enforcement alone (service code filtering by tenant_id) fails when:
- A developer forgets to add the WHERE clause in a new query
- A bug generates the wrong tenant_id in a complex join
- A dependency injection error passes the wrong tenant context

Database-layer RLS alone (without application-layer enforcement) fails when:
- A service receives a spoofed `X-Tenant-ID` header from an attacker who bypassed Kong
- A JWT is replayed from a different tenant context

Both layers failing simultaneously requires: a spoofed Kong header AND a bug in the tenant middleware AND a bypass of RLS. This defence-in-depth makes tenant isolation robust against realistic failure modes.

### 2. JWT claims as the authoritative tenant source

The tenant_id is established at login by Keycloak, not derived from the request. Even if a malicious client sends `{"tenant_id": "competitor-abc"}` in a request body, the tenant middleware ignores it and uses only the value from the verified JWT via the Kong-injected header.

This means tenant isolation is enforced at the boundary of the system, before any service code runs.

### 3. RLS at the database level survives application-level bugs

Row-Level Security is enforced by the PostgreSQL process, not by application code. A SQL injection vulnerability in a service could allow arbitrary SQL execution — but that SQL still runs under the RLS context, so it can only return the attacking user's own tenant data.

### 4. Shared-database schema is operationally simpler than per-tenant databases

An alternative is to create a separate PostgreSQL database per tenant. This provides the strongest isolation but requires:
- Creating and migrating a new database for every tenant onboarded
- N database connections per service (one per active tenant)
- Separate backup/restore per tenant

With shared-database + RLS, onboarding a new tenant requires only a row in the `parties` table and a Keycloak realm user — no schema work. The isolation guarantee is equivalent for the threat model we're protecting against (accidental cross-tenant data access, not physical database-level isolation).

---

## Alternatives Considered

### A. Per-tenant database (database-per-tenant)

Each tenant gets their own PostgreSQL database. Services connect to the correct database based on tenant_id.

**Pros:** Complete physical isolation; simplest mental model for isolation.

**Cons:** 100 tenants = 100 databases × 11 services = 1100 database connections minimum; Alembic migrations must run against every tenant database on every schema change; connection pool fragmentation makes efficient connection reuse impossible.

**Rejected:** Connection pool exhaustion becomes a hard limit on tenant count. Operational overhead of per-tenant migrations is prohibitive.

### B. Per-tenant schema (schema-per-tenant within one database)

PostgreSQL supports multiple schemas per database. Each tenant gets their own schema namespace.

**Pros:** Strong isolation; single database instance to operate.

**Cons:** `search_path` manipulation per-request is fragile and has known bypass vectors; Alembic migration tooling does not natively support per-schema migrations; schema proliferation creates metadata bloat in large PostgreSQL installations.

**Rejected:** The `search_path` approach for multi-tenancy has well-documented security concerns in shared PostgreSQL environments.

### C. Application-layer tenant filtering only (no RLS)

Services filter all queries with `WHERE tenant_id = :current_tenant_id`. No RLS.

**Pros:** Simpler — no PostgreSQL policy management; easier to debug.

**Cons:** A single missing WHERE clause exposes all tenants' data. As the codebase grows, the probability of a missing filter approaches certainty. There is no enforcement mechanism to catch the omission before it reaches production.

**Rejected:** Single-layer enforcement fails the defence-in-depth requirement. The potential impact of a missing WHERE clause (cross-tenant commission data exposure) is unacceptable.

### D. Separate Kubernetes namespaces with separate database deployments per tenant

Full infrastructure isolation per tenant.

**Pros:** Maximum blast radius containment.

**Cons:** Infrastructure cost grows linearly with tenant count; a platform with 200 dealer networks would require 200 K8s namespaces with full infrastructure each; impractical to manage.

**Rejected:** Not economically viable for distribution-scale operations.

---

## Consequences

**Positive:**
- New tenant onboarding is a data operation (Keycloak user + parties table row), not an infrastructure operation
- A missing WHERE clause in application code is caught by RLS before it reaches production data
- Kong header injection means the `tenant_id` trust boundary is at the network edge, not in each service's business logic
- All services share the same isolation mechanism — a new developer learns one pattern, not eleven

**Negative:**
- Every query must set `app.current_tenant_id` as a session variable; failure to do so causes RLS to use `null` and return zero rows (safe failure mode, but confusing to debug)
- Connection pooling tools (PgBouncer) must be configured to use per-session mode, not per-transaction mode, because `SET LOCAL` is transaction-scoped and does not survive connection reuse in transaction-mode pools
- Kafka consumers must explicitly extract and set tenant context before any database operation — this is implemented in `telco-common` base consumer class to prevent omission

**Mitigations:**
- `TenantMiddleware` in `telco-common` sets `app.current_tenant_id` on every SQLAlchemy session — services do not set it manually
- Integration tests include a cross-tenant isolation test: create records under tenant A, authenticate as tenant B, assert zero results returned
- `FORCE ROW LEVEL SECURITY` is applied to all tables so that even a misconfigured `OWNER` connection is subject to the policy
