# Telco Distribution & Commission System — IT Operations Guide

> **Who this is for:** System administrators, DevOps engineers, and support engineers responsible for running, monitoring, and troubleshooting the platform.

---

## System at a Glance

| Component | Technology | Purpose |
|-----------|-----------|---------|
| 11 backend services | Python 3.11 / FastAPI | Business logic, REST APIs |
| 9 PostgreSQL databases | PostgreSQL 16 | Per-service persistent storage |
| Message broker | Apache Kafka | Async event pipeline between services |
| Cache / CQRS read model | Redis 7 | Real-time stock query (microsecond reads) |
| Identity & access | Keycloak 24 | JWT tokens, RBAC, SSO |
| API gateway | Kong (db-less) | JWT validation, rate limiting, routing |
| Frontend | React 18 / nginx | Dealer & manager web UI |
| Observability | Prometheus, Grafana, Loki, Tempo | Metrics, logs, traces |
| Orchestration (prod) | Kubernetes 1.29 | HA deployment |
| Local dev | Docker Compose | Single-machine full stack |

---

## Service Map

| Service | Port | Database | TMForum Spec | Health Check |
|---------|------|----------|--------------|--------------|
| inventory-service | 8001 | postgres:5432/inventory | TMF637 | `GET /health` |
| party-service | 8002 | postgres:5432/party | TMF632 | `GET /health` |
| sell-out-service | 8003 | postgres:5432/sellout | TMF699 | `GET /health` |
| sell-in-service | 8004 | postgres:5432/sellin | TMF622 | `GET /health` |
| stock-query-service | 8005 | Redis | TMF637 CQRS | `GET /health` |
| performance-service | 8006 | postgres:5432/performance | TMF628 | `GET /health` |
| commission-rules-service | 8007 | postgres:5432/commission_rules | TMF651 | `GET /health` |
| commission-calculation-service | 8008 | postgres:5432/commission_calc | TMF666 | `GET /health` |
| payout-service | 8009 | postgres:5432/payout | TMF666 | `GET /health` |
| notification-service | 8010 | — | Internal | `GET /health` |
| audit-service | 8011 | postgres:5432/audit | Internal | `GET /health` |

---

## Day-1 Startup (Local / Dev)

```bash
# 1. Start infrastructure (Kafka, PostgreSQL, Redis, Keycloak)
make infra-up
# Wait ~30s for Postgres and Kafka health checks to pass

# 2. Run database migrations
make migrate

# 3. Seed demo data (tenants, dealers, commission rules)
make seed

# 4. Start all application services + frontend
make up

# 5. Verify all services are healthy
make ps   # or: docker compose ps
```

Everything up? Validate with:
```bash
for port in 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011; do
  echo -n "Port $port: "
  curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health
  echo
done
# All should return 200
```

---

## Daily Operations

### Start / Stop

```bash
make up          # start all containers (builds images if needed)
make down        # stop all containers (preserves data volumes)
make down-clean  # stop + remove all volumes (DESTRUCTIVE — data loss)
```

### View Logs

```bash
make logs                              # all services, tail 100
make logs-commission-calculation-service  # single service
docker compose logs -f sell-out-service   # follow in real time
```

### Run Migrations

```bash
make migrate                    # all services
make migrate-inventory-service  # single service
```

### Tail Kafka Events

Open http://localhost:8090 (Kafka UI) — no credentials needed in dev.

Key topics to watch:
| Topic | Meaning |
|-------|---------|
| `telco.sales.sellout.completed` | Every POS sale |
| `telco.commission.event.calculated` | Every commission calculation |
| `telco.commission.statement.confirmed` | Statement approved for payout |
| `telco.payout.request.completed` | Payout disbursed |
| `telco.dlq.*` | Dead letter queue — failed processing |

**DLQ messages need human review.** Any message on a `telco.dlq.*` topic means a consumer failed to process it after 3 retries.

---

## Monitoring Dashboards

Grafana: http://localhost:3001 (admin / admin)

| Dashboard | What It Shows |
|-----------|--------------|
| Service Health | HTTP request rates, error rates, p95/p99 latency per service |
| Kafka Consumer Lag | How far behind each consumer is; alert if lag > 1,000 |
| Commission Pipeline | End-to-end latency from sale → commission calculated |
| Payout SLA | Outstanding confirmed statements not yet paid |
| PostgreSQL | Connection pool usage, slow queries per database |

Prometheus: http://localhost:9090 — raw metrics scraping.

Loki: integrated in Grafana (Explore → Loki). Query by service:
```
{container="stock-commission-sell-out-service-1"}
```

---

## Troubleshooting Runbook

### Service won't start / keeps restarting

```bash
docker compose logs <service-name> --tail=50
```

Common causes:
- **Database not ready** — check `docker compose ps | grep postgres`; it must be `(healthy)` before the service starts
- **Kafka not ready** — services wait for Kafka health check; if Kafka is `restarting`, see [Kafka issues](#kafka-issues) below
- **Missing environment variable** — look for `ValidationError` or `pydantic_settings` errors in logs

### Kafka issues

Symptom: `KeeperErrorCode = NodeExists` in Kafka logs
```bash
docker compose restart zookeeper kafka
# Wait for: "started (kafka.server.KafkaServer)" in kafka logs
```

Symptom: Consumer lag growing indefinitely
- Check DLQ topic for the affected service
- Check service logs for repeated `ERROR` messages
- Replay DLQ via the admin API (see each service's `/docs`)

### Commission not calculated after a sale

1. Check sell-out-service published the event:
   ```bash
   docker compose logs sell-out-service | grep "sellout.completed"
   ```
2. Check commission-calculation-service consumed it:
   ```bash
   docker compose logs commission-calculation-service | grep "commission calculated"
   ```
3. If neither: check Kafka `telco.sales.sellout.completed` topic in Kafka UI
4. If event is there but not consumed: check commission-calculation-service for DB errors (idempotency table write)

### Database connection errors

```bash
# Connect to a specific service's database (all databases on one container)
docker compose exec postgres psql -U postgres -d sellout

# Check active connections per database
docker compose exec postgres psql -U postgres -c \
  "SELECT datname, count(*), state FROM pg_stat_activity GROUP BY datname, state;"

# Check connection pool exhaustion in service logs
grep "TimeoutError\|pool" <(docker compose logs sell-out-service)
```

### Stock-on-hand shows wrong value

The stock-query-service uses Redis as a read model, updated from Kafka events. If Redis was cleared or an event was missed:
```bash
# Force a full Redis flush and re-sync is not automatic in current version.
# Workaround: restart stock-query-service — it will re-hydrate from
# the inventory-service DB on its next Kafka event.
docker compose restart stock-query-service
```

---

## Database Access

Each service owns its database exclusively. No service reads another service's database directly.

All nine databases share a **single PostgreSQL container** in local dev (port 5432), which cuts RAM usage from ~700 MB (9 separate instances) to ~150 MB. Domain isolation is preserved — each service connects to its own named database.

| Service | DB Name | Host | Port |
|---------|---------|------|------|
| inventory-service | `inventory` | localhost | 5432 |
| party-service | `party` | localhost | 5432 |
| sell-out-service | `sellout` | localhost | 5432 |
| sell-in-service | `sellin` | localhost | 5432 |
| performance-service | `performance` | localhost | 5432 |
| commission-rules-service | `commission_rules` | localhost | 5432 |
| commission-calculation-service | `commission_calc` | localhost | 5432 |
| payout-service | `payout` | localhost | 5432 |
| audit-service | `audit` | localhost | 5432 |

Credentials (dev only): user `postgres`, password `postgres`.

```bash
# Connect to a specific service's database
docker compose exec postgres psql -U postgres -d sellout

# List all databases
docker compose exec postgres psql -U postgres -c "\l"

# Check active connections per database
docker compose exec postgres psql -U postgres -c \
  "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname ORDER BY datname;"
```

---

## Backup & Recovery (Production)

In production (Kubernetes + CloudNativePG):
- PostgreSQL: continuous WAL archiving to S3; PITR up to 30 days; RPO < 5 min
- Kafka: replication factor 3, min.insync.replicas 2; topic retention 7 years for commission/audit topics
- Redis: persistence disabled by design — the read model is rebuilt from Kafka on cold start

To restore a single service database from backup:
```bash
# Via CloudNativePG operator
kubectl annotate cluster <cluster-name> \
  k8s.enterprisedb.io/hibernate=off \
  recovery.k8s.enterprisedb.io/restore-point="2026-01-15T10:00:00Z"
```

---

## Security Notes

1. **JWT tokens** — issued by Keycloak, verified at Kong gateway. Services trust the `X-Tenant-ID` header injected by Kong after JWT validation. Services never trust client-supplied `tenant_id` values.
2. **Row-Level Security** — PostgreSQL RLS is enabled on all tables with a `tenant_id` column. Even if a service bug constructs a wrong query, the database enforces tenant isolation.
3. **Kafka ACLs** — in production, each service has its own Kafka credentials scoped to its topics.
4. **Secrets** — in dev: environment variables in docker-compose.yml. In production: Kubernetes Secrets or HashiCorp Vault.
5. **mTLS** — in production: Istio service mesh enforces mutual TLS between all services.

**Do not** use dev credentials (`postgres/postgres`, `admin/admin`) in any environment beyond local development.

---

## Deployment (Kubernetes)

```bash
# Apply base manifests
kubectl apply -k infrastructure/kubernetes/base/

# Apply environment overlay
kubectl apply -k infrastructure/kubernetes/overlays/production/

# Check rollout
kubectl -n telco-commission rollout status deployment/commission-calculation-service

# Roll back a bad deploy
kubectl -n telco-commission rollout undo deployment/sell-out-service
```

See `infrastructure/kubernetes/` for full manifests and `infrastructure/terraform/` for cloud infrastructure provisioning.

---

## Makefile Quick Reference

| Command | What it Does |
|---------|-------------|
| `make infra-up` | Start infra only (Kafka, PG, Redis, Keycloak) |
| `make up` | Start full stack |
| `make down` | Stop all containers |
| `make migrate` | Run Alembic migrations across all services |
| `make seed` | Load demo data |
| `make test` | Run all unit tests |
| `make test-rules` | Run commission rule evaluator tests only |
| `make lint` | Run ruff linter |
| `make fmt` | Auto-format with ruff |
| `make logs` | Tail all service logs |
| `make ps` | Show container status |
