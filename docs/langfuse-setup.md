# Langfuse Setup Guide

Local Langfuse instance for LLM observability and tracing in the Arxivian dev stack.

## Prerequisites

- Docker Compose dev stack running (`just dev` or `just up-d`)
- Langfuse runs automatically as part of the `dev` profile

## 1. Access Langfuse

Open http://localhost:3001 in your browser. On first launch you'll see the sign-in page.

## 2. Create an Account

1. Navigate to **Sign up** (http://localhost:3001/auth/sign-up)
2. Fill in Name, Email, and Password
3. Click **Sign up**

## 3. Create Organization and Project

1. After sign-up, click **New Organization**
2. Enter organization name (e.g. `Arxivian`), click **Create**
3. Skip the "Invite Members" step by clicking **Next**
4. Enter project name (e.g. `arxivian`), click **Create**

## 4. Generate API Keys

1. Go to **Settings > API Keys** in the project sidebar
2. Click **Create new API keys**
3. Copy the **Secret Key** immediately -- it is only shown once
4. Note the **Public Key** and **Host** as well

## 5. Configure the Backend

Add the following to `backend/.env`:

```env
# Langfuse Observability
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=http://langfuse:3000
```

Note: The host is `http://langfuse:3000` (internal Docker network address), not `http://localhost:3001`.

## 6. Restart Backend Services

```bash
BUILD_TARGET=development docker compose --profile dev restart app celery-worker celery-beat
```

## 7. Verify

- Backend health: `just health` -- should return `status: ok`
- Langfuse dashboard: http://localhost:3001 -- traces will appear once real LLM calls are made through the application
- Tests use `LANGFUSE_ENABLED=false` in `.env.test` and mock all LLM calls, so they will not produce traces

## Architecture Notes

### How Tracing Works

- LLM calls go through LiteLLM, which has Langfuse configured as a global callback in `src/main.py` lifespan
- Langfuse utilities live in `src/clients/langfuse_utils.py` (trace context, singleton client)
- Celery workers have their own independent Langfuse singleton in `src/tasks/tracing.py`

### Docker Compose Services

| Service | Image | Profile | Port |
|---|---|---|---|
| `langfuse-db` | `postgres:16-alpine` | `dev` | internal only |
| `langfuse` | `langfuse/langfuse:2` | `dev` | 3001 -> 3000 |

### Profile Separation

Langfuse services only have the `dev` profile (not `test`). This ensures `docker compose --profile test down` (used by `just test` teardown) does not stop Langfuse while the dev stack is running. Tests don't need Langfuse since `LANGFUSE_ENABLED=false` in `.env.test`.

### Data Persistence

Langfuse data is stored in the `langfuse_postgres_data` named Docker volume. Running `just down` stops containers but preserves data. Running `just down-volumes` or `just clean` will destroy the volume and require repeating this setup from step 2.

## Troubleshooting

**Langfuse not reachable after running tests**
This was a historical issue caused by Langfuse services sharing the `test` profile. If you encounter this, verify `langfuse-db` and `langfuse` only have `profiles: [dev]` in `docker-compose.yml`.

**Backend can't connect to Langfuse**
Ensure `LANGFUSE_HOST` uses the Docker internal hostname (`http://langfuse:3000`), not `localhost:3001`.

**Lost API keys**
Generate new ones in Langfuse UI under Settings > API Keys. Update `backend/.env` and restart backend services.

**Dashboard shows no traces**
Traces only appear from real LLM calls made through the running application (chat agent, ingestion, etc.). Unit and API tests mock all LLM interactions and don't produce traces.
