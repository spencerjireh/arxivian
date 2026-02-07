# LiteLLM Integration Plan

## Goal

Replace the custom multi-provider LLM client layer (`OpenAIClient`, `ZAIClient`, `TracedLLMClient`) with LiteLLM's unified SDK. `InstrumentedLLMClient` is also removed (it is unused dead code -- `get_llm_client()` never wraps with it). The existing `BaseLLMClient` interface is preserved so all 7 calling sites (4 `generate_completion` + 3 `generate_structured` across agent nodes and tools) require zero changes.

**Supported providers: OpenAI and NVIDIA NIM only.** Z.AI (GLM models) is being dropped as a provider -- all ZAI-specific code, config fields, and env vars are removed in this migration. NVIDIA NIM replaces it as the second provider. NVIDIA NIM is natively supported by LiteLLM via the `nvidia_nim/` prefix (e.g., `nvidia_nim/meta/llama-3.1-8b-instruct`), so no custom endpoint routing is needed.

## Current Architecture

```
get_llm_client() factory
  -> OpenAIClient(BaseLLMClient)   OR   ZAIClient(BaseLLMClient)
    -> wrapped by TracedLLMClient(BaseLLMClient)  [if Langfuse enabled]
      -> used by AgentContext -> passed to all nodes/tools

Note: InstrumentedLLMClient exists but is dead code (never used by the factory).
```

### Files to modify or remove

| File | Action |
|------|--------|
| `clients/base_llm_client.py` | Keep (interface preserved) |
| `clients/openai_client.py` | Remove |
| `clients/zai_client.py` | Remove |
| `clients/instrumented_llm_client.py` | Remove (dead code -- never used by `get_llm_client()`) |
| `clients/traced_llm_client.py` | Replace with `clients/langfuse_utils.py` (keep only Langfuse singleton + trace context helpers) |
| `clients/__init__.py` | Update exports (keep `ArxivClient`, `JinaEmbeddingsClient`) |
| `clients/litellm_client.py` | Create (new) |
| `factories/client_factories.py` | Rewrite `get_llm_client()`; remove deprecated `get_openai_client()`; remove `TracedLLMClient`/`LANGFUSE_AVAILABLE` imports and wrapping logic |
| `config.py` | Update LLM config fields; remove ZAI fields |
| `routers/feedback.py` | Update import: `_get_langfuse` -> `get_langfuse` (renamed, moved to `langfuse_utils`) |
| `services/agent_service/service.py` | Update imports: `set_trace_context` (line 11) and `_get_langfuse` (line 415) -> from `langfuse_utils`; rename `_get_langfuse` to `get_langfuse` |
| `main.py` | Update `from src.clients.traced_llm_client import shutdown_langfuse` -> `from src.clients.langfuse_utils import shutdown_langfuse` (lifespan shutdown); update "Z.AI" string in features list (line 105) to "NVIDIA NIM" |
| `routers/health.py` | Update provider/model config references (currently checks per-provider API keys and allowed models) |
| `routers/stream.py` | Update "Z.AI" in docstring (line 47) to "NVIDIA NIM" |
| `tasks/tracing.py` | No change (has its own Langfuse singleton for Celery workers) |

### Files with zero changes needed

These use the `BaseLLMClient` interface and are unaffected by the migration.

**7 call sites** (call `generate_completion` or `generate_structured` directly):
- `services/agent_service/nodes/generation.py:45` -- `generate_completion`
- `services/agent_service/nodes/out_of_scope.py:52` -- `generate_completion`
- `services/agent_service/nodes/rewrite.py:30` -- `generate_completion`
- `services/agent_service/tools/summarize_paper.py:77` -- `generate_completion`
- `services/agent_service/nodes/grading.py:30` -- `generate_structured`
- `services/agent_service/nodes/guardrail.py:46` -- `generate_structured`
- `services/agent_service/nodes/router.py:86` -- `generate_structured`

**Dependency wiring** (store/pass `llm_client` but don't call LLM methods):
- `services/agent_service/context.py`
- `services/agent_service/graph_builder.py`

---

## Step 1: Add litellm dependency

Add `litellm` to `pyproject.toml` (or `requirements.txt`).

```
uv add litellm
```

Verify it installs cleanly inside the backend Docker container.

**Note:** Keep `openai` as a direct dependency in `pyproject.toml`. Even though `OpenAIClient` is removed, the `openai` package is still needed for `ChatCompletionMessageParam` type imports used in `BaseLLMClient` and all 7 call sites. LiteLLM also depends on `openai` transitively, but the direct dependency ensures type imports remain available.

---

## Step 2: Create `clients/langfuse_utils.py`

Extract the Langfuse singleton, trace context helpers, and shutdown function from `traced_llm_client.py` into a standalone module. This decouples Langfuse from the LLM client layer.

```python
"""Langfuse singleton and trace context utilities."""

from contextvars import ContextVar
from typing import Optional

from src.utils.logger import get_logger

log = get_logger(__name__)

_current_trace_id: ContextVar[str | None] = ContextVar("langfuse_trace_id", default=None)
_langfuse_client = None
LANGFUSE_AVAILABLE = False

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    Langfuse = None


def set_trace_context(trace_id: str | None) -> None:
    _current_trace_id.set(trace_id)


def get_trace_context() -> str | None:
    return _current_trace_id.get()


def get_langfuse() -> Optional["Langfuse"]:
    """Get or create singleton Langfuse client."""
    global _langfuse_client
    if not LANGFUSE_AVAILABLE:
        return None
    if _langfuse_client is None:
        from src.config import get_settings
        settings = get_settings()
        if settings.langfuse_enabled:
            if not settings.langfuse_public_key or not settings.langfuse_secret_key:
                log.warning("langfuse_keys_missing")
                return None
            _langfuse_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
    return _langfuse_client


def shutdown_langfuse() -> None:
    global _langfuse_client
    if _langfuse_client is not None:
        _langfuse_client.flush()
        _langfuse_client.shutdown()
        _langfuse_client = None
```

Update imports in:
- `routers/feedback.py`: `from src.clients.traced_llm_client import _get_langfuse` -> `from src.clients.langfuse_utils import get_langfuse`
- `services/agent_service/service.py`: `from src.clients.traced_llm_client import set_trace_context` -> `from src.clients.langfuse_utils import set_trace_context` (line 11), and lazy import of `_get_langfuse` (line 415) -> `get_langfuse`
- `main.py`: `from src.clients.traced_llm_client import shutdown_langfuse` (line 48) -> `from src.clients.langfuse_utils import shutdown_langfuse`

---

## Step 3: Create `clients/litellm_client.py`

Implement `LiteLLMClient(BaseLLMClient)` using the `litellm` SDK. This single class replaces `OpenAIClient`, `ZAIClient`, and `TracedLLMClient`.

**Important:** Langfuse callbacks (`litellm.success_callback`) must be set once at app startup (in `main.py` lifespan or a module-level init), NOT in `LiteLLMClient.__init__()`, because `litellm.success_callback` is global state and `get_llm_client()` creates a new instance per request.

Both OpenAI and NVIDIA NIM are natively supported by LiteLLM, so no custom provider routing (`_get_provider_kwargs`) is needed. LiteLLM reads `OPENAI_API_KEY` and `NVIDIA_NIM_API_KEY` from env vars automatically and routes based on the model prefix.

```python
"""LLM client using LiteLLM unified API."""

import asyncio
from typing import AsyncIterator, List, Optional, Type, TypeVar

import litellm
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import BaseLLMClient
from src.clients.langfuse_utils import get_trace_context
from src.exceptions import LLMTimeoutError
from src.utils.logger import get_logger

log = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class LiteLLMClient(BaseLLMClient):
    """
    Unified LLM client backed by LiteLLM.

    Handles OpenAI and NVIDIA NIM providers via LiteLLM's model format:
    - "openai/gpt-4o", "openai/gpt-4o-mini"
    - "nvidia_nim/meta/llama-3.1-8b-instruct", "nvidia_nim/nvidia/llama-3.1-nemotron-70b-instruct"

    Both providers are natively supported by LiteLLM. API keys are read from
    env vars (OPENAI_API_KEY, NVIDIA_NIM_API_KEY) automatically.

    Langfuse tracing is handled via LiteLLM's native callback system,
    configured at app startup (not per-instance).
    """

    def __init__(self, model: str, timeout: float = 60.0):
        """
        Args:
            model: LiteLLM model string (e.g. "openai/gpt-4o-mini",
                   "nvidia_nim/meta/llama-3.1-8b-instruct")
            timeout: Default timeout in seconds per LLM call
        """
        self._model = model
        self._timeout = timeout

        # Parse provider from model string (e.g. "openai/gpt-4o" -> "openai")
        self._provider = model.split("/")[0] if "/" in model else "openai"

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    async def generate_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        stream: bool = False,
        timeout: Optional[float] = None,
    ) -> str | AsyncIterator[str]:
        effective_model = model or self._model
        effective_timeout = timeout or self._timeout

        # Build metadata for Langfuse trace nesting
        metadata = self._build_metadata()

        try:
            if stream:
                return self._stream(
                    messages, effective_model, temperature, max_tokens,
                    effective_timeout, metadata
                )
            else:
                async with asyncio.timeout(effective_timeout):
                    response = await litellm.acompletion(
                        model=effective_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=effective_timeout,
                        metadata=metadata,
                    )
                return response.choices[0].message.content or ""

        except asyncio.TimeoutError:
            raise LLMTimeoutError(provider=self._provider, timeout_seconds=effective_timeout)

    async def _stream(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
        metadata: dict,
    ) -> AsyncIterator[str]:
        try:
            async with asyncio.timeout(timeout):
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    timeout=timeout,
                    metadata=metadata,
                )
                async for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except asyncio.TimeoutError:
            raise LLMTimeoutError(provider=self._provider, timeout_seconds=timeout)

    async def generate_structured(
        self,
        messages: List[ChatCompletionMessageParam],
        response_format: Type[T],
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> T:
        effective_model = model or self._model
        effective_timeout = timeout or self._timeout
        metadata = self._build_metadata()

        try:
            async with asyncio.timeout(effective_timeout):
                response = await litellm.acompletion(
                    model=effective_model,
                    messages=messages,
                    response_format=response_format,
                    timeout=effective_timeout,
                    metadata=metadata,
                )
            raw = response.choices[0].message.content
            if not raw:
                raise ValueError(
                    f"LLM returned empty content for structured output "
                    f"(model={effective_model}, format={response_format.__name__})"
                )
            return response_format.model_validate_json(raw)

        except asyncio.TimeoutError:
            raise LLMTimeoutError(provider=self._provider, timeout_seconds=effective_timeout)

    def _build_metadata(self) -> dict:
        """Build per-call metadata for Langfuse trace nesting.

        Uses ``existing_trace_id`` (not ``trace_id``) so that LiteLLM's
        Langfuse callback nests generations under the already-created parent
        trace instead of creating a new top-level trace.
        """
        meta: dict = {}
        trace_id = get_trace_context()
        if trace_id:
            meta["existing_trace_id"] = trace_id
        return meta
```

### Key design decisions

1. **`BaseLLMClient` interface preserved** -- All 7 node/tool call sites remain untouched.
2. **Trace nesting via metadata** -- Each `litellm.acompletion()` call passes `metadata={"existing_trace_id": ...}` from the ContextVar. LiteLLM's Langfuse callback distinguishes between `trace_id` (creates a **new** trace) and `existing_trace_id` (nests under an **already-created** trace). We use `existing_trace_id` because the parent trace is created by the LangGraph `CallbackHandler` in `service.py`. Optionally pass `parent_observation_id` for deeper nesting. **This must be verified with a spike** -- see Compatibility Notes below.
3. **Structured outputs** -- Uses `response_format=PydanticModel` on `acompletion()`. LiteLLM passes this through to the provider. The response content is parsed with `model_validate_json()` with an explicit `None` content guard (`ValueError` raised if LLM returns empty content). **Note:** This is a behavioral change from the current `client.beta.chat.completions.parse()` which returns a pre-parsed Pydantic object. The LiteLLM approach requires manual JSON parsing. Test explicitly with each provider.
4. **Streaming** -- Returns `AsyncIterator[str]` by extracting `chunk.choices[0].delta.content`, matching the existing interface.
5. **Timeouts** -- Dual layer: `asyncio.timeout()` wrapper + LiteLLM's own `timeout` parameter.
6. **No custom provider routing needed** -- Both OpenAI and NVIDIA NIM are natively supported by LiteLLM. The model prefix (`openai/` or `nvidia_nim/`) is sufficient. LiteLLM reads API keys from standard env vars (`OPENAI_API_KEY`, `NVIDIA_NIM_API_KEY`) automatically.
7. **Langfuse callbacks** -- Set once at app startup (not per-instance) since `litellm.success_callback` is global state.

---

## Step 4: Update `config.py`

Replace per-provider API key/model fields with a unified LiteLLM configuration.

### Before

```python
default_llm_provider: Literal["openai", "zai"] = "openai"
openai_api_key: str = ""
openai_allowed_models: str = "gpt-4o-mini,gpt-4o,gpt-4-turbo"
zai_api_key: Optional[str] = None
zai_allowed_models: str = "glm-4.6,glm-4.5,glm-4-32b-0414-128k"
```

### After

```python
# LLM Configuration (LiteLLM)
default_llm_model: str = "openai/gpt-4o-mini"
allowed_llm_models: str = (
    "openai/gpt-4o-mini,openai/gpt-4o,openai/gpt-4-turbo,"
    "nvidia_nim/meta/llama-3.1-8b-instruct,"
    "nvidia_nim/meta/llama-3.1-70b-instruct,"
    "nvidia_nim/nvidia/llama-3.1-nemotron-70b-instruct"
)
litellm_fallback_models: str = ""  # Comma-separated fallback chain

# Provider API Keys (LiteLLM reads these from env automatically, but we keep them
# in Settings for validation and explicit configuration)
openai_api_key: str = ""
nvidia_nim_api_key: Optional[str] = None
nvidia_nim_api_base: Optional[str] = None  # Default: https://integrate.api.nvidia.com/v1
```

Also update or remove the helper methods (`get_allowed_models`, `get_default_model`, `validate_model`) to work with the flat model list instead of per-provider lookups.

LiteLLM reads API keys from standard env vars automatically:
- `OPENAI_API_KEY` for OpenAI models
- `NVIDIA_NIM_API_KEY` for NVIDIA NIM models
- `NVIDIA_NIM_API_BASE` optionally overrides the default NIM endpoint (`https://integrate.api.nvidia.com/v1`)

### Environment variable mapping

| Current env var | New env var | Notes |
|---|---|---|
| `DEFAULT_LLM_PROVIDER` | `DEFAULT_LLM_MODEL` | Now full model string e.g. `openai/gpt-4o-mini` |
| `OPENAI_API_KEY` | `OPENAI_API_KEY` | Unchanged, LiteLLM reads natively |
| `OPENAI_ALLOWED_MODELS` | `ALLOWED_LLM_MODELS` | Now includes provider prefix |
| `ZAI_API_KEY` | (removed) | ZAI provider dropped |
| `ZAI_ALLOWED_MODELS` | (removed) | ZAI provider dropped |
| (new) | `NVIDIA_NIM_API_KEY` | For NVIDIA NIM provider |
| (new) | `NVIDIA_NIM_API_BASE` | Optional, override NIM endpoint for self-hosted NIM |
| (new) | `LITELLM_FALLBACK_MODELS` | Optional fallback chain |

Update `.env.example` and `.env.test` accordingly.

---

## Step 5: Rewrite `factories/client_factories.py`

Remove all old client imports and the `TracedLLMClient` wrapping logic:
- Remove `from src.clients.openai_client import OpenAIClient`
- Remove `from src.clients.zai_client import ZAIClient`
- Remove `from src.clients.traced_llm_client import TracedLLMClient, LANGFUSE_AVAILABLE`
- Remove the `if LANGFUSE_AVAILABLE and settings.langfuse_enabled: return TracedLLMClient(client)` block (Langfuse is now handled via global LiteLLM callbacks set in `main.py`)
- Remove the deprecated `get_openai_client()` function (dead code, no callers)
- Add `from src.clients.litellm_client import LiteLLMClient`

```python
def get_llm_client(model: Optional[str] = None) -> BaseLLMClient:
    """Create LLM client for specified model.

    Args:
        model: LiteLLM model string (e.g. "openai/gpt-4o",
               "nvidia_nim/meta/llama-3.1-8b-instruct"). Uses default if None.

    Returns:
        LiteLLMClient instance
    """
    settings = get_settings()
    effective_model = model or settings.default_llm_model

    # Validate model against allowed list
    allowed = [m.strip() for m in settings.allowed_llm_models.split(",")]
    if effective_model not in allowed:
        # Extract provider from model string for meaningful error message
        provider = effective_model.split("/")[0] if "/" in effective_model else "unknown"
        raise InvalidModelError(
            model=effective_model, provider=provider, valid_models=allowed
        )

    timeout = float(settings.llm_call_timeout_seconds)
    return LiteLLMClient(model=effective_model, timeout=timeout)
```

Note: The `provider` parameter is removed from the function signature. The provider is now embedded in the model string (`openai/gpt-4o`). Callers that currently pass `provider` and `model` separately need updating.

### Callers of `get_llm_client()` to update

**`factories/service_factories.py`** (line 134): Currently calls `get_llm_client(provider=provider, model=model)`. Update to `get_llm_client(model=model)` where model is already in `provider/model` format.

**`factories/service_factories.py` signature**: The `get_agent_service()` function takes separate `provider` and `model` parameters. Either:
- Remove the `provider` parameter and expect `model` in `provider/model` format, or
- Keep both and combine internally: `model = f"{provider}/{model}"` if both are set.

**`routers/stream.py`**: The `StreamRequest` schema (in `schemas/stream.py`) currently has separate `provider: Literal["openai", "zai"]` and `model: str` fields. The router passes these to `get_agent_service(provider=request.provider, model=request.model)`.

**Option A (recommended for initial migration):** Keep separate fields in `StreamRequest` for backwards compatibility. Combine in `get_agent_service()`:

```python
# In service_factories.py get_agent_service():
if provider and model:
    litellm_model = f"{provider}/{model}"
elif provider:
    # Find first allowed model matching this provider
    allowed = [m.strip() for m in settings.allowed_llm_models.split(",")]
    provider_models = [m for m in allowed if m.startswith(f"{provider}/")]
    if not provider_models:
        raise InvalidProviderError(provider=provider)
    litellm_model = provider_models[0]
else:
    litellm_model = None  # Use default
llm_client = get_llm_client(model=litellm_model)
```

Update `StreamRequest.provider` type from `Literal["openai", "zai"]` to `Literal["openai", "nvidia_nim"]`.

**Option B (future):** Update `StreamRequest` schema to accept a single `model` field in LiteLLM format. Update frontend to send `"openai/gpt-4o"` instead of separate provider + model. This is a breaking frontend change and should be a follow-up PR.

---

## Step 6: Configure LiteLLM Router for fallbacks (optional, can defer)

If `litellm_fallback_models` is configured, set up LiteLLM Router:

```python
from litellm import Router

router = Router(
    model_list=[
        {"model_name": "default", "litellm_params": {"model": "openai/gpt-4o-mini"}},
        {"model_name": "default", "litellm_params": {"model": "nvidia_nim/meta/llama-3.1-70b-instruct"}},
    ],
    num_retries=2,
    fallbacks=[{"default": ["default"]}],
    retry_policy=RetryPolicy(
        TimeoutErrorRetries=2,
        RateLimitErrorRetries=3,
    ),
)
```

This is an enhancement. The basic migration works without it. Consider deferring to a follow-up PR.

---

## Step 7: Configure Langfuse callbacks at startup

Set LiteLLM's Langfuse callbacks once in `main.py` lifespan, not per-instance:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("starting application", debug=settings.debug, log_level=settings.log_level)
    await init_db()

    # Configure LiteLLM global settings
    import litellm
    import logging

    litellm.set_verbose = False
    litellm.suppress_debug_info = True
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    # Optional: litellm.drop_params = True  # silently drop unsupported params per-provider

    # Configure LiteLLM Langfuse callbacks (global, set once)
    if settings.langfuse_enabled:
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]
        log.info("litellm_langfuse_callbacks_configured")
        log.info("langfuse_enabled", host=settings.langfuse_host)

    yield

    # Shutdown
    try:
        from src.clients.langfuse_utils import shutdown_langfuse
        shutdown_langfuse()
    except Exception as e:
        log.warning("langfuse_shutdown_failed", error=str(e))

    await engine.dispose()
```

---

## Step 8: Delete removed files and clean up Z.AI references

- `clients/openai_client.py`
- `clients/zai_client.py`
- `clients/instrumented_llm_client.py` (dead code, never used by factory)
- `clients/traced_llm_client.py` (replaced by `langfuse_utils.py` + LiteLLM callbacks)

Also update remaining "Z.AI" string references:
- `main.py:105` -- features list: "Multi-provider LLM support (OpenAI, Z.AI)" -> "(OpenAI, NVIDIA NIM)"
- `routers/stream.py:47` -- docstring: same change

Update `clients/__init__.py`:

```python
from src.clients.base_llm_client import BaseLLMClient
from src.clients.litellm_client import LiteLLMClient
from src.clients.arxiv_client import ArxivClient
from src.clients.embeddings_client import JinaEmbeddingsClient

__all__ = [
    "BaseLLMClient",
    "LiteLLMClient",
    "ArxivClient",
    "JinaEmbeddingsClient",
]
```

---

## Step 9: Update tests

### Unit tests to update

| Test file | Change |
|---|---|
| `tests/unit/services/test_agent_service/test_guardrail.py` | Mock interface unchanged (`context.llm_client.generate_structured`). No changes needed. |
| `tests/unit/services/test_agent_service/test_tools.py` | Mock interface unchanged (`llm_client.generate_completion`). No changes needed. |
| `tests/api/routers/test_stream_router.py` | Update mock if it references OpenAIClient directly. |
| `tests/api/routers/conftest.py` | Remove `settings.zai_api_key = None` (line 134); add `settings.nvidia_nim_api_key = None` and update `settings.default_llm_provider` -> `settings.default_llm_model` |
| `tests/api/routers/test_health_router.py` | Remove `bad_settings.zai_api_key = None` (line 80); update to new config field names |
| Any test importing `OpenAIClient` or `ZAIClient` | Update to use `LiteLLMClient` or mock `BaseLLMClient`. |

**Note:** There are currently no unit tests for the LLM client layer (`OpenAIClient`, `ZAIClient`, `TracedLLMClient`). No existing client tests need migration, but this means there is no regression safety net. The new tests below are critical path, not optional.

### New tests to add

- `tests/unit/clients/test_litellm_client.py`: Mock `litellm.acompletion` and verify:
  - Non-streaming completion returns string
  - Streaming completion yields tokens
  - Structured output parses Pydantic model
  - Structured output raises on malformed JSON (behavioral change from `beta.chat.completions.parse`)
  - Structured output raises `ValueError` when LLM returns `None` content
  - Timeout raises `LLMTimeoutError`
  - Metadata includes `existing_trace_id` (not `trace_id`) when trace context is set
  - Provider name parsed from model string (both `openai/` and `nvidia_nim/` prefixes)
  - NVIDIA NIM models pass through to LiteLLM without custom routing

- `tests/unit/clients/test_langfuse_utils.py`: Verify singleton behavior, trace context get/set.

- Update factory tests to verify new `get_llm_client(model)` signature and provider extraction for error messages.

---

## Step 10: Update `.env.example` and `.env.test`

```env
# LLM Configuration
DEFAULT_LLM_MODEL=openai/gpt-4o-mini
ALLOWED_LLM_MODELS=openai/gpt-4o-mini,openai/gpt-4o,openai/gpt-4-turbo,nvidia_nim/meta/llama-3.1-8b-instruct,nvidia_nim/meta/llama-3.1-70b-instruct,nvidia_nim/nvidia/llama-3.1-nemotron-70b-instruct

# Provider API Keys
OPENAI_API_KEY=sk-...
# NVIDIA_NIM_API_KEY=nvapi-...
# NVIDIA_NIM_API_BASE=https://integrate.api.nvidia.com/v1  (default, override for self-hosted NIM)

# Fallbacks (optional)
# LITELLM_FALLBACK_MODELS=nvidia_nim/meta/llama-3.1-70b-instruct
```

---

## Step 11: Update frontend provider options

Update the frontend settings panel to replace ZAI with NVIDIA NIM.

### Backend schema change
- `schemas/stream.py`: `StreamRequest.provider` type from `Literal["openai", "zai"]` to `Literal["openai", "nvidia_nim"]`

### Frontend files to update

| File | Change |
|------|--------|
| `frontend/src/types/api.ts` | `LLMProvider = 'openai' \| 'zai'` -> `'openai' \| 'nvidia_nim'` |
| `frontend/src/stores/settingsStore.ts` | Update default provider/model values if ZAI is referenced |
| `frontend/src/components/chat/ChatInput.tsx` | Replace `<option value="zai">Z.AI</option>` with `<option value="nvidia_nim">NVIDIA NIM</option>` in provider selector |
| `frontend/src/hooks/useChat.ts` | `ChatOptions` uses `LLMProvider` type -- no change needed if type is updated |
| `frontend/src/components/chat/MetadataPanel.tsx` | Provider display labels -- update if ZAI-specific display logic exists |

---

## Execution Order

The steps are designed to be done in order, each building on the previous:

1. **Spike: verify Langfuse trace nesting** -- test that `litellm.acompletion(metadata={"existing_trace_id": ...})` nests under existing traces in Langfuse UI (use `existing_trace_id`, NOT `trace_id`)
2. **Add litellm dependency** -- no code changes, just verify install
3. **Create `langfuse_utils.py`** -- extract from traced_llm_client, update 3 import sites (`feedback.py`, `service.py`, `main.py`)
4. **Create `litellm_client.py`** -- new file, no custom provider routing needed since both OpenAI and NVIDIA NIM are native LiteLLM providers
5. **Update `config.py`** -- new fields alongside old ones during transition; remove ZAI fields
6. **Rewrite factory + update `service_factories.py`** -- switch from old clients to LiteLLMClient, combine provider/model in service factory
7. **Configure Langfuse callbacks at startup** -- set `litellm.success_callback = ["langfuse"]` once in `main.py` lifespan (not per-instance)
8. **Router/fallbacks** -- optional enhancement, can be a separate PR
9. **Delete old files** -- clean up after verifying everything works
10. **Update tests** -- adapt mocks, add new test file (include structured output behavioral change tests)
11. **Update env files and frontend** -- final config alignment, swap ZAI for NVIDIA NIM in frontend

Steps 3-4 can be done in parallel. Steps 5-7 should be done together. Step 9 should only happen after step 10 confirms all tests pass. Step 1 (spike) is a prerequisite for the entire migration -- if it fails, the fallback plan in Compatibility Notes applies.

---

## Compatibility Notes

### Langfuse trace hierarchy (HIGH RISK -- spike first)

**Current:** `TracedLLMClient` uses `langfuse.start_as_current_observation(as_type="generation", trace_context={"trace_id": trace_id})` -- this is the Langfuse Python SDK's context manager for explicit trace nesting. It is a well-documented, reliable mechanism.

**After:** LiteLLM's native Langfuse callback (`"langfuse"`, non-OTEL) reads metadata from each `acompletion()` call to achieve the same nesting. The `CallbackHandler` in `service.py` still creates the parent trace; individual LLM calls nest under it via metadata.

**Critical: `existing_trace_id` vs `trace_id`:** LiteLLM's Langfuse callback distinguishes between these two metadata keys:
- `metadata={"trace_id": "..."}` -- creates a **new** trace with that ID
- `metadata={"existing_trace_id": "..."}` -- nests under an **already-created** trace (does not create a new trace)

Since the parent trace is created by the LangGraph `CallbackHandler` before LLM calls happen, we **must** use `existing_trace_id`. Using `trace_id` would create competing top-level traces instead of nesting. Optionally also pass `parent_observation_id` for deeper nesting within the trace.

**Note:** Automatic detection of Langfuse `@observe()` context was requested (GitHub issue #8423) but was closed as "not planned". Metadata keys must be passed manually.

**Risk:** Whether LiteLLM's Langfuse callback correctly nests via `existing_trace_id` in practice is the highest-risk item in the migration.

**Mitigation:** Run a spike before starting implementation (see Execution Order). If LiteLLM's callback does not nest correctly, the fallback is to keep a thin wrapper that uses `langfuse.start_as_current_observation()` around each `LiteLLMClient` call, similar to the current `TracedLLMClient` but delegating to `litellm.acompletion()` instead of provider-specific clients.

**Do NOT use the `"langfuse_otel"` callback** -- it has known nesting bugs (GitHub issue #11742) where it creates separate traces instead of nesting under the parent span.

**Verify:** After migration, check Langfuse UI to confirm generations still appear nested under the graph trace, not as separate top-level traces.

### Custom Langfuse scores

`service.py:419-429` calls `langfuse.score()` directly for `guardrail_score` and `retrieval_attempts`. This is independent of the LLM client and will continue working via `langfuse_utils.get_langfuse()`.

### Feedback endpoint

`routers/feedback.py` calls `_get_langfuse()` from `traced_llm_client`. After migration, import from `langfuse_utils.get_langfuse()` instead. Behavior is identical.

### Structured outputs (behavioral change -- test explicitly)

**Current:** `OpenAIClient` and `ZAIClient` use `client.beta.chat.completions.parse(response_format=PydanticModel)`, which returns a pre-parsed Pydantic object directly via `response.choices[0].message.parsed`. The OpenAI SDK handles JSON parsing internally and has its own validation/retry logic.

**After:** `LiteLLMClient` uses `litellm.acompletion(response_format=PydanticModel)` which returns raw JSON in `response.choices[0].message.content`. We then manually parse with `response_format.model_validate_json(raw)`. This is a fundamentally different code path.

**Risks:**
- If the model returns malformed JSON, `model_validate_json()` will raise a `ValidationError` instead of the OpenAI SDK's specific error handling.
- NVIDIA NIM structured output support varies by model. Not all NIM-hosted models support `response_format` with JSON schema. Verify with each NIM model.

**Mitigation:** Add explicit tests for `generate_structured()` with each provider. Test with the actual Pydantic models used in the codebase (`GuardrailResult`, `GradingResult`, `RouterDecision`). If parsing failures are frequent, consider wrapping `model_validate_json()` with retry logic or a more descriptive error.

LiteLLM passes `response_format` through to the provider. This works for:
- **OpenAI**: Native structured outputs support
- **NVIDIA NIM**: Depends on the model; some NIM-hosted models (e.g., Llama 3.1 variants) support JSON mode but not full JSON schema. May need to fall back to prompt-based JSON extraction for models that do not support `response_format`.

If a provider does not support structured outputs, `generate_structured()` will raise an error. This is acceptable -- the `allowed_llm_models` config controls which models are available. Consider documenting which NIM models support structured outputs.

### NVIDIA NIM provider

NVIDIA NIM is natively supported by LiteLLM. No custom endpoint routing is needed (unlike the previous ZAI integration which required `_get_provider_kwargs` with `api_base` overrides).

- Models use the `nvidia_nim/` prefix (e.g., `nvidia_nim/meta/llama-3.1-8b-instruct`)
- API key is read from `NVIDIA_NIM_API_KEY` env var
- Default API base is `https://integrate.api.nvidia.com/v1`
- For self-hosted NIM instances, override via `NVIDIA_NIM_API_BASE` env var
- This simplifies `LiteLLMClient` compared to the previous plan -- no `_get_provider_kwargs()` method is needed

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| LiteLLM Langfuse callback doesn't nest traces correctly | **High** | Run spike before implementation (see Execution Order). Use `existing_trace_id` (not `trace_id`) in metadata. Use `"langfuse"` callback (not `"langfuse_otel"` which has nesting bugs). Fall back to keeping a thin wrapper using `langfuse.start_as_current_observation()` around `LiteLLMClient` calls. |
| `generate_structured` behavioral change (`model_validate_json` vs `beta.parse`) | **Medium** | Test with actual Pydantic models (`GuardrailResult`, `GradingResult`, `RouterDecision`). Add explicit error handling for `ValidationError` in `generate_structured`. |
| NVIDIA NIM models may not support structured outputs (JSON schema) | **Medium** | Test each NIM model for `response_format` support. Document supported models. Fall back to prompt-based JSON extraction if needed. |
| LiteLLM structured output inconsistencies across providers | **Medium** | LiteLLM has had bugs with `acompletion` structured outputs on non-OpenAI providers (GitHub #8060, #7561). Test `generate_structured()` with each provider explicitly. |
| `litellm.success_callback` set per-instance instead of once | **Low** (fixed) | Set in `main.py` lifespan, not in `LiteLLMClient.__init__()`. |
| LiteLLM verbose logging floods production logs | **Low** (fixed) | Set `litellm.set_verbose = False`, `litellm.suppress_debug_info = True`, and `logging.getLogger("LiteLLM").setLevel(logging.WARNING)` at startup. |
| LiteLLM adds latency overhead | **Low** | Benchmark before/after. LiteLLM is a thin wrapper; overhead should be <5ms per call. |
| Breaking change for frontend (provider/model format) | **Low** | Combine `provider` + `model` in `service_factories.py` for backwards compatibility. Migrate frontend in follow-up PR. |
