"""Stream consumption utilities for integration evals."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.schemas.stream import (
    StreamEvent,
    StreamEventType,
    SourcesEventData,
    MetadataEventData,
    ErrorEventData,
)
from src.services.agent_service import AgentService


@dataclass
class StreamResult:
    """Collected output from a single ask_stream() call."""

    events: list[StreamEvent] = field(default_factory=list)
    status_events: list[StreamEvent] = field(default_factory=list)
    content_tokens: list[str] = field(default_factory=list)
    sources_event: StreamEvent | None = None
    metadata_event: StreamEvent | None = None
    done_event: StreamEvent | None = None
    error_events: list[StreamEvent] = field(default_factory=list)

    @property
    def answer(self) -> str:
        return "".join(self.content_tokens)

    @property
    def event_types(self) -> list[str]:
        return [e.event.value for e in self.events]

    @property
    def source_arxiv_ids(self) -> list[str]:
        if self.sources_event is None:
            return []
        data = self.sources_event.data
        if isinstance(data, SourcesEventData):
            return [s.arxiv_id for s in data.sources]
        return []

    @property
    def session_id(self) -> str | None:
        if self.metadata_event is None:
            return None
        data = self.metadata_event.data
        if isinstance(data, MetadataEventData):
            return data.session_id
        return None


async def consume_stream(
    agent_service: AgentService,
    query: str,
    session_id: str | None = None,
) -> StreamResult:
    """Consume all events from ask_stream() into a StreamResult."""
    result = StreamResult()
    async for event in agent_service.ask_stream(query, session_id=session_id):
        result.events.append(event)

        if event.event == StreamEventType.STATUS:
            result.status_events.append(event)
        elif event.event == StreamEventType.CONTENT:
            token = event.data.token if hasattr(event.data, "token") else ""
            result.content_tokens.append(token)
        elif event.event == StreamEventType.SOURCES:
            result.sources_event = event
        elif event.event == StreamEventType.METADATA:
            result.metadata_event = event
        elif event.event == StreamEventType.DONE:
            result.done_event = event
        elif event.event == StreamEventType.ERROR:
            result.error_events.append(event)

    return result
