# Agent Refactor Plan: 12-Factor Agentic Architecture

## Status: IMPLEMENTED

All phases have been completed. See implementation details below.

---

## Overview

Refactor the agent service from a **static DAG** to a **dynamic tool router pattern** aligned with [12-factor agent principles](https://github.com/humanlayer/12-factor-agents). This enables:

- Dynamic tool selection by LLM (Factor 4, 8)
- Easy addition of new tools without graph changes
- Pause/resume capability (Factor 6)
- Unified state management (Factor 5)
- Future human-in-the-loop support (Factor 7)

## Goal: Flexible Free-form Conversation

The architecture should support **natural, free-form conversation** while maintaining structural guardrails:

**Flexible (LLM-driven)**:
- Router decides which tools to call based on query semantics, not hardcoded rules
- Can chain multiple tools (e.g., retrieve -> web_search -> retrieve) as needed
- Conversation history informs tool selection (understands "this", "that", follow-ups)
- Early exit if query is simple (router can skip tools and go straight to generate)
- Dynamic iterations - uses as many tool calls as needed (up to max_iterations)

**Structured (Safety guardrails)**:
- Guardrail gate filters out-of-scope queries
- Max iterations prevents infinite loops
- Tool schemas prevent hallucinated actions
- Grading validates retrieved content quality
- Typed `RouterDecision` output, not free-form text

**Example multi-turn flow**:
```
User: "I'm researching vision transformers"
  -> Router: retrieve_chunks("vision transformer ViT")
  -> Generate: overview of ViT

User: "What about for object detection?"
  -> Router sees history, retrieves detection-specific papers
  -> Generate: builds on previous context

User: "Any 2024 papers on this?"
  -> Router: web_search("vision transformer object detection 2024")
  -> Generate: recent developments
```

## Architecture Diagram

```
                    +-------------+
                    |    START    |
                    +------+------+
                           |
                    +------v------+
                    |  guardrail  |
                    +------+------+
                           |
              +------------+------------+
              |                         |
       +------v------+           +------v------+
       |   router    |           | out_of_scope|---> END
       +------+------+           +-------------+
              |
     +--------+--------+
     |                 |
+----v----+      +-----v-----+
| executor|      |  generate |---> END
+----+----+      +-----------+
     |
     +-----> (loops back to router)
```

---

## Phase 1: Core Infrastructure [COMPLETED]

### 1.1 Tool Registry & Definitions

- [x] Create `tools/` directory structure
- [x] Create `tools/registry.py` - ToolRegistry class
- [x] Create `tools/base.py` - BaseTool abstract class
- [x] Create `tools/retrieve.py` - Retrieve chunks tool (migrate from nodes)
- [x] Create `tools/web_search.py` - Generic web search tool

### 1.2 Updated State Schema

- [x] Update `schemas/langgraph_state.py` with new fields:
  - `status`: running/paused/completed/failed
  - `iteration`: current loop count
  - `max_iterations`: safety limit
  - `router_decision`: LLM's tool selection
  - `tool_history`: list of tool executions
  - `pause_reason`: for future HITL

---

## Phase 2: Router Architecture [COMPLETED]

### 2.1 New Nodes

- [x] Create `nodes/router.py` - LLM decides next tool
- [x] Create `nodes/executor.py` - Generic tool dispatcher

### 2.2 Router Prompt

- [x] Add router prompt template to `prompts.py`
- [x] Create `RouterDecision` schema for structured output

### 2.3 Edge Functions

- [x] Add `route_after_router()` to `edges.py`
- [x] Handle: execute, generate, max_iterations paths

---

## Phase 3: Graph & Service Refactor [COMPLETED]

### 3.1 Graph Builder

- [x] Rewrite `graph_builder.py` with router-based flow
- [x] Remove old static edges (retrieve -> grade -> rewrite loop)
- [x] Wire: guardrail -> router <-> executor -> generate

### 3.2 Context Updates

- [x] Update `context.py` - add ToolRegistry
- [x] Update AgentContext initialization

### 3.3 Service Updates

- [x] Update `service.py` for new graph structure
- [x] Update streaming events to use tool names
- [x] Add max_iterations parameter

---

## Phase 4: State Persistence [COMPLETED]

### 4.1 Database Migration

- [x] Create alembic migration for `agent_executions` table
- [x] Fields: id, session_id, status, state_snapshot, timestamps

### 4.2 Repository

- [x] Create `repositories/agent_execution_repository.py`
- [x] Methods: save_state, load_state, update_status

---

## Phase 5: Cleanup [COMPLETED]

### 5.1 Remove Deprecated Code

- [x] Delete `tools.py` (old LangGraph tool wrapper)
- [x] Clean up unused imports in `nodes/__init__.py`
- Note: `nodes/retrieval.py` and `nodes/rewrite.py` kept for backwards compatibility

### 5.2 Update Exports

- [x] Update `nodes/__init__.py` exports
- [x] Update `agent_service/__init__.py` exports

---

## File Changes Summary

| Action | File | Description |
|--------|------|-------------|
| NEW | `tools/__init__.py` | Tool module init |
| NEW | `tools/registry.py` | ToolRegistry class |
| NEW | `tools/base.py` | BaseTool abstract class |
| NEW | `tools/retrieve.py` | Retrieve chunks tool |
| NEW | `tools/web_search.py` | Web search tool |
| NEW | `nodes/router.py` | Router node |
| NEW | `nodes/executor.py` | Tool executor node |
| NEW | `alembic/versions/20241217_add_agent_executions.py` | State persistence |
| NEW | `repositories/agent_execution_repository.py` | Execution state repo |
| NEW | `models/agent_execution.py` | AgentExecution model |
| MODIFY | `schemas/langgraph_state.py` | Add execution state fields |
| MODIFY | `graph_builder.py` | Router-based graph |
| MODIFY | `context.py` | Add ToolRegistry |
| MODIFY | `service.py` | Update for new architecture |
| MODIFY | `prompts.py` | Add router prompt |
| MODIFY | `edges.py` | Add route_after_router |
| MODIFY | `nodes/__init__.py` | Update exports |
| MODIFY | `models/__init__.py` | Add AgentExecution |
| MODIFY | `repositories/__init__.py` | Add AgentExecutionRepository |
| DELETE | `tools.py` | Old tool wrapper (replaced by tools/) |

---

## Design Decisions

### Grading Node

**Decision**: Keep grading as a separate node (not embedded in retrieve tool).

**Rationale**: Grading is a distinct LLM operation that evaluates retrieval quality. Keeping it separate provides:
- Clear observability of grading decisions
- Ability to skip grading for certain queries
- Easier debugging of retrieval vs grading issues

### Web Search Tool

**Decision**: Generic web search using httpx with DuckDuckGo API.

**Rationale**: Keep it simple and extensible. Can be enhanced later for specific sources.

### State Persistence

**Decision**: Store full state snapshot in JSONB for pause/resume.

**Rationale**: Aligns with Factor 5 (unified state) and Factor 6 (pause/resume). Full state allows:
- Resume from any point
- Debug failed executions
- Future: fork conversations

---

## Streaming Event Updates

New mapping for streaming events:

```python
NODE_TO_STEP = {
    "guardrail": "guardrail",
    "out_of_scope": "out_of_scope",
    "router": "routing",
    "executor": "executing",
    "grade_documents": "grading",
    "generate": "generation",
}
```

Tool events are emitted via custom events:
- `tool_start`: When a tool begins execution
- `tool_end`: When a tool completes

---

## Next Steps

The following are suggested future enhancements:

1. **Human-in-the-loop**: Implement pause/resume with user confirmation for sensitive actions
2. **Additional tools**: Add more specialized tools (arxiv search, paper summarization, etc.)
3. **Tool caching**: Cache tool results to avoid redundant calls
4. **Observability**: Add metrics for router decisions and tool performance
