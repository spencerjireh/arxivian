# Base stage - common dependencies
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies and UV
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy project files for dependency installation
COPY pyproject.toml uv.lock README.md ./

# Install dependencies using UV
RUN uv sync --frozen --no-editable

# Create directory for PDFs
RUN mkdir -p /app/data/pdfs

# Expose port
EXPOSE 8000

# Development stage
FROM base AS development

# Copy application code (will be overridden by volume mount in dev)
COPY . .

# Run migrations and start server with hot reload
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"]

# Production stage
FROM base AS production

# Copy application code
COPY . .

# Run migrations and start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"]
