# Bruno API Client Setup

This repository uses [Bruno](https://www.usebruno.com/) as the API client for testing and development. Bruno is a fast, git-friendly, open-source alternative to Postman that stores collections as plain text files directly in your repository.

## Requirements

- Bruno version from November 2025 or later (required for SSE streaming support)
- The streaming endpoints use Server-Sent Events (SSE) which requires a recent Bruno version with streaming support

## Installation

### macOS

```bash
# Using Homebrew
brew install bruno
```

### Linux

```bash
# Snap
sudo snap install bruno

# Or download from https://www.usebruno.com/downloads
```

### Windows

Download the installer from [https://www.usebruno.com/downloads](https://www.usebruno.com/downloads)

## Opening the Collection

1. Launch Bruno
2. Click "Open Collection" or use `Cmd+O` (macOS) / `Ctrl+O` (Windows/Linux)
3. Navigate to this repository's root directory
4. Select the `bruno/` folder
5. Bruno will automatically load all API requests

## Collection Structure

```
bruno/
├── bruno.json                 # Collection metadata
├── environments/
│   └── local.bru             # Local environment (base_url, api_key)
├── Ask/                      # Streaming agent endpoints with SSE
├── Conversations/            # Conversation management (list, get, delete, cancel)
├── Feedback/                 # User feedback submission
├── Health/                   # Health check endpoint
├── Ops/                      # Operations (ingest, tasks, cleanup, system config)
├── Papers/                   # Paper listing and lookup
├── Root/                     # Root API information endpoint
├── Search/                   # Search endpoints (hybrid, vector, fulltext)
└── Users/                    # User profile endpoints
```

Total: **29 API requests** across 9 folders

## Environment Configuration

The collection includes a `local` environment with the following variables:

| Variable | Default | Used by |
|----------|---------|---------|
| `base_url` | `http://localhost:8000` | All requests |
| `api_key` | `your-api-key-here` | Ops endpoints (`X-Api-Key` header) |

### Using Environments

1. In Bruno, look for the environment dropdown (usually top-right)
2. Select "local" environment
3. All requests will automatically use the configured variables

### Adding More Environments

To add additional environments (e.g., production, staging):

1. Create a new file in `bruno/environments/` (e.g., `production.bru`)
2. Add the following content:

```
vars {
  base_url: https://your-production-url.com
  api_key: your-production-api-key
}
```

3. Save and select the new environment in Bruno

## Available Requests

### Health

- **Health Check**: GET `/api/v1/health` -- Check API health status

### Search

- **Hybrid Search**: POST `/api/v1/search` -- Vector + full-text + RRF fusion
- **Vector Search**: POST `/api/v1/search` -- Pure semantic search
- **Full-Text Search**: POST `/api/v1/search` -- Pure keyword search
- **Search with Filters**: POST `/api/v1/search` -- Search with category and date filters

### Ask (Streaming with SSE)

- **Ask Agent (Basic)**: POST `/api/v1/stream` -- Stream with default settings via SSE
- **Ask Agent (OpenAI)**: POST `/api/v1/stream` -- Use OpenAI provider (gpt-4o-mini)
- **Ask Agent (Z.AI)**: POST `/api/v1/stream` -- Use Z.AI provider (glm-4.6)
- **Ask Agent (Advanced Parameters)**: POST `/api/v1/stream` -- Custom parameters with streaming
- **Ask Agent (Conversation Continuity)**: POST `/api/v1/stream` -- Multi-turn conversation with streaming

All Ask Agent endpoints use Server-Sent Events (SSE) to stream responses in real-time. You will see status updates, content tokens, sources, and metadata as separate events.

### Papers

- **List Papers**: GET `/api/v1/papers` -- Paginated list with filters
- **Get Paper by arXiv ID**: GET `/api/v1/papers/:arxiv_id` -- Single paper details
- **List Papers with Filters**: GET `/api/v1/papers` -- Example with filters applied

### Conversations

- **List Conversations**: GET `/api/v1/conversations` -- Paginated list of conversations
- **Get Conversation**: GET `/api/v1/conversations/:session_id` -- Full conversation with all turns
- **Delete Conversation**: DELETE `/api/v1/conversations/:session_id` -- Delete conversation and turns
- **Cancel Stream**: POST `/api/v1/conversations/:session_id/cancel` -- Cancel active stream

### Users

- **Get Current User**: GET `/api/v1/users/me` -- Get authenticated user profile

### Ops (requires `X-Api-Key` header)

- **Cleanup Orphaned Records**: POST `/api/v1/ops/cleanup` -- Remove orphaned papers
- **Bulk Ingest Papers**: POST `/api/v1/ops/ingest` -- Ingest papers by ID or search query
- **List Tasks**: GET `/api/v1/ops/tasks` -- List background Celery tasks
- **Get Task Status**: GET `/api/v1/ops/tasks/:task_id` -- Poll task completion status
- **Revoke Task**: DELETE `/api/v1/ops/tasks/:task_id` -- Revoke a pending or running task
- **Delete Paper**: DELETE `/api/v1/ops/papers/:arxiv_id` -- Delete paper and chunks
- **Update User Tier**: PATCH `/api/v1/ops/users/:user_id/tier` -- Change a user's tier
- **Get System arXiv Searches**: GET `/api/v1/ops/system/arxiv-searches` -- Get scheduled search configs
- **Update System arXiv Searches**: PUT `/api/v1/ops/system/arxiv-searches` -- Replace all search configs

### Feedback

- **Submit Feedback**: POST `/api/v1/feedback` -- Submit user feedback to Langfuse

### Root

- **API Information**: GET `/` -- API version and feature information

## Usage Tips

### Starting the API Server

Before using Bruno, ensure your API server is running:

```bash
# Using Docker (recommended)
just dev
```

The API will be available at `http://localhost:8000`.

### Testing Streaming and Conversation Flow

The Ask Agent endpoints use Server-Sent Events (SSE) for real-time streaming. When you send a request:

1. Bruno will display events as they arrive in real-time
2. You'll see status updates (guardrail, retrieval, grading, generation)
3. Content tokens will stream as they're generated
4. Sources and metadata appear as separate events
5. The stream completes with a "done" event

To test multi-turn conversations with the Ask Agent:

1. Run "Ask Agent (Basic)" with a question
2. Watch the streaming response in real-time
3. Copy the `session_id` from the metadata event
4. Paste it into "Ask Agent (Conversation Continuity)" request body
5. Ask follow-up questions using the same `session_id`

The agent will remember context from previous turns in the conversation.

### Ops Endpoints

All Ops endpoints require the `X-Api-Key` header for authentication. Set the `api_key` variable in your environment to your actual API key before using these requests.

### Path Parameters

For requests with path parameters (e.g., `/api/v1/papers/:arxiv_id`):

1. Open the request in Bruno
2. Replace the placeholder in the URL or use the "Params" tab to fill in path parameters

### Query Parameters

For GET requests with query parameters:

1. Open the request in Bruno
2. Use the "Params" tab to enable/disable or modify query parameters
3. Bruno will automatically update the URL

## FastAPI Documentation

In addition to Bruno, you can also use the interactive FastAPI documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Bruno won't open the collection

- Make sure you're selecting the `bruno/` folder, not individual files
- Verify that `bruno/bruno.json` exists
- Try restarting Bruno

### Requests are failing

- Ensure the API server is running (`just dev`)
- Check that you're using the correct environment (local)
- Verify the `base_url` is set to `http://localhost:8000`

### SSE streaming not working

- Ensure you're using Bruno version from November 2025 or later
- Check that your Bruno installation is up to date: `brew upgrade bruno` (macOS)
- If streaming still doesn't work, try the FastAPI docs at `http://localhost:8000/docs`
- Alternative: Use curl for testing SSE: `curl -N http://localhost:8000/api/v1/stream -H "Content-Type: application/json" -d '{"query":"test"}'`

### Ops requests returning 401/403

- Verify the `api_key` environment variable is set to a valid API key
- Check that the "local" environment is selected in Bruno

### Environment variables not working

- Make sure you've selected the "local" environment in Bruno's environment dropdown
- Check that the environment file `bruno/environments/local.bru` exists

## Contributing

When adding new API endpoints:

1. Create a new `.bru` file in the appropriate folder
2. Follow the existing naming and structure conventions
3. Include documentation in the `docs` section
4. For ops endpoints, include the `X-Api-Key: {{api_key}}` header
5. Update this README if adding new folders or major features

## Resources

- Bruno Documentation: [https://docs.usebruno.com](https://docs.usebruno.com)
- Bruno GitHub: [https://github.com/usebruno/bruno](https://github.com/usebruno/bruno)
- FastAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs) (when server is running)
