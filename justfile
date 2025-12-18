# Justfile for Jireh's Agent Project
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
    BUILD_TARGET=development docker-compose --profile dev build

# Build with no cache (clean build)
rebuild:
    BUILD_TARGET=development docker-compose --profile dev build --no-cache

# Start all services (with hot reload)
up:
    BUILD_TARGET=development docker-compose --profile dev up

# Start all services (detached)
up-d:
    BUILD_TARGET=development docker-compose --profile dev up -d

# Stop all services
down:
    docker-compose down

# Stop all services and remove volumes
down-volumes:
    docker-compose down -v

# View logs from all services
logs:
    docker-compose logs -f

# View logs from specific service (usage: just logs-service backend)
logs-service service:
    docker-compose logs -f {{service}}

# Restart all services
restart:
    docker-compose restart

# Check status of all services
ps:
    docker-compose ps

# Execute command in backend container (usage: just exec-backend "ls -la")
exec-backend cmd:
    docker exec -it jirehs-agent-backend {{cmd}}

# Execute command in frontend container (usage: just exec-frontend "ls -la")
exec-frontend cmd:
    docker exec -it jirehs-agent-frontend {{cmd}}

# Open shell in backend container
shell-backend:
    docker exec -it jirehs-agent-backend sh

# Open shell in frontend container
shell-frontend:
    docker exec -it jirehs-agent-frontend sh

# Open PostgreSQL shell
db-shell:
    docker exec -it jirehs-agent-db psql -U arxiv_user -d arxiv_rag

# Check backend health
health:
    curl http://localhost:${BACKEND_PORT:-8000}/api/v1/health

# Run database migrations
migrate:
    docker exec jirehs-agent-backend uv run alembic upgrade head

# Clean up: stop containers, remove volumes, and prune unused images
clean:
    docker-compose down -v
    docker system prune -f

# Full reset: clean everything and rebuild
reset: clean setup build up-d

# Development workflow: rebuild and start with hot reload
dev: rebuild up
