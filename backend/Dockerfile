FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and UV
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy project files for dependency installation
COPY pyproject.toml uv.lock ./

# Install dependencies using UV
RUN uv sync --frozen --no-editable

# Copy application code
COPY . .

# Create directory for PDFs
RUN mkdir -p /app/data/pdfs

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"]
