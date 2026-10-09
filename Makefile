.DEFAULT_GOAL := help
COMPOSE_DEV  := docker compose -f docker-compose.dev.yml
COMPOSE_PROD := docker compose -f docker-compose.prod.yml
BACKEND      := cd backend &&
FRONTEND     := cd frontend &&

# LocalStack credentials. Any non-empty pair works — LocalStack does not verify
# them; they exist because boto3 refuses to sign a request without credentials.
AWS_LOCAL_ENV := ATTENDANCE_S3_BUCKET=attendance-local \
                 ATTENDANCE_S3_ENDPOINT_URL=http://localstack:4566 \
                 ATTENDANCE_S3_ACCESS_KEY=test \
                 ATTENDANCE_S3_SECRET_KEY=test

.PHONY: help dev dev-down up down logs ps shell \
        install test test-be test-fe lint format check migrate migration db-up db-migrate seed dev-api dev-web \
        up-aws clean bench sizes review

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ── first run ────────────────────────────────────────────────────────────────

install: ## Install backend + frontend dependencies locally (no docker)
	$(BACKEND) uv sync --all-groups
	$(FRONTEND) npm install

# ── docker: development ──────────────────────────────────────────────────────
dev: ## Dev stack: Vite HMR :5173, API :8000, debugpy :5678
	$(COMPOSE_DEV) up --build

up-aws: ## Dev stack + LocalStack (S3/SQS/SNS/Secrets Manager) on :4566
	$(AWS_LOCAL_ENV) $(COMPOSE_DEV) --profile aws up --build

dev-down: ## Stop the dev stack
	$(COMPOSE_DEV) down

logs: ## Tail dev logs
	$(COMPOSE_DEV) logs -f

ps: ## Show running containers
	$(COMPOSE_DEV) ps

shell: ## Shell into the backend container
	$(COMPOSE_DEV) exec backend bash

# ── docker: production shape ─────────────────────────────────────────────────
up: ## Production image locally — SPA served by FastAPI on :8000
	$(COMPOSE_PROD) up --build

down: ## Stop the production stack
	$(COMPOSE_PROD) down

# ── database ─────────────────────────────────────────────────────────────────
migrate: ## Apply migrations to the dev database
	$(COMPOSE_DEV) exec backend alembic upgrade head

migration: ## Autogenerate a migration: make migration m="add orders table"
	@test -n "$(m)" || (echo 'usage: make migration m="what changed"' && exit 1)
	$(COMPOSE_DEV) exec backend alembic revision --autogenerate -m "$(m)"
	@echo "\n⚠  Read the generated file before committing. Autogenerate misses"
	@echo "   renames (it writes drop+add, which loses the data) and never"
	@echo "   writes a backfill."

# ── quality gates (run locally, same commands run in CI) ─────────────────────
check: lint test ## Everything CI runs

test: test-be test-fe ## Run all tests

test-be: ## Backend tests with coverage
	$(BACKEND) uv run pytest

test-fe: ## Frontend tests
	$(FRONTEND) npm run test

lint: ## Lint + typecheck both sides, dependency rule, file length
	$(BACKEND) uv run ruff check src tests
	$(BACKEND) uv run ruff format --check src tests
	$(BACKEND) uv run mypy src
	$(FRONTEND) npx tsc -b --noEmit
	@python3 scripts/check_dependency_rule.py
	@python3 scripts/check_file_length.py

bench: ## Run the micro-benchmarks with timing (normally they run untimed)
	$(BACKEND) uv run pytest tests/benchmark --benchmark-enable --benchmark-only --no-cov

sizes: ## List the largest files by code lines
	@python3 scripts/check_file_length.py --list

review: ## What `/review` runs first — the mechanical half of a code review
	@$(MAKE) --no-print-directory lint
	@echo "\nMechanical checks pass. For the judgement half — layering, N+1,"
	@echo "the Query/Zustand split, test placement — run /review in Claude Code."

format: ## Auto-fix what can be auto-fixed
	$(BACKEND) uv run ruff check --fix src tests
	$(BACKEND) uv run ruff format src tests

clean: ## Remove build artefacts, caches and volumes
	$(COMPOSE_DEV) down -v
	rm -rf frontend/dist frontend/node_modules backend/.venv backend/.pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

# Attendance app local development with an isolated PostgreSQL instance.
db-up: ## Start only the local PostgreSQL container
	$(COMPOSE_DEV) up -d db

db-migrate: ## Apply migrations using backend/.env
	$(BACKEND) uv run alembic upgrade head

seed: ## Add fictional workshop data (idempotent; does not overwrite edits)
	$(BACKEND) uv run python -m attendance.seed ../mock-ui/mock-data.json

dev-api: ## Start local API on port 8001
	$(BACKEND) uv run uvicorn attendance.main:app --host 127.0.0.1 --port 8001 --reload

dev-web: ## Start local frontend on port 5184
	$(FRONTEND) npm run dev -- --host localhost --port 5184 --strictPort
