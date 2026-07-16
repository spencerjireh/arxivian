# Conversation Title Generation

Design doc for LLM-generated conversation titles using a blocking `gpt-4o-mini` call
after the first turn completes.

## Problem

The sidebar displays conversations by truncating `last_query` to 50 characters. This
produces titles like "What are the key differences between transformer..." -- unusable
for scanning a conversation list. Users cannot distinguish conversations at a glance.

## Solution

Generate a short, descriptive title via a single `generate_completion()` call to
`openai/gpt-4o-mini` after the first turn is saved. The title is persisted on the
`Conversation` model and picked up by the frontend through the existing query
invalidation on `GET /conversations` (the `onMetadata` handler already calls
`invalidateQueries({ queryKey: conversationKeys.lists() })`).

### Constraints

- Blocking: adds ~300-500ms after streaming ends, before the METADATA event. The user
  has already received the full answer, so the delay is imperceptible.
- First turn only: `turn_number == 0` triggers generation. Subsequent turns skip it.
- Graceful degradation: if the LLM call fails, `title` remains `NULL` and the frontend
  falls back to truncated `last_query`.
- Fixed model: always `openai/gpt-4o-mini` regardless of the agent's configured
  provider. `generate_structured` lacks a `model` override parameter, so
  `generate_completion` with an explicit model is the correct call.

## Design

### 1. Database

Add `title` column to `conversations`:

```python
# models/conversation.py
title: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

Migration (auto-generate via `alembic revision --autogenerate`):

```python
op.add_column("conversations", sa.Column("title", sa.String(200), nullable=True))
```

No backfill. Existing conversations remain `NULL` -- the frontend already handles this
with the `last_query` fallback.

### 2. Repository

Add one method to `ConversationRepository`, following the existing entity-load pattern
used by `complete_pending_turn`, `clear_pending_confirmation`, etc.:

```python
async def update_title(self, session_id: str, title: str) -> None:
    result = await self.session.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )
    conv = result.scalar_one_or_none()
    if conv:
        conv.title = title
        await self.session.flush()
```

### 3. Title Generation

A standalone async function in its own module for testability -- no need to construct a
full `AgentService` to unit test it:

```python
# services/title_service.py

from src.clients.base_llm_client import BaseLLMClient
from src.services.agent_service.prompts import TITLE_SYSTEM_PROMPT
from src.utils.logger import get_logger

log = get_logger(__name__)


async def generate_title(
    llm_client: BaseLLMClient, query: str, answer: str
) -> str | None:
    """Generate a short title for a conversation's first turn.

    Returns None on failure so the caller can degrade gracefully.
    """
    try:
        raw = await llm_client.generate_completion(
            messages=[
                {"role": "system", "content": TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            model="openai/gpt-4o-mini",
            temperature=0.5,
            max_tokens=30,
            timeout=5.0,
        )
        return raw.strip().strip('"').strip("'")[:200]
    except Exception:
        log.warning("title_generation_failed", exc_info=True)
        return None
```

The user query alone is sufficient context -- the title describes "what was asked," not
"what was answered." This halves token cost and avoids truncation heuristics on the
answer.

### 4. Wiring into `ask_stream`

In `AgentService.ask_stream()`, after `save_turn()` completes in the normal (non-HITL)
flow. Both `self.conversation_repo` and `turn_number` are already available at this
point (lines 468-470, 607):

```python
# Normal flow: save turn
if session_id and self.conversation_repo:
    turn = await self.conversation_repo.save_turn(
        session_id,
        self._build_turn_data(query, final_state, tracker),
        user_id=self.user_id,
    )
    turn_number = turn.turn_number

    # Generate title for new conversations
    if turn_number == 0:
        title = await generate_title(self.context.llm_client, query, answer)
        if title:
            await self.conversation_repo.update_title(session_id, title)
```

Where `answer` is extracted via `self._extract_answer(final_state)` (already called
inside `_build_turn_data`; hoist it to avoid double-extraction).

### 5. Prompt

Add to `services/agent_service/prompts.py` alongside the other system prompt constants:

```python
TITLE_SYSTEM_PROMPT = (
    "Generate a concise title (4-8 words) for this research conversation. "
    "Be specific to the topic. No quotes, no trailing punctuation."
)
```

### 6. Schemas

Add `title` to both `ConversationListItem` and `ConversationDetailResponse`:

```python
# schemas/conversation.py
class ConversationListItem(BaseModel):
    session_id: str
    turn_count: int
    created_at: datetime
    updated_at: datetime
    last_query: str | None = Field(None, description="Preview of last user message")
    title: str | None = None

class ConversationDetailResponse(BaseModel):
    session_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    turns: list[ConversationTurnResponse]
```

No changes to `MetadataEventData` or `schemas/stream.py`. The SSE stream does not
carry the title -- the frontend picks it up via the sidebar refetch triggered by
query invalidation.

**Frontend** -- mirror in `types/api.ts`:

```typescript
interface ConversationListItem {
  ...
  title?: string
}

interface ConversationDetailResponse {
  ...
  title?: string
}
```

### 7. Router

In `list_conversations()`, read `title` from the model (already loaded via
`selectinload`):

```python
items.append(
    ConversationListItem(
        ...
        title=conv.title,
        last_query=last_query,
    )
)
```

In `get_conversation()`, pass `title` through to the detail response:

```python
return ConversationDetailResponse(
    session_id=conv.session_id,
    title=conv.title,
    ...
)
```

No new endpoint. The existing `GET /conversations` and `GET /conversations/{session_id}`
return the title alongside `last_query`.

### 8. Frontend

**`SidebarConversationItem.tsx`** -- prefer `title` over `last_query`:

```tsx
<p className={...}>
  {conversation.title || truncate(conversation.last_query ?? '', 50) || 'New conversation'}
</p>
```

An LLM-generated title (4-8 words) will rarely exceed 50 characters, so truncation
is effectively a no-op safety net.

**`useChat.ts`** -- no changes. The `onMetadata` handler already calls
`queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })`. The sidebar
refetches and picks up the new title automatically.

## Files Changed

| File | Change |
|------|--------|
| `models/conversation.py` | Add `title` column |
| `alembic/versions/...` | Auto-generated migration |
| `repositories/conversation_repository.py` | Add `update_title()` |
| `services/title_service.py` | New: `generate_title()` standalone function |
| `services/agent_service/prompts.py` | Add `TITLE_SYSTEM_PROMPT` constant |
| `services/agent_service/service.py` | Wire `generate_title` + `update_title` into `ask_stream` |
| `schemas/conversation.py` | Add `title` to `ConversationListItem` and `ConversationDetailResponse` |
| `routers/conversations.py` | Pass `conv.title` in list and detail responses |
| `frontend/src/types/api.ts` | Add `title?` to list and detail interfaces |
| `frontend/src/components/sidebar/SidebarConversationItem.tsx` | Display `title` with fallback |

## Testing Strategy

### Unit Tests

- **`test_generate_title`**: Mock `generate_completion`, verify title is returned,
  stripped, and truncated to 200 chars. Function takes `(llm_client, query, answer)` --
  no `AgentService` construction needed.
- **`test_generate_title_failure`**: Mock `generate_completion` to raise. Verify
  `generate_title` returns `None`, no exception propagated.
- **`test_generate_title_strips_quotes`**: Verify leading/trailing quotes and whitespace
  are removed.
- **`test_ask_stream_generates_title_on_first_turn`**: Mock the full `ask_stream` flow
  with `turn_number == 0`. Verify `update_title` is called on the conversation repo.
- **`test_ask_stream_skips_title_on_subsequent_turns`**: Mock with `turn_number > 0`.
  Verify `generate_title` is not called.
- **`test_update_title_repository`**: Verify `update_title` loads the entity, sets the
  attribute, and flushes.

### Integration Tests

- Full `ask_stream` with a real (test) database. Verify `conversations.title` is
  populated after the first turn. Verify the `GET /conversations` response includes
  the title. Verify `GET /conversations/{session_id}` includes the title.

## Open Questions

1. **Rename endpoint**: Should a `PATCH /conversations/{session_id}` be added for manual
   title editing? Not in scope for v1, but the `title` column supports it trivially.
2. **Re-titling**: If the conversation pivots topic significantly, should the title
   update? Current design: no. The first-turn title persists. Revisit if users report
   stale titles.
