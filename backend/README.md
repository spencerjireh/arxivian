# Jirehs Agent

A document processing and search service built with Python and FastAPI.

## Features

- Document ingestion and processing
- PDF parsing and text extraction
- Vector embeddings generation
- Semantic search capabilities
- REST API endpoints for document management and search

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables:
```bash
cp .env.example .env
```

3. Run the application:
```bash
uv run main.py
```

## API Endpoints

- `POST /ingest` - Ingest documents
- `POST /search` - Search documents
- `POST /ask` - Ask questions about documents
- `GET /health` - Health check

## Database

The application uses SQLAlchemy with Alembic for database migrations.

## Configuration

Configure your environment in the `.env` file.

