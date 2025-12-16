# Jireh's Agent

 A full-stack app utilizing agentic RAG workflows for working with arXiv papers.

## Stack

- **Backend**: FastAPI + Python 3.11
- **Frontend**: React 19 + TypeScript + Vite
- **Database**: PostgreSQL 16 + pgvector
- **AI**: OpenAI + LangChain + LangGraph

## Quick Start

1. Install [just](https://github.com/casey/just):
   ```bash
   brew install just
   ```

2. Setup environment:
   ```bash
   just setup
   ```
   Edit `.env` and add your API keys.

3. Start the application:
   ```bash
   just dev
   ```

4. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Hot Reload

The development environment includes hot reloading for both services:

- **Backend**: Auto-reloads on code changes (FastAPI with `--reload`)
- **Frontend**: Vite HMR (Hot Module Replacement) for instant updates
- Source code is mounted as volumes for live editing

## Common Commands

```bash
just --list      # Show all commands
just dev         # Build and start with hot reload
just up          # Start services (after building)
just down        # Stop services
just logs        # View logs
just db-shell    # Access database
just clean       # Clean up everything
```

## Requirements

- Docker & Docker Compose
- OpenAI API key
- Jina AI API key
