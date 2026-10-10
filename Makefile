# OpsCommand task runner.
# On Windows without GNU Make, use the equivalent commands documented in README.md
# (a `scripts/` PowerShell helper and npm scripts are provided).

PY ?= python
VENV := .venv
PIP := $(VENV)/Scripts/pip.exe
RUN := $(VENV)/Scripts/python.exe
FRONT := frontend

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-18s %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Create venvs and install dependencies
	$(PY) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e "backend[dev]"
	cd $(FRONT) && npm install

.PHONY: infra
infra: ## Start Postgres + Redis via Docker Compose
	docker compose up -d postgres redis

.PHONY: dev
dev: ## Run backend API and frontend in the foreground
	docker compose up

.PHONY: migrate
migrate: ## Apply Alembic migrations
	cd backend && $(RUN) -m alembic upgrade head

.PHONY: seed
seed: ## Seed demonstration data
	cd backend && $(RUN) -m app.seed

.PHONY: test
test: test-backend test-frontend ## Run all tests

.PHONY: test-backend
test-backend: ## Run backend test suite
	cd backend && $(RUN) -m pytest -q

.PHONY: test-frontend
test-frontend: ## Run frontend unit tests
	cd $(FRONT) && npm test -- --run

.PHONY: test-e2e
test-e2e: ## Run Playwright end-to-end tests
	cd $(FRONT) && npm run test:e2e

.PHONY: lint
lint: lint-backend lint-frontend ## Run linters

.PHONY: lint-backend
lint-backend: ## Lint backend
	cd backend && $(RUN) -m ruff check .

.PHONY: lint-frontend
lint-frontend: ## Lint frontend
	cd $(FRONT) && npm run lint

.PHONY: format
format: ## Format code
	cd backend && $(RUN) -m ruff format .
	cd $(FRONT) && npm run format

.PHONY: typecheck
typecheck: ## Type-check backend and frontend
	cd backend && $(RUN) -m mypy app
	cd $(FRONT) && npm run typecheck

.PHONY: verify
verify: lint typecheck test ## Run the full validation suite

.PHONY: clean
clean: ## Remove build artifacts and caches
	rm -rf backend/.venv backend/.mypy_cache backend/.ruff_cache backend/.pytest_cache
	rm -rf $(FRONT)/node_modules $(FRONT)/dist $(FRONT)/coverage
	docker compose down -v
