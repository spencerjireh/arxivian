# Langfuse Integration - Implementation Plan

Implementation plan for adding Langfuse observability to the Jireh's Agent System.

## Overview

```
Request --> stream.py (router)
                |
                v
           AgentService.ask_stream()
                |
                v
           CallbackHandler creates trace  <-- Single trace owner
                |
                v
           LangGraph astream_events()  <-- Auto-traces all nodes
                |
                v
           TracedLLMClient wrapper  <-- Auto-traces all LLM calls (any provider)
                |
                v
           MetadataEventData includes trace_id
```

**Architecture Notes:**
- **Single trace owner**: `CallbackHandler` creates and owns the trace - avoids duplicate traces
- **Provider-agnostic**: `TracedLLMClient` wraps any `BaseLLMClient` - works with OpenAI, ZAI, or any future provider
- **Automatic node tracing**: LangGraph `CallbackHandler` traces all nodes without code changes
- **Automatic LLM tracing**: Wrapper intercepts all LLM calls, handles streaming correctly
- **No `@observe` decorators**: Avoids known async generator bugs in Langfuse SDK
- **No contextvars**: Avoids fragile context propagation across async boundaries
- **Minimal code changes**: ~50 lines changed in existing files, 1 new file

**Why single trace owner?**
Creating traces in both `stream.py` and `service.py` would result in duplicate, disconnected traces.
The `CallbackHandler` automatically creates a trace when passed to `astream_events()`, so we let it
own the trace and extract `trace_id` from it to include in the response metadata.

---

## Phase 1: Infrastructure

### 1.1 Add Langfuse Service to Docker Compose (Optional - Self-Hosted)

**File**: `docker-compose.yml`

Skip this if using Langfuse Cloud (https://cloud.langfuse.com).

```yaml
  # Langfuse Observability Service
  langfuse-db:
    image: postgres:16-alpine
    container_name: jirehs-agent-langfuse-db
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: langfuse
      POSTGRES_DB: langfuse
    volumes:
      - langfuse_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse -d langfuse"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - jirehs-agent-network

  langfuse:
    image: langfuse/langfuse:latest
    container_name: jirehs-agent-langfuse
    environment:
      DATABASE_URL: postgresql://langfuse:langfuse@langfuse-db:5432/langfuse
      NEXTAUTH_URL: http://localhost:3001
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET:-change-me-in-production}
      SALT: ${LANGFUSE_SALT:-change-me-in-production}
      TELEMETRY_ENABLED: "false"
    ports:
      - "${LANGFUSE_PORT:-3001}:3000"
    depends_on:
      langfuse-db:
        condition: service_healthy
    networks:
      - jirehs-agent-network

# Add to volumes section:
  langfuse_postgres_data:
    driver: local
```

### 1.2 Add Environment Variables

**File**: `backend/.env`

```bash
# Langfuse Configuration
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
# Use http://langfuse:3000 for self-hosted, https://cloud.langfuse.com for cloud
LANGFUSE_HOST=https://cloud.langfuse.com
```

Note: Get API keys from Langfuse UI after setup.

### 1.3 Add Python Dependency

**File**: `backend/pyproject.toml`

```toml
dependencies = [
    # ... existing deps ...
    "langfuse>=3.0.0",
]
```

Run `uv sync` after updating.

---

## Phase 2: Configuration

### 2.1 Extend Settings

**File**: `backend/src/config.py`

Add fields matching existing pattern:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Langfuse Observability
    langfuse_enabled: bool = False
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
```

---

## Phase 3: Provider-Agnostic LLM Tracing

### 3.1 Create TracedLLMClient Wrapper

This wrapper traces **any** LLM client that implements `BaseLLMClient`. When you add new providers (Anthropic, Gemini, etc.), they automatically get tracing without any additional code.

**File**: `backend/src/clients/traced_llm_client.py` (new file)

```python
"""Provider-agnostic LLM tracing wrapper for Langfuse."""

from typing import AsyncIterator, List, Optional, Type, TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import BaseLLMClient
from src.utils.logger import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Lazy Langfuse initialization
try:
    from langfuse import Langfuse

    _langfuse_client: Optional[Langfuse] = None

    def _get_langfuse() -> Optional[Langfuse]:
        """Get or create singleton Langfuse client."""
        global _langfuse_client
        if _langfuse_client is None:
            from src.config import get_settings

            settings = get_settings()
            if (
                settings.langfuse_enabled
                and settings.langfuse_public_key
                and settings.langfuse_secret_key
            ):
                _langfuse_client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
                log.info("langfuse_client_initialized")
        return _langfuse_client

    def shutdown_langfuse() -> None:
        """Flush and shutdown the singleton Langfuse client.

        Call this during application shutdown to ensure all pending
        events are sent before the process exits.
        """
        global _langfuse_client
        if _langfuse_client is not None:
            _langfuse_client.flush()
            _langfuse_client.shutdown()
            _langfuse_client = None
            log.info("langfuse_shutdown")

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

    def _get_langfuse() -> None:
        return None

    def shutdown_langfuse() -> None:
        """No-op when Langfuse is not installed."""
        pass


class TracedLLMClient(BaseLLMClient):
    """
    Wrapper that adds Langfuse tracing to any BaseLLMClient.

    Automatically traces:
    - Non-streaming completions (full input/output)
    - Streaming completions (collects tokens, logs complete response)
    - Structured outputs (input/parsed output)

    Usage:
        base_client = OpenAIClient(...)
        traced_client = TracedLLMClient(base_client)
        # Use traced_client exactly like base_client
    """

    def __init__(self, client: BaseLLMClient):
        self._client = client

    @property
    def provider_name(self) -> str:
        return self._client.provider_name

    @property
    def model(self) -> str:
        return self._client.model

    async def generate_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        stream: bool = False,
        timeout: Optional[float] = None,
    ) -> str | AsyncIterator[str]:
        """Generate completion with automatic Langfuse tracing."""
        langfuse = _get_langfuse()
        model_name = model or self.model

        if not langfuse:
            return await self._client.generate_completion(
                messages, model, temperature, max_tokens, stream, timeout
            )

        if stream:
            return self._traced_stream(
                messages, model_name, temperature, max_tokens, timeout, langfuse
            )
        else:
            return await self._traced_completion(
                messages, model_name, temperature, max_tokens, timeout, langfuse
            )

    async def _traced_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: Optional[float],
        langfuse: "Langfuse",
    ) -> str:
        """Trace non-streaming completion."""
        generation = langfuse.generation(
            name=f"{self.provider_name}_completion",
            model=model,
            input=messages,
            metadata={"temperature": temperature, "max_tokens": max_tokens},
        )

        try:
            result = await self._client.generate_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                timeout=timeout,
            )
            # Result is str when stream=False
            generation.end(output=result)
            return result  # type: ignore[return-value]

        except Exception as e:
            generation.end(level="ERROR", status_message=str(e))
            raise

    async def _traced_stream(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: Optional[float],
        langfuse: "Langfuse",
    ) -> AsyncIterator[str]:
        """Trace streaming completion - collects tokens and logs at end."""
        generation = langfuse.generation(
            name=f"{self.provider_name}_streaming",
            model=model,
            input=messages,
            metadata={"temperature": temperature, "stream": True},
        )

        collected: list[str] = []
        try:
            stream = await self._client.generate_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                timeout=timeout,
            )

            # Stream is AsyncIterator[str] when stream=True
            async for token in stream:  # type: ignore[union-attr]
                collected.append(token)
                yield token

            generation.end(output="".join(collected))

        except Exception as e:
            generation.end(
                output="".join(collected) if collected else None,
                level="ERROR",
                status_message=str(e),
            )
            raise

    async def generate_structured(
        self,
        messages: List[ChatCompletionMessageParam],
        response_format: Type[T],
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> T:
        """Generate structured output with automatic Langfuse tracing."""
        langfuse = _get_langfuse()
        model_name = model or self.model

        if not langfuse:
            return await self._client.generate_structured(
                messages, response_format, model, timeout
            )

        generation = langfuse.generation(
            name=f"{self.provider_name}_structured",
            model=model_name,
            input=messages,
            metadata={"response_format": response_format.__name__},
        )

        try:
            result = await self._client.generate_structured(
                messages, response_format, model, timeout
            )
            generation.end(output=result.model_dump())
            return result

        except Exception as e:
            generation.end(level="ERROR", status_message=str(e))
            raise
```

### 3.2 Update Client Factory

**File**: `backend/src/factories/client_factories.py`

Wrap clients with tracing at the factory level:

```python
# Add import at top
from src.clients.traced_llm_client import TracedLLMClient, LANGFUSE_AVAILABLE


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseLLMClient:
    """Get LLM client for specified provider, with automatic Langfuse tracing."""
    settings = get_settings()

    # ... existing validation code (unchanged) ...

    # Create the base client (existing code)
    if actual_provider == "openai":
        client = OpenAIClient(
            api_key=settings.openai_api_key,
            model=actual_model,
            timeout=timeout,
        )
    elif actual_provider == "zai":
        client = ZAIClient(
            api_key=settings.zai_api_key,
            model=actual_model,
            timeout=timeout,
        )
    else:
        raise InvalidProviderError(actual_provider)

    # Wrap with tracing if Langfuse is enabled
    if LANGFUSE_AVAILABLE and settings.langfuse_enabled:
        return TracedLLMClient(client)

    return client
```

---

## Phase 4: LangGraph Node Tracing

### 4.1 Add CallbackHandler to AgentService

The Langfuse `CallbackHandler` automatically traces all LangGraph nodes without any changes to node code.
It also owns the trace and provides `trace_id` for inclusion in response metadata.

**File**: `backend/src/services/agent_service/service.py`

```python
# Add import at top
try:
    from langfuse.callback import CallbackHandler

    LANGFUSE_CALLBACK_AVAILABLE = True
except ImportError:
    LANGFUSE_CALLBACK_AVAILABLE = False


class AgentService:
    # ... existing __init__ unchanged ...

    async def ask_stream(
        self, query: str, session_id: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Execute agent workflow with streaming events."""
        # ... existing setup code unchanged (start_time, session_id generation, history loading) ...

        # Build LangGraph config with Langfuse callback
        config: dict = {}
        trace_id: str | None = None  # Will be set if Langfuse is enabled

        if LANGFUSE_CALLBACK_AVAILABLE:
            from src.config import get_settings

            settings = get_settings()
            if settings.langfuse_enabled:
                callback = CallbackHandler(
                    session_id=session_id,
                    user_id=session_id,  # Optional: use session as user for grouping
                    metadata={
                        "query": query[:200],
                        "provider": self.llm_client.provider_name,
                        "model": self.llm_client.model,
                    },
                )
                trace_id = callback.trace_id  # Extract trace_id for response metadata
                config["callbacks"] = [callback]

        # ... existing initial_state setup unchanged ...

        # Change this line to pass config
        async for event in self.graph.astream_events(
            initial_state,
            version="v2",
            config=config,  # Add this parameter
        ):
            # ... rest of event handling unchanged ...

        # Update final metadata event to include trace_id (see Phase 5)
```

**Key points:**
- `CallbackHandler` is created BEFORE `astream_events()` so we can extract `trace_id`
- `trace_id` is available immediately after `CallbackHandler` initialization
- Pass `session_id` to group traces by conversation
- Include query metadata for easier trace identification in Langfuse UI

---

## Phase 5: Schema and Service Updates

### 5.1 Update MetadataEventData Schema

**File**: `backend/src/schemas/stream.py`

Add `trace_id` field:

```python
class MetadataEventData(BaseModel):
    """Data for metadata event with execution stats."""

    query: str
    execution_time_ms: float
    retrieval_attempts: int
    rewritten_query: Optional[str] = None
    guardrail_score: Optional[int] = None
    provider: str
    model: str
    session_id: Optional[str] = None
    turn_number: int = 0
    reasoning_steps: List[str] = Field(default_factory=list)
    trace_id: Optional[str] = None  # Langfuse trace ID for feedback
```

### 5.2 Update MetadataEventData Emission in AgentService

**File**: `backend/src/services/agent_service/service.py`

Update the final metadata event to include `trace_id` (around line 372):

```python
        # Final metadata event - include trace_id from CallbackHandler
        yield StreamEvent(
            event=StreamEventType.METADATA,
            data=MetadataEventData(
                query=query,
                execution_time_ms=execution_time,
                retrieval_attempts=final_state.get("retrieval_attempts", 0),
                rewritten_query=final_state.get("rewritten_query"),
                guardrail_score=guardrail_score,
                provider=self.llm_client.provider_name,
                model=self.llm_client.model,
                session_id=session_id,
                turn_number=turn_number,
                reasoning_steps=final_state.get("metadata", {}).get("reasoning_steps", []),
                trace_id=trace_id,  # Add this line - trace_id from CallbackHandler
            ),
        )
```

**Note**: The `trace_id` variable was captured from `CallbackHandler` in Phase 4.

### 5.3 Add Feedback Schemas (Optional)

**File**: `backend/src/schemas/feedback.py` (new file)

```python
"""Feedback schemas for Langfuse integration."""

from typing import Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """User feedback submission."""

    trace_id: str = Field(..., description="Langfuse trace ID from response metadata")
    score: float = Field(
        ..., ge=0, le=1, description="Feedback score (0=negative, 1=positive)"
    )
    comment: Optional[str] = Field(
        None, max_length=1000, description="Optional feedback comment"
    )


class FeedbackResponse(BaseModel):
    """Feedback submission result."""

    success: bool
    message: str = "Feedback submitted"
```

---

## Phase 6: Router Integration (No Changes Required)

**No changes needed to `stream.py`.**

The `trace_id` is now included in `MetadataEventData` by the `AgentService` (Phase 5.2).
The router simply passes through the events as-is - no trace creation or injection needed.

**Why no router changes?**
- `CallbackHandler` in `AgentService` owns the trace (Phase 4)
- `trace_id` is extracted and included in `MetadataEventData` (Phase 5.2)
- Creating a separate trace in `stream.py` would result in duplicate, disconnected traces
- The router's existing error handling (timeout, cancellation) is sufficient

**Optional enhancement**: If you want to update the trace status on errors, you could pass
the `CallbackHandler` instance back through the event stream, but this adds complexity
for minimal benefit since Langfuse's callback already handles errors within the graph execution.

---

## Phase 7: Feedback Endpoint (Optional)

### 7.1 Create Feedback Router

**File**: `backend/src/routers/feedback.py` (new file)

```python
"""Feedback collection endpoint for Langfuse."""

from fastapi import APIRouter

from src.schemas.feedback import FeedbackRequest, FeedbackResponse
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter()

try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """Submit user feedback for a trace."""
    if not LANGFUSE_AVAILABLE:
        return FeedbackResponse(success=False, message="Langfuse not installed")

    from src.config import get_settings

    settings = get_settings()
    if not settings.langfuse_enabled:
        return FeedbackResponse(success=False, message="Feedback collection disabled")

    try:
        langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

        langfuse.score(
            trace_id=request.trace_id,
            name="user-feedback",
            value=request.score,
            comment=request.comment,
        )
        langfuse.flush()

        return FeedbackResponse(success=True)

    except Exception as e:
        log.error("feedback_submission_failed", error=str(e), trace_id=request.trace_id)
        return FeedbackResponse(success=False, message="Failed to submit feedback")
```

### 7.2 Register Router

**File**: `backend/src/main.py`

```python
from src.routers import feedback

# Add with other router registrations
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
```

---

## Phase 8: Lifespan Integration

### 8.1 Update Application Lifespan

**File**: `backend/src/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    log.info("starting application", debug=settings.debug, log_level=settings.log_level)
    await init_db()
    log.info("database initialized")

    # Log Langfuse status
    if settings.langfuse_enabled:
        log.info("langfuse_enabled", host=settings.langfuse_host)

    yield

    # Flush any pending Langfuse events on shutdown
    try:
        from src.clients.traced_llm_client import shutdown_langfuse

        shutdown_langfuse()
    except ImportError:
        pass

    log.info("shutting down application")
    await engine.dispose()
    log.info("database connections closed")
```

---

## Implementation Checklist

### Phase 1: Infrastructure
- [ ] (Optional) Add Langfuse services to `docker-compose.yml` for self-hosting
- [ ] Add environment variables to `backend/.env`
- [ ] Add `langfuse>=3.0.0` to `pyproject.toml`
- [ ] Run `uv sync` to install dependency

### Phase 2: Configuration
- [ ] Add Langfuse fields to `config.py` Settings class

### Phase 3: LLM Tracing (Provider-Agnostic)
- [ ] Create `src/clients/traced_llm_client.py`
- [ ] Update `client_factories.py` to wrap clients with `TracedLLMClient`

### Phase 4: Node Tracing
- [ ] Add `CallbackHandler` to `AgentService.ask_stream()`
- [ ] Extract `trace_id` from `CallbackHandler` after creation

### Phase 5: Schema and Service Updates
- [ ] Add `trace_id` field to `MetadataEventData` in `schemas/stream.py`
- [ ] Update `MetadataEventData` emission in `service.py` to include `trace_id`
- [ ] (Optional) Create `src/schemas/feedback.py`

### Phase 6: Router Integration
- [ ] No changes required - `trace_id` flows through existing event stream

### Phase 7: Feedback (Optional)
- [ ] Create `src/routers/feedback.py`
- [ ] Register feedback router in `main.py`

### Phase 8: Lifespan
- [ ] Update `main.py` lifespan to call `shutdown_langfuse()` from `traced_llm_client.py`

### Testing
- [ ] Start services with `just up`
- [ ] Create API keys in Langfuse UI (or use Cloud)
- [ ] Add keys to `.env`
- [ ] Test agent request and verify traces appear
- [ ] Verify LLM calls show as generations
- [ ] Verify nodes show in trace hierarchy
- [ ] Verify `trace_id` appears in metadata SSE event
- [ ] (Optional) Test feedback submission

---

## File Structure

```
backend/src/
  config.py                           # + 4 Langfuse settings
  main.py                             # + Lifespan shutdown, feedback router
  clients/
    traced_llm_client.py              # NEW - Provider-agnostic tracing wrapper + shutdown_langfuse()
    openai_client.py                  # UNCHANGED
    zai_client.py                     # UNCHANGED
    base_llm_client.py                # UNCHANGED
  factories/
    client_factories.py               # + Wrap clients with TracedLLMClient
  services/
    agent_service/
      service.py                      # + CallbackHandler + trace_id in metadata
      nodes/                          # UNCHANGED - auto-traced by callback
  routers/
    stream.py                         # UNCHANGED - trace_id flows through events
    feedback.py                       # NEW (optional) - feedback endpoint
  schemas/
    stream.py                         # + trace_id field in MetadataEventData
    feedback.py                       # NEW (optional) - feedback schemas
```

---

## What Gets Traced

| Component | Traced? | How |
|-----------|---------|-----|
| Full request | Yes | `CallbackHandler` creates root trace |
| All LangGraph nodes | Yes | `CallbackHandler` auto-traces |
| OpenAI LLM calls | Yes | `TracedLLMClient` wrapper |
| ZAI LLM calls | Yes | `TracedLLMClient` wrapper |
| Any future LLM client | Yes | Just implement `BaseLLMClient` |
| Streaming responses | Yes | Tokens collected, logged at end |
| Request errors | Yes | Trace updated with error status |
| User feedback | Optional | `/api/v1/feedback` endpoint |

---

## Example Trace in Langfuse

```
Trace: agent_stream (session: user-123)
│
├── Chain: guardrail
│   └── Generation: openai_structured
│       ├── Input: [system prompt, user query]
│       ├── Output: {"score": 85, "reasoning": "..."}
│       └── Model: gpt-4o-mini
│
├── Chain: router
│   └── Generation: openai_structured
│       ├── Input: [routing prompt]
│       ├── Output: {"action": "use_tool", "tool": "search"}
│       └── Model: gpt-4o-mini
│
├── Chain: executor
│   └── (tool execution - no LLM call)
│
├── Chain: grade_documents
│   └── Generation: openai_structured
│       └── ...
│
└── Chain: generate
    └── Generation: openai_streaming
        ├── Input: [generation prompt with context]
        ├── Output: "Based on the research papers..."
        └── Model: gpt-4o
```

---

## Adding New LLM Providers

When you add a new provider (e.g., Anthropic, Gemini), tracing works automatically:

```python
# 1. Create new client implementing BaseLLMClient
class AnthropicClient(BaseLLMClient):
    async def generate_completion(self, ...): ...
    async def generate_structured(self, ...): ...

# 2. Add to factory (tracing wrapper applied automatically)
def get_llm_client(provider, model):
    # ...
    elif actual_provider == "anthropic":
        client = AnthropicClient(...)

    # This line wraps ALL providers
    if LANGFUSE_AVAILABLE and settings.langfuse_enabled:
        return TracedLLMClient(client)
    return client

# Done! All Anthropic calls are now traced.
```

---

## Langfuse UI Access

**For self-hosted:**
1. Run `just up` (if Langfuse services added to docker-compose)
2. Open http://localhost:3001
3. Create account (first user becomes admin)
4. Create project
5. Go to Settings > API Keys
6. Copy public/secret keys to `backend/.env`
7. Restart backend container

**For Langfuse Cloud:**
1. Sign up at https://cloud.langfuse.com
2. Create project
3. Go to Settings > API Keys
4. Copy public/secret keys to `backend/.env`
5. Restart backend

---

## Frontend Integration (Optional)

### Store trace_id from Response

```typescript
const [traceId, setTraceId] = useState<string | null>(null);

// When processing SSE events
if (event.event_type === "metadata" && event.data.trace_id) {
  setTraceId(event.data.trace_id);
}
```

### Submit Feedback

```typescript
async function submitFeedback(isPositive: boolean, comment?: string) {
  if (!traceId) return;

  await fetch("/api/v1/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      trace_id: traceId,
      score: isPositive ? 1.0 : 0.0,
      comment: comment,
    }),
  });
}
```

---

## Troubleshooting

### Traces not appearing
1. Check `LANGFUSE_ENABLED=true` in `.env`
2. Verify API keys are correct
3. Check logs for `langfuse_client_initialized` message
4. Ensure `uv sync` was run after adding dependency

### LLM calls not traced
1. Verify `TracedLLMClient` is wrapping the client (check factory)
2. Check that `LANGFUSE_AVAILABLE` is `True` (dependency installed)

### Nodes not traced
1. Verify `CallbackHandler` is in the config passed to `astream_events`
2. Check that `LANGFUSE_CALLBACK_AVAILABLE` is `True`

### Streaming not showing full output
- This is expected: tokens are collected during streaming and logged when complete
- You'll see the full response in Langfuse after the stream finishes

### trace_id not appearing in metadata event
1. Verify `CallbackHandler` is created before `astream_events()` call
2. Check that `trace_id = callback.trace_id` is captured after CallbackHandler initialization
3. Verify `trace_id` is passed to `MetadataEventData` in the final yield
4. Check frontend is parsing the metadata event correctly
