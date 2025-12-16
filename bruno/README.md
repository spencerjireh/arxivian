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

Alternatively, you can also use:
- File > Open Collection
- Or just drag and drop the `bruno/` folder into Bruno

## Collection Structure

The Bruno collection is organized into the following folders:

```
bruno/
├── bruno.json                 # Collection metadata
├── environments/
│   └── local.bru             # Local environment (localhost:8000)
├── Health/                   # Health check endpoint
├── Search/                   # Search endpoints (hybrid, vector, fulltext)
├── Ingest/                   # Paper ingestion endpoints
├── Ask/                      # Streaming agent endpoints with SSE (with conversation support)
├── Papers/                   # Paper management endpoints (CRUD)
└── Root/                     # Root API information endpoint
```

Total: **17 API requests** covering all endpoints

## Environment Configuration

The collection includes a `local` environment with the following variables:

- `base_url`: `http://localhost:8000`

### Using Environments

1. In Bruno, look for the environment dropdown (usually top-right)
2. Select "local" environment
3. All requests will automatically use `http://localhost:8000`

### Adding More Environments

To add additional environments (e.g., production, staging):

1. Create a new file in `bruno/environments/` (e.g., `production.bru`)
2. Add the following content:

```
vars {
  base_url: https://your-production-url.com
}
```

3. Save and select the new environment in Bruno

## Available Requests

### Health

- **Health Check**: GET `/api/v1/health` - Check API health status

### Search

- **Hybrid Search**: POST `/api/v1/search` - Vector + full-text + RRF fusion
- **Vector Search**: POST `/api/v1/search` - Pure semantic search
- **Full-Text Search**: POST `/api/v1/search` - Pure keyword search
- **Search with Filters**: POST `/api/v1/search` - Search with category and date filters

### Ingest

- **Ingest Papers (Basic)**: POST `/api/v1/ingest` - Basic arXiv ingestion
- **Ingest Papers (Advanced)**: POST `/api/v1/ingest` - With categories and date filters
- **Ingest Papers (Force Reprocess)**: POST `/api/v1/ingest` - Re-process existing papers

### Ask (Streaming with SSE)

- **Ask Agent (Basic)**: POST `/api/v1/stream` - Stream with default settings via SSE
- **Ask Agent (OpenAI)**: POST `/api/v1/stream` - Use OpenAI provider (gpt-4o-mini)
- **Ask Agent (Z.AI)**: POST `/api/v1/stream` - Use Z.AI provider (glm-4.6)
- **Ask Agent (Advanced Parameters)**: POST `/api/v1/stream` - Custom parameters with streaming
- **Ask Agent (Conversation Continuity)**: POST `/api/v1/stream` - Multi-turn conversation with streaming

All Ask Agent endpoints use Server-Sent Events (SSE) to stream responses in real-time. You will see status updates, content tokens, sources, and metadata as separate events.

### Papers

- **List Papers**: GET `/api/v1/papers` - Paginated list with filters
- **Get Paper by arXiv ID**: GET `/api/v1/papers/:arxiv_id` - Single paper details
- **Delete Paper**: DELETE `/api/v1/papers/:arxiv_id` - Delete paper and chunks
- **List Papers with Filters**: GET `/api/v1/papers` - Example with filters applied

### Root

- **API Information**: GET `/` - API version and feature information

## Usage Tips

### Starting the API Server

Before using Bruno, ensure your API server is running:

```bash
# Using Docker (recommended)
just up

# Or start services manually
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

### Viewing Request Documentation

Each request in Bruno includes documentation explaining:
- What the endpoint does
- Available parameters
- Example use cases
- Response format

Click on any request and look for the "Docs" tab to view this information.

### Path Parameters

For requests with path parameters (e.g., `/api/v1/papers/:arxiv_id`):

1. Open the request in Bruno
2. Replace `:arxiv_id` in the URL with an actual arXiv ID (e.g., `2301.12345`)
3. Or use the "Params" tab to fill in path parameters

### Query Parameters

For GET requests with query parameters:

1. Open the request in Bruno
2. Use the "Params" tab to enable/disable or modify query parameters
3. Bruno will automatically update the URL

## FastAPI Documentation

In addition to Bruno, you can also use the interactive FastAPI documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

These provide an alternative way to explore and test the API endpoints.

## Troubleshooting

### Bruno won't open the collection

- Make sure you're selecting the `bruno/` folder, not individual files
- Verify that `bruno/bruno.json` exists
- Try restarting Bruno

### Requests are failing

- Ensure the API server is running (`just up` or `just dev`)
- Check that you're using the correct environment (local)
- Verify the `base_url` is set to `http://localhost:8000`

### SSE streaming not working

- Ensure you're using Bruno version from November 2025 or later
- Check that your Bruno installation is up to date: `brew upgrade bruno` (macOS)
- If streaming still doesn't work, try the FastAPI docs at `http://localhost:8000/docs` which has built-in SSE support
- Alternative: Use curl for testing SSE: `curl -N http://localhost:8000/api/v1/stream -H "Content-Type: application/json" -d '{"query":"test"}'`

### Environment variables not working

- Make sure you've selected the "local" environment in Bruno's environment dropdown
- Check that the environment file `bruno/environments/local.bru` exists

## Contributing

When adding new API endpoints:

1. Create a new `.bru` file in the appropriate folder
2. Follow the existing naming and structure conventions
3. Include comprehensive documentation in the `docs` section
4. Update this README if adding new folders or major features

## Resources

- Bruno Documentation: [https://docs.usebruno.com](https://docs.usebruno.com)
- Bruno GitHub: [https://github.com/usebruno/bruno](https://github.com/usebruno/bruno)
- FastAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs) (when server is running)
