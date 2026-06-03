.PHONY: help build up down logs test migrate seed e2e e2e-http lint fmt infra-up infra-down topics

# Colours
BOLD  := $(shell tput bold)
RESET := $(shell tput sgr0)
GREEN := $(shell tput setaf 2)

SERVICES = inventory-service party-service sell-out-service sell-in-service \
           stock-query-service performance-service commission-rules-service \
           commission-calculation-service payout-service notification-service \
           audit-service

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-30s$(RESET) %s\n", $$1, $$2}'

# ─── Local infra ──────────────────────────────────────────────────────────────

infra-up: ## Start infrastructure only (Kafka, PG, Redis, Keycloak)
	docker compose -f docker-compose.infra.yml up -d
	@echo "$(BOLD)Waiting for Kafka to be ready...$(RESET)"
	@sleep 15
	$(MAKE) topics

infra-down: ## Stop infrastructure
	docker compose -f docker-compose.infra.yml down

topics: ## Create Kafka topics
	bash scripts/kafka/create-topics.sh

# ─── Full stack ───────────────────────────────────────────────────────────────

up: ## Start full stack (infra + all services + frontend)
	docker compose up -d --build

down: ## Stop full stack
	docker compose down -v

build: ## Build all service Docker images
	docker compose build

logs: ## Tail logs for all services
	docker compose logs -f --tail=100

logs-%: ## Tail logs for a specific service: make logs-sell-out-service
	docker compose logs -f --tail=100 $*

# ─── Database migrations ──────────────────────────────────────────────────────

migrate: ## Run Alembic migrations for all services
	@for svc in inventory-service party-service sell-out-service sell-in-service \
	            performance-service commission-rules-service commission-calculation-service \
	            payout-service audit-service; do \
		echo "$(BOLD)Migrating $$svc...$(RESET)"; \
		docker compose run --rm $$svc alembic upgrade head; \
	done

migrate-%: ## Run migrations for a specific service: make migrate-inventory-service
	docker compose run --rm $* alembic upgrade head

# ─── Seed data ────────────────────────────────────────────────────────────────

seed: ## Seed development data (parties, commission rules + dealer agreement)
	docker compose exec -T postgres psql -U postgres -v ON_ERROR_STOP=1 -f - < scripts/seed-data/seed.sql

# ─── Testing ──────────────────────────────────────────────────────────────────

test: ## Run all unit tests
	@for svc in $(SERVICES); do \
		echo "$(BOLD)Testing $$svc...$(RESET)"; \
		cd services/$$svc && python -m pytest tests/unit/ -v --tb=short 2>&1 || exit 1; \
		cd ../..; \
	done

test-%: ## Run tests for a specific service: make test-sell-out-service
	cd services/$* && python -m pytest tests/ -v --tb=short

e2e: ## E2E pipeline test via Kafka (inject sell-out event -> assert commission)
	bash scripts/e2e-test.sh

e2e-http: ## E2E test via HTTP (Keycloak token -> POST sale API -> assert commission)
	bash scripts/e2e-http-test.sh

test-integration: ## Run integration tests (requires infra running)
	@for svc in $(SERVICES); do \
		echo "$(BOLD)Integration testing $$svc...$(RESET)"; \
		cd services/$$svc && python -m pytest tests/integration/ -v --tb=short 2>&1; \
		cd ../..; \
	done

test-rules: ## Run commission rule evaluator tests specifically
	cd services/commission-calculation-service && \
		python -m pytest tests/unit/test_rule_evaluator.py -v

# ─── Code quality ─────────────────────────────────────────────────────────────

lint: ## Lint all services with ruff
	@for svc in $(SERVICES); do \
		echo "$(BOLD)Linting $$svc...$(RESET)"; \
		cd services/$$svc && ruff check app/ tests/ 2>&1; \
		cd ../..; \
	done
	cd shared/telco-common && ruff check telco_common/

fmt: ## Format all services with ruff
	@for svc in $(SERVICES); do \
		cd services/$$svc && ruff format app/ tests/ 2>&1; \
		cd ../..; \
	done
	cd shared/telco-common && ruff format telco_common/

typecheck: ## Run mypy on all services
	@for svc in $(SERVICES); do \
		echo "$(BOLD)Type-checking $$svc...$(RESET)"; \
		cd services/$$svc && python -m mypy app/ --ignore-missing-imports 2>&1; \
		cd ../..; \
	done

# ─── Frontend ─────────────────────────────────────────────────────────────────

frontend-dev: ## Start frontend in development mode
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	cd frontend && npm run build

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

# ─── Utilities ────────────────────────────────────────────────────────────────

generate-openapi: ## Generate OpenAPI specs for all services
	@for svc in $(SERVICES); do \
		echo "Generating OpenAPI for $$svc..."; \
		docker compose run --rm $$svc python -c \
			"import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" \
			> docs/api/openapi/$$svc.json 2>&1; \
	done

ps: ## Show running containers
	docker compose ps

clean: ## Remove all build artifacts and volumes
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
