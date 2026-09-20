"""Tracing setup: Pydantic Logfire over OpenTelemetry.

The only module that imports `logfire`. With no `LOGFIRE_TOKEN` in the environment nothing
is exported (dev, CI); with one, every FastAPI request, SQL statement, LangGraph node,
LiteLLM call, outbound httpx call and Celery task lands in one trace, and structlog lines
attach to the active span (`utils.logger`). Prompts and paper text are sent by design.

`LOGFIRE_TOKEN` and `LOGFIRE_ENVIRONMENT` are read by the SDK itself; there is no Settings
field for them.
"""

import logfire
from openinference.instrumentation.langchain import LangChainInstrumentor

_configured = False


def configure_tracing(service_name: str) -> None:
    """Configure the exporter and the process-wide instrumentors. Idempotent."""
    global _configured
    if _configured:
        return
    logfire.configure(
        send_to_logfire="if-token-present",
        service_name=service_name,
        console=False,  # structlog owns the console
        inspect_arguments=False,  # span messages are plain strings; skip source introspection
    )
    logfire.instrument_litellm()
    logfire.instrument_httpx()
    LangChainInstrumentor().instrument()
    _configured = True


def flush() -> None:
    """Flush pending spans (call on process shutdown)."""
    logfire.force_flush()
