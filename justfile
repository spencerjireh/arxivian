# Justfile for Arxivian
# Run 'just --list' to see all available commands

# Default recipe to display help
default:
    @just --list

# Setup: Copy .env.example to .env if it doesn't exist
setup:
    @test -f .env || (cp .env.example .env && echo ".env file created. Please update with your API keys.")
    @test -f .env && echo ".env file exists."

# Build all services (with hot reload)
build:
    BUILD_TARGET=development docker compose --profile dev build

# Build with no cache (clean build)
rebuild:
    BUILD_TARGET=development docker compose --profile dev build --no-cache

# Start all services (with hot reload)
up:
    BUILD_TARGET=development docker compose --profile dev up

# Start all services (detached)
up-d:
    BUILD_TARGET=development docker compose --profile dev up -d

# Stop all services
down:
    docker compose --profile dev --profile test --profile inteval down

# Stop all services and remove volumes
down-volumes:
    docker compose --profile dev --profile test --profile inteval down -v

# View logs from all services
logs:
    docker compose --profile dev logs -f

# View logs from specific service (usage: just logs-service app)
logs-service service:
    docker compose --profile dev logs -f {{service}}

# Restart all services
restart:
    docker compose --profile dev restart

# Check status of all services
ps:
    docker compose --profile dev --profile test --profile inteval ps

# Execute command in backend container (usage: just exec-backend "ls -la")
exec-backend cmd:
    docker compose --profile dev exec app {{cmd}}

# Execute command in frontend container (usage: just exec-frontend "ls -la")
exec-frontend cmd:
    docker compose --profile dev exec frontend {{cmd}}

# Open shell in backend container
shell-backend:
    docker compose --profile dev exec app sh

# Open shell in frontend container
shell-frontend:
    docker compose --profile dev exec frontend sh

# Open PostgreSQL shell
db-shell:
    docker compose exec db psql -U arxiv_user -d arxiv_rag

# Check backend health
health:
    @curl -sf http://localhost:${BACKEND_PORT:-8000}/api/v1/health | python3 -m json.tool || echo "Health check failed - is the backend running?"

# Run database migrations
migrate:
    docker compose --profile dev exec app uv run alembic upgrade head

# Clean up: stop containers, remove volumes, and remove locally built images
clean:
    docker compose --profile dev --profile test --profile inteval down -v --rmi local

# Full reset: clean everything and rebuild
reset: clean setup build up-d

# Development workflow: build and start with hot reload
dev: build up

# =============================================================================
# Testing
# =============================================================================

# Run tests (usage: just test, just test tests/integration, just test -k "pattern")
test *args:
    #!/usr/bin/env bash
    set -uo pipefail
    trap 'docker compose --profile test down 2>/dev/null' EXIT
    docker compose --profile test build test-runner
    docker compose --profile test run --rm test-runner uv run pytest {{args}}

# Cleanup test containers
test-clean:
    docker compose --profile test rm -fsv test-db test-runner frontend-test-runner 2>/dev/null

# =============================================================================
# Evaluation
# =============================================================================

# Run LLM-backed evals (requires API keys in backend/.env)
eval *args:
    #!/usr/bin/env bash
    set -uo pipefail
    trap 'docker compose --profile eval down 2>/dev/null' EXIT
    docker compose --profile eval build eval-runner
    docker compose --profile eval run --rm eval-runner \
        sh -c "uv sync --frozen --extra dev --extra eval && uv run pytest tests/evals -m eval -v --tb=short {{args}}"

# =============================================================================
# Integration Evaluation (real LLM + real DB + real services)
# =============================================================================

# Seed DB for integration evals (migrations + paper ingest). Idempotent.
# Data persists in test_postgres_data volume; only re-seed after `just clean`.
inteval-seed:
    #!/usr/bin/env bash
    set -uo pipefail
    trap 'docker compose --profile inteval down 2>/dev/null' EXIT
    docker compose --profile inteval build inteval-runner
    docker compose --profile inteval up -d test-db
    docker compose --profile inteval run --rm inteval-runner \
        sh -c "uv sync --frozen --extra dev --extra eval && uv run alembic upgrade head && uv run python -m tests.evals.integration.seed"

# Run integration evals (requires inteval-seed first).
# Data persists in test_postgres_data volume; only re-seed after `just clean`.
inteval *args:
    #!/usr/bin/env bash
    set -uo pipefail
    trap 'docker compose --profile inteval down 2>/dev/null' EXIT
    docker compose --profile inteval build inteval-runner
    docker compose --profile inteval up -d test-db
    docker compose --profile inteval run --rm inteval-runner \
        sh -c "uv sync --frozen --extra dev --extra eval && uv run alembic upgrade head && uv run pytest tests/evals/integration -m inteval -v --tb=short {{args}}"

# =============================================================================
# Code Quality
# =============================================================================

# Run Python linter
lint:
    docker compose --profile dev exec app uv run ruff check src/

# Run Python formatter
format:
    docker compose --profile dev exec app uv run ruff format src/

# Run Python type checker
typecheck:
    docker compose --profile dev exec app uv run ty check src/

# Run all checks (lint + typecheck)
check: lint typecheck

# Auto-fix Python lint and formatting issues
fix:
    docker compose --profile dev exec app uv run ruff format src/
    docker compose --profile dev exec app uv run ruff check src/ --fix

# Run frontend linting
lint-frontend:
    docker compose --profile dev run --rm --no-deps frontend npm run lint

# Run frontend tests (usage: just test-frontend, just test-frontend -- --reporter=verbose)
test-frontend *args:
    docker compose --profile test run --rm frontend-test-runner npm test -- {{args}}
