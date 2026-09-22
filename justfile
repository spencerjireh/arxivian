# Arxivian -- all development runs in Docker. `just --list` shows recipes by group.

profiles := "--profile dev --profile test --profile eval --profile inteval"

default:
    @just --list

# Create backend/.env, backend/.env.test and frontend/.env from their .example files (idempotent)
[group('env')]
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    for f in backend/.env backend/.env.test frontend/.env; do
        if [ -f "$f" ]; then echo "$f exists"; else cp "$f.example" "$f" && echo "created $f -- fill in the keys listed in README.md"; fi
    done

# Build and start everything with hot reload
[group('env')]
dev: build up

[group('env')]
build:
    BUILD_TARGET=development docker compose --profile dev build

[group('env')]
rebuild:
    BUILD_TARGET=development docker compose --profile dev build --no-cache

[group('env')]
up:
    BUILD_TARGET=development docker compose --profile dev up

[group('env')]
up-d:
    BUILD_TARGET=development docker compose --profile dev up -d

[group('env')]
down:
    docker compose {{profiles}} down

# Stop everything and remove volumes
[group('env')]
down-volumes:
    docker compose {{profiles}} down -v

[group('env')]
restart:
    docker compose --profile dev restart

# Follow logs (usage: just logs, just logs app celery-worker)
[group('env')]
logs *services:
    docker compose --profile dev logs -f {{services}}

[group('env')]
ps:
    docker compose {{profiles}} ps

[group('env')]
health:
    @curl -sf http://localhost:${BACKEND_PORT:-8000}/api/v1/health | python3 -m json.tool || echo "Health check failed - is the backend running?"

# Stop everything, remove volumes and locally built images
[group('env')]
clean:
    docker compose {{profiles}} down -v --rmi local

# Full reset: clean, setup, build, start detached
[group('env')]
reset: clean setup build up-d

# Run a command in the backend container (usage: just exec-backend "uv run alembic current")
[group('shell')]
exec-backend cmd:
    docker compose --profile dev exec app {{cmd}}

[group('shell')]
exec-frontend cmd:
    docker compose --profile dev exec frontend {{cmd}}

[group('shell')]
shell-backend:
    docker compose --profile dev exec app sh

[group('shell')]
shell-frontend:
    docker compose --profile dev exec frontend sh

[group('shell')]
db-shell:
    docker compose --profile dev exec db psql -U arxiv_user -d arxiv_rag

# Run Alembic migrations in the dev backend
[group('shell')]
migrate:
    docker compose --profile dev exec app uv run alembic upgrade head

# Backend tests; bare `just test` also collects tests/evals (usage: just test tests/unit tests/api, just test -k "pattern")
[group('test')]
test *args:
    #!/usr/bin/env bash
    set -uo pipefail
    trap 'docker compose --profile test down 2>/dev/null' EXIT
    docker compose --profile test build test-runner
    docker compose --profile test run --rm test-runner uv run pytest {{args}}

# Frontend tests (usage: just test-frontend, just test-frontend --coverage)
[group('test')]
test-frontend *args:
    docker compose --profile test run --rm frontend-test-runner npm test -- {{args}}

[group('test')]
test-clean:
    docker compose --profile test rm -fsv test-db test-runner frontend-test-runner 2>/dev/null

# LLM-backed evals (requires API keys in backend/.env)
[group('eval')]
eval *args:
    #!/usr/bin/env bash
    set -uo pipefail
    trap 'docker compose --profile eval down 2>/dev/null' EXIT
    docker compose --profile eval build eval-runner
    docker compose --profile eval run --rm eval-runner \
        sh -c "uv sync --frozen --group eval && uv run pytest tests/evals -m eval -v --tb=short {{args}}"

# Seed the inteval DB (migrations + paper ingest); idempotent, re-seed only after `just clean`
[group('eval')]
inteval-seed:
    #!/usr/bin/env bash
    set -uo pipefail
    trap 'docker compose --profile inteval down 2>/dev/null' EXIT
    docker compose --profile inteval build inteval-runner
    docker compose --profile inteval up -d test-db
    docker compose --profile inteval run --rm inteval-runner \
        sh -c "uv sync --frozen --group eval && uv run alembic upgrade head && uv run python -m tests.evals.integration.seed"

# Integration evals: real LLM + real DB + real services (run inteval-seed first)
[group('eval')]
inteval *args:
    #!/usr/bin/env bash
    set -uo pipefail
    trap 'docker compose --profile inteval down 2>/dev/null' EXIT
    docker compose --profile inteval build inteval-runner
    docker compose --profile inteval up -d test-db
    docker compose --profile inteval run --rm inteval-runner \
        sh -c "uv sync --frozen --group eval && uv run alembic upgrade head && uv run pytest tests/evals/integration -m inteval -v --tb=short {{args}}"

# Ruff lint + format check (src, tests, alembic)
[group('quality')]
lint:
    docker compose --profile dev exec app uv run ruff check src/ tests/ alembic/ scripts/
    docker compose --profile dev exec app uv run ruff format --check src/ tests/ alembic/ scripts/

[group('quality')]
format:
    docker compose --profile dev exec app uv run ruff format src/ tests/ alembic/ scripts/

[group('quality')]
typecheck:
    docker compose --profile dev exec app uv run ty check src/ scripts/

# Auto-fix backend lint and formatting
[group('quality')]
fix:
    docker compose --profile dev exec app uv run ruff format src/ tests/ alembic/ scripts/
    docker compose --profile dev exec app uv run ruff check src/ tests/ alembic/ scripts/ --fix

# Likely-dead backend code (config in pyproject [tool.vulture]; advisory, decorator-registered code is noise)
[group('quality')]
deadcode:
    docker compose --profile dev exec app uv run vulture

# ESLint + knip, prettier check, tsc -- the same three steps as CI
[group('quality')]
lint-frontend:
    docker compose --profile dev run --rm --no-deps frontend sh -c "npm run lint && npm run format:check && npm run typecheck"

[group('quality')]
format-frontend:
    docker compose --profile dev run --rm --no-deps frontend npm run format

# Regenerate frontend/openapi.json from the backend and src/types/api.gen.ts from it (needs just up-d)
[group('quality')]
types:
    docker compose --profile dev exec -T app uv run python -m scripts.export_openapi > frontend/openapi.json
    docker compose --profile dev run --rm --no-deps frontend npm run types:generate

# Lint + typecheck, both trees
[group('quality')]
check: lint typecheck lint-frontend

# All git hooks against every file (needs uv and Node 22 on the host)
[group('quality')]
pre-commit:
    uvx pre-commit run --all-files

# Everything CI gates on, locally (needs `just up-d`; skips the production image builds)
[group('quality')]
ci:
    #!/usr/bin/env bash
    set -euo pipefail
    docker compose --profile dev exec app uv lock --check
    just check
    just types
    git diff --exit-code -- frontend/openapi.json frontend/src/types/api.gen.ts
    just test tests/unit tests/api --cov=src --cov-report=term-missing:skip-covered
    just test tests/integration
    just test-frontend --coverage
    POSTGRES_PASSWORD=x REDIS_PASSWORD=x TYPESAFE_API_KEY=x OPENAI_API_KEY=x \
    CLERK_DOMAIN=x CORS_ORIGINS=http://localhost VITE_CLERK_PUBLISHABLE_KEY=pk_test_x FLOWER_BASIC_AUTH=a:b \
        docker compose -f docker-compose.coolify.yml config -q
