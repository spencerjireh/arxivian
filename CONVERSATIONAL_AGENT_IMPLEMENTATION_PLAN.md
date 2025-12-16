# Conversational Agent with Memory - Implementation Plan

## Goal

Transform the template-based agent into a conversational LLM-driven system with multi-turn memory.

**Core Changes:**
1. Replace hardcoded responses with LLM-generated conversational messages
2. Add conversation persistence (sessions, turns)
3. Introduce `ConversationFormatter` in `AgentContext` for clean history access
4. Introduce `PromptBuilder` for composable, extensible prompt construction

**Constraints:**
- Backward compatible (session_id optional)
- No tests, rate limiting, or auth in this phase
- Temperature 0.7 for out-of-scope, 0.3 for generation
- 5-turn context window (10 messages)

---

## Architecture Overview

### Current Flow
```
Request -> Router -> AgentService -> LangGraph (nodes use AgentContext) -> Response
```

### New Components
```
AgentContext (extended)
    |-- ConversationFormatter    # Formats history for prompts
    |-- conversation_window      # Config: max turns to include

PromptBuilder                    # Composable prompt construction
    .with_conversation()
    .with_retrieval_context()
    .build() -> (system, user)

ConversationRepository           # DB persistence
    .get_or_create_conversation()
    .get_history()
    .save_turn()
```

### Data Flow (with session_id)
```
1. Router receives request with session_id
2. AgentService loads history via ConversationRepository
3. History formatted via ConversationFormatter -> AgentState
4. Nodes use PromptBuilder to include conversation context
5. After execution, turn saved to DB
6. Response includes session_id + turn_number
```

---

## Database Schema

### `conversations`
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    metadata_ JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
```

### `conversation_turns`
```sql
CREATE TABLE conversation_turns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    user_query TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    guardrail_score INTEGER,
    retrieval_attempts INTEGER DEFAULT 1,
    rewritten_query TEXT,
    sources JSONB,
    reasoning_steps JSONB,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (conversation_id, turn_number)
);
CREATE INDEX idx_conversation_turns_conversation_id ON conversation_turns(conversation_id);
```

---

## New Types

### `ConversationMessage` (schemas/conversation.py)
```python
from typing import Literal, TypedDict

class ConversationMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str
```

### `TurnData` (schemas/conversation.py)
```python
from dataclasses import dataclass

@dataclass
class TurnData:
    user_query: str
    agent_response: str
    provider: str
    model: str
    guardrail_score: int | None = None
    retrieval_attempts: int = 1
    rewritten_query: str | None = None
    sources: list[dict] | None = None
    reasoning_steps: list[str] | None = None
```

**Why:** Reduces parameter sprawl in repository methods.

---

## ConversationFormatter (context.py)

Encapsulates history formatting logic. Lives in `AgentContext` so nodes don't parse raw history.

```python
class ConversationFormatter:
    """Formats conversation history for prompt injection."""
    
    def __init__(self, max_turns: int = 3):
        self.max_turns = max_turns
    
    def format_for_prompt(self, history: list[ConversationMessage]) -> str:
        """Format recent history as prompt-ready string."""
        recent = history[-(self.max_turns * 2):]  # Last N turns
        if not recent:
            return ""
        
        lines = ["Previous conversation:"]
        for msg in recent:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content'][:500]}")
        return "\n".join(lines)
    
    def as_messages(self, history: list[ConversationMessage]) -> list[dict]:
        """Return history as LLM message format."""
        return [{"role": m["role"], "content": m["content"]} for m in history]
```

**Why:** Nodes call `context.conversation_formatter.format_for_prompt(history)` instead of implementing formatting logic themselves.

---

## PromptBuilder (prompts.py)

Composable prompt construction. New nodes can build prompts without modifying existing functions.

```python
class PromptBuilder:
    """Composable prompt builder for LLM calls."""
    
    def __init__(self, system_base: str):
        self._system = system_base
        self._user_parts: list[str] = []
    
    def with_conversation(
        self, 
        formatter: ConversationFormatter, 
        history: list[ConversationMessage]
    ) -> "PromptBuilder":
        formatted = formatter.format_for_prompt(history)
        if formatted:
            self._user_parts.append(formatted)
        return self
    
    def with_retrieval_context(self, chunks: list[dict]) -> "PromptBuilder":
        if chunks:
            context = "\n\n".join(
                f"[{c['arxiv_id']}] {c['title']}\n{c['chunk_text']}"
                for c in chunks
            )
            self._user_parts.append(f"Retrieved context:\n{context}")
        return self
    
    def with_query(self, query: str, label: str = "Question") -> "PromptBuilder":
        self._user_parts.append(f"{label}: {query}")
        return self
    
    def with_note(self, note: str) -> "PromptBuilder":
        self._user_parts.append(f"Note: {note}")
        return self
    
    def build(self) -> tuple[str, str]:
        return self._system, "\n\n".join(self._user_parts)


# System prompt constants
ANSWER_SYSTEM_PROMPT = """You are a research assistant specializing in AI/ML papers.
Answer based ONLY on provided context. Cite sources as [arxiv_id].
Be precise, technical, and conversational. Avoid robotic phrases."""

OUT_OF_SCOPE_SYSTEM_PROMPT = """You are an AI/ML research assistant.
The user's query is outside your scope. Respond helpfully:
- Explain you specialize in AI/ML research papers
- Suggest how they might rephrase for AI/ML relevance
- Be concise (2-3 sentences), professional, not over-apologetic"""
```

**Usage in nodes:**
```python
# generation.py
prompt = (
    PromptBuilder(ANSWER_SYSTEM_PROMPT)
    .with_conversation(context.conversation_formatter, history)
    .with_retrieval_context(chunks)
    .with_query(query)
    .build()
)

# out_of_scope.py
prompt = (
    PromptBuilder(OUT_OF_SCOPE_SYSTEM_PROMPT)
    .with_conversation(context.conversation_formatter, history)
    .with_query(query, label="User query")
    .with_note(f"Relevance score: {score}/100. Reason: {reasoning}")
    .build()
)
```

**Why:** 
- New nodes compose prompts without new functions in prompts.py
- Conversation formatting is consistent across all nodes
- Easy to add new context types (e.g., `.with_tool_results()`)

---

## AgentContext Updates (context.py)

```python
class AgentContext:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
        conversation_formatter: ConversationFormatter | None = None,
        guardrail_threshold: int = 75,
        top_k: int = 3,
        max_retrieval_attempts: int = 3,
        temperature: float = 0.3,
    ):
        self.llm_client = llm_client
        self.search_service = search_service
        self.conversation_formatter = conversation_formatter or ConversationFormatter()
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts
        self.temperature = temperature
```

---

## AgentState Updates (schemas/langgraph_state.py)

```python
class AgentState(TypedDict):
    # ... existing fields ...
    
    # NEW: Conversation
    conversation_history: list[ConversationMessage]  # Typed, not list[dict]
    session_id: str | None
```

---

## API Schema Updates (schemas/ask_agent.py)

### Request
```python
class AgentAskRequest(BaseModel):
    # ... existing ...
    session_id: str | None = Field(None, description="Session UUID for conversation continuity")
    conversation_window: int = Field(5, ge=1, le=10)
```

### Response
```python
class AgentAskResponse(BaseModel):
    # ... existing ...
    session_id: str | None = None
    turn_number: int = 0
    guardrail_score: int | None = None  # Changed from int
```

---

## Node Updates

### out_of_scope.py
```python
async def out_of_scope_node(state: AgentState, context: AgentContext) -> AgentState:
    guardrail = state.get("guardrail_result")
    query = state.get("original_query", "")
    history = state.get("conversation_history", [])
    
    if guardrail:
        system, user = (
            PromptBuilder(OUT_OF_SCOPE_SYSTEM_PROMPT)
            .with_conversation(context.conversation_formatter, history)
            .with_query(query, label="User query")
            .with_note(f"Score: {guardrail.score}/100. Reason: {guardrail.reasoning}")
            .build()
        )
        message = await context.llm_client.generate_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.7,
            max_tokens=300,
        )
    else:
        message = "I specialize in AI/ML research papers. How can I help with that?"
    
    state["messages"].append(AIMessage(content=message))
    return state
```

### generation.py
```python
async def generate_answer_node(state: AgentState, context: AgentContext) -> AgentState:
    query = state.get("original_query", "")
    chunks = state["relevant_chunks"][:context.top_k]
    history = state.get("conversation_history", [])
    attempts = state.get("retrieval_attempts", 1)
    
    builder = (
        PromptBuilder(ANSWER_SYSTEM_PROMPT)
        .with_conversation(context.conversation_formatter, history)
        .with_retrieval_context(chunks)
        .with_query(query)
    )
    
    if attempts >= context.max_retrieval_attempts and len(chunks) < context.top_k:
        builder.with_note("Limited sources found. Acknowledge gaps if needed.")
    
    system, user = builder.build()
    
    answer = await context.llm_client.generate_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=context.temperature,
        max_tokens=1000,
    )
    
    state["messages"].append(AIMessage(content=answer))
    state["metadata"]["reasoning_steps"].append("Generated answer with conversation context")
    return state
```

---

## Repository (repositories/conversation_repository.py)

```python
class ConversationRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def get_or_create(self, session_id: str) -> Conversation:
        conv = self.session.query(Conversation).filter_by(session_id=session_id).first()
        if not conv:
            conv = Conversation(session_id=session_id)
            self.session.add(conv)
            self.session.commit()
            self.session.refresh(conv)
        return conv
    
    def get_history(self, session_id: str, limit: int = 5) -> list[ConversationTurn]:
        conv = self.session.query(Conversation).filter_by(session_id=session_id).first()
        if not conv:
            return []
        return (
            self.session.query(ConversationTurn)
            .filter_by(conversation_id=conv.id)
            .order_by(ConversationTurn.turn_number.desc())
            .limit(limit)
            .all()
        )[::-1]  # Reverse to chronological
    
    def save_turn(self, session_id: str, turn: TurnData) -> ConversationTurn:
        conv = self.get_or_create(session_id)
        max_turn = (
            self.session.query(func.max(ConversationTurn.turn_number))
            .filter_by(conversation_id=conv.id)
            .scalar()
        )
        turn_number = (max_turn or -1) + 1
        
        ct = ConversationTurn(
            conversation_id=conv.id,
            turn_number=turn_number,
            user_query=turn.user_query,
            agent_response=turn.agent_response,
            guardrail_score=turn.guardrail_score,
            retrieval_attempts=turn.retrieval_attempts,
            rewritten_query=turn.rewritten_query,
            sources=turn.sources,
            reasoning_steps=turn.reasoning_steps,
            provider=turn.provider,
            model=turn.model,
        )
        self.session.add(ct)
        self.session.commit()
        self.session.refresh(ct)
        return ct
    
    def delete(self, session_id: str) -> bool:
        conv = self.session.query(Conversation).filter_by(session_id=session_id).first()
        if conv:
            self.session.delete(conv)
            self.session.commit()
            return True
        return False
```

---

## Service Updates (services/agent_service/service.py)

```python
class AgentService:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
        conversation_repo: ConversationRepository | None = None,
        conversation_window: int = 5,
        # ... existing params
    ):
        self.conversation_repo = conversation_repo
        self.conversation_window = conversation_window
        # ... existing
    
    async def ask(self, query: str, session_id: str | None = None) -> dict:
        # Load history if session provided
        history: list[ConversationMessage] = []
        if session_id and self.conversation_repo:
            turns = self.conversation_repo.get_history(session_id, self.conversation_window)
            for t in turns:
                history.append({"role": "user", "content": t.user_query})
                history.append({"role": "assistant", "content": t.agent_response})
        
        initial_state = {
            # ... existing fields ...
            "conversation_history": history,
            "session_id": session_id,
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        # Extract answer
        answer = result["messages"][-1].content if result["messages"] else ""
        
        # Save turn if session provided
        turn_number = 0
        if session_id and self.conversation_repo:
            turn = self.conversation_repo.save_turn(
                session_id,
                TurnData(
                    user_query=query,
                    agent_response=answer,
                    provider=self.provider,
                    model=self.model,
                    guardrail_score=result.get("guardrail_result", {}).get("score"),
                    retrieval_attempts=result.get("retrieval_attempts", 1),
                    rewritten_query=result.get("rewritten_query"),
                    sources=[...],  # Build from relevant_chunks
                    reasoning_steps=result.get("metadata", {}).get("reasoning_steps"),
                )
            )
            turn_number = turn.turn_number
        
        return {
            # ... existing ...
            "session_id": session_id,
            "turn_number": turn_number,
        }
```

---

## Extension Guide

### Adding a New Node

1. Create `nodes/my_node.py`:
```python
async def my_node(state: AgentState, context: AgentContext) -> AgentState:
    history = state.get("conversation_history", [])
    
    system, user = (
        PromptBuilder("Your system prompt here")
        .with_conversation(context.conversation_formatter, history)
        .with_query(state["original_query"])
        .build()
    )
    
    result = await context.llm_client.generate_completion(...)
    # Update state
    return state
```

2. Export in `nodes/__init__.py`
3. Register in `graph_builder.py`:
```python
workflow.add_node("my_node", create_node_wrapper(my_node, context))
```

### Adding a New Tool

1. Add factory in `tools.py`:
```python
def create_my_tool(dependency: SomeDependency):
    @tool
    async def my_tool(param: str) -> dict:
        return await dependency.do_something(param)
    return my_tool
```

2. Add to `ToolNode` in `graph_builder.py`:
```python
tools = [retrieve_tool, my_tool]
tool_node = ToolNode(tools)
```

### Adding Prompt Context Types

Extend `PromptBuilder`:
```python
def with_tool_results(self, results: list[dict]) -> "PromptBuilder":
    if results:
        formatted = "\n".join(f"- {r['tool']}: {r['output']}" for r in results)
        self._user_parts.append(f"Tool results:\n{formatted}")
    return self
```

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create `backend/src/schemas/conversation.py` (ConversationMessage, TurnData)
- [ ] Create `backend/src/models/conversation.py` (Conversation, ConversationTurn)
- [ ] Update `backend/src/models/__init__.py`
- [ ] Create migration `backend/alembic/versions/YYYYMMDD_add_conversations.py`
- [ ] Run migration

### Phase 2: Repository
- [ ] Create `backend/src/repositories/conversation_repository.py`
- [ ] Update `backend/src/repositories/__init__.py`

### Phase 3: Context & Prompts
- [ ] Add `ConversationFormatter` to `context.py`
- [ ] Add `PromptBuilder` and system prompt constants to `prompts.py`
- [ ] Remove `get_out_of_scope_message()` from `prompts.py`
- [ ] Update `AgentContext.__init__` with conversation_formatter

### Phase 4: State & Schemas
- [ ] Add ConversationMessage import to `langgraph_state.py`
- [ ] Add `conversation_history`, `session_id` to AgentState
- [ ] Update `ask_agent.py` request/response schemas

### Phase 5: Nodes
- [ ] Update `nodes/out_of_scope.py` to use PromptBuilder + LLM
- [ ] Update `nodes/generation.py` to use PromptBuilder

### Phase 6: Service Integration
- [ ] Update `AgentService.__init__` with conversation_repo, conversation_window
- [ ] Update `AgentService.ask()` with history loading/saving
- [ ] Update `service_factories.py` to create ConversationRepository

### Phase 7: Router
- [ ] Update `routers/ask_agent.py` to pass session_id, conversation_window
- [ ] Return session_id and turn_number in response

---

## Backward Compatibility

- `session_id` is optional - omitting it uses stateless mode (no DB operations)
- All new response fields have defaults
- Existing API contracts unchanged
- No frontend changes required initially

---

## Performance Notes

| Operation | Impact |
|-----------|--------|
| Stateless mode | No change |
| With session_id | +2-3 DB queries (~20-50ms) |
| Out-of-scope LLM | +1 LLM call (~500-1500ms, only for rejected queries) |
| Context tokens | +~500 tokens for 5-turn window |
