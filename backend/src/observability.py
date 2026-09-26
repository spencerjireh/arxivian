"""Tracing setup: Pydantic Logfire over OpenTelemetry.

The only module that imports `logfire`. With no `LOGFIRE_TOKEN` in the environment nothing
is exported (dev, CI); with one, every FastAPI request, SQL statement, LangGraph node,
LiteLLM call, outbound httpx call and Celery task lands in one trace, and structlog lines
attach to the active span (`utils.logger`). Prompts and paper text are sent by design.

`LOGFIRE_TOKEN` and `LOGFIRE_ENVIRONMENT` are read by the SDK itself; there is no Settings
field for them. `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` are read
by the OTel SDK inside logfire: when both are set it adds a second span exporter, after
scrubbing, so the same spans also reach the self-hosted collector. No code here changes for it.
"""

import logfire
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace

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


def current_trace_id() -> str | None:
    """The active trace id as 32 hex chars, or None outside a span.

    `utils.logger` stamps this on every log line so Grafana can jump from a Tempo span to its
    Loki lines: the Tempo datasource's `filterByTraceID` appends `|="<traceID>"` to the Loki
    query, a substring match on the raw line, so the id has to be *in* the line.
    """
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return trace.format_trace_id(span_context.trace_id)


def flush() -> None:
    """Flush pending spans (call on process shutdown)."""
    logfire.force_flush()
