# Jireh's Agent System - Development Guidelines

## Docker Development via Justfile (Default way for running the program locally with Hot Reload)
- **Development**: `just up`
- **Build & run**: `just dev`
- **Clean**: `just clean`

## Build/Lint/Test Commands

### Backend (Python)
- **Lint**: `uv run ruff check src/`
- **Format**: `uv run ruff format src/` 
- **Type check**: `uv run ty check src/`
- **Unit tests**: `uv run pytest tests/unit/`
- **Integration/E2E tests**: `just test` (spins up required services via Docker)
- **Single integration test**: `just test tests/integration/test_specific.py::test_function`
- **Pattern match**: `just test -k "pattern"`
- **Test cleanup**: `just test-clean`
- **Migrations**: `uv run alembic upgrade head`

### Frontend (TypeScript/React)
- **Lint**: `npm run lint` (in frontend container)
- **Build**: `npm run build` (in frontend container)
- **Dev server**: `npm run dev` (in frontend container)

## Code Style Guidelines

### Python (Backend)
- **Line length**: 100 characters (ruff config)
- **Python version**: 3.11+ (ty targets 3.13)
- **Imports**: Use `isort`-style grouping (stdlib, third-party, local)
- **Type hints**: Required for all function signatures
- **Error handling**: Use custom exceptions in `src/exceptions.py`
- **Async**: Use async/await for I/O operations
- **Logging**: Use `src/utils/logger.py` logger

### TypeScript/React (Frontend)
- **ESLint**: Follow React + TypeScript recommended rules
- **Components**: Use functional components with hooks
- **Routing**: React Router v7 with createBrowserRouter
- **Styling**: Tailwind CSS v4
- **Type safety**: Strict TypeScript configuration

### General
- **Database**: Alembic for migrations, PostgreSQL with pgvector
- **API**: FastAPI with automatic OpenAPI docs at `/docs`
- Avoid using emojis in code and comments
