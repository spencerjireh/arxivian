# Arxivian Agent Architecture -- Interview Study Guide

---

## Table of Contents

1. [The Problem Statement](#1-the-problem-statement)
2. [30-Second Elevator Pitch](#2-30-second-elevator-pitch)
3. [Architecture Overview](#3-architecture-overview)
4. [Graph Topology](#4-graph-topology)
5. [Node-by-Node Breakdown](#5-node-by-node-breakdown)
6. [Tools](#6-tools)
7. [The Retry / Grading Loop](#7-the-retry--grading-loop)
8. [Human-in-the-Loop (HITL)](#8-human-in-the-loop-hitl)
9. [SSE Streaming](#9-sse-streaming)
10. [Key Design Decisions and Tradeoffs](#10-key-design-decisions-and-tradeoffs)
11. [Safety and Guardrails](#11-safety-and-guardrails)
12. [Operational Details](#12-operational-details)
13. [Anticipated Interview Questions](#13-anticipated-interview-questions)
14. [Quick Reference: File Locations](#14-quick-reference-file-locations)
15. [The Two-Graph System (Feed Pivot)](#15-the-two-graph-system-feed-pivot)

---

## 1. The Problem Statement

Always lead with the problem, not the implementation.

> "We needed a system where users could ask questions about academic papers,
> and the system would retrieve relevant content, assess whether it had enough
> information, and if not, autonomously refine its search -- all while streaming
> results back in real-time."

This frames everything that follows. The interviewer now understands *why* you
built what you built.

---

## 2. 30-Second Elevator Pitch

Memorize this. Use it for the "tell me about your project" opener.

> "I built a conversational RAG agent for academic paper analysis. The core is
> a LangGraph state machine that classifies queries, executes tools in parallel,
> evaluates retrieval quality, and autonomously rewrites queries if the results
> are insufficient -- bounded by iteration limits and stagnation detection. It
> supports human-in-the-loop paper ingestion via graph checkpointing, streams
> results over SSE with structured event types, and has multi-layer prompt
> injection defense. The whole thing runs as a single compiled graph shared
> across requests, with per-request context injected through LangGraph's config
> system."

---

## 3. Architecture Overview

Explain in three layers, from high-level to detail.

### Layer 1: The Graph (what it is)

A LangGraph `StateGraph` compiled once at startup, shared across all requests.
Per-request context (LLM client, services, user config) is passed via
`RunnableConfig["configurable"]["context"]` as an `AgentContext` object.

### Layer 2: The Design Decisions (why you made the choices)

This is where you differentiate yourself. See [Section 10](#10-key-design-decisions-and-tradeoffs).

### Layer 3: Operational Details (only if asked)

Stagnation detection, tool dedup, prompt injection layers, tier gating.
See [Section 12](#12-operational-details).

---

## 4. Graph Topology

Draw this on a whiteboard if possible. The loop is the most interesting part.

```
START --> classify_and_route --+--> out_of_scope --> END
                               |
                               +--> executor --+--> confirm_ingest --> classify_and_route
                               |               |
                               |               +--> evaluate_batch --+--> generate --> END
                               |               |                     |
                               |               +--> classify_and_route (re-loop)
                               |
                               +--> evaluate_batch (safety net)
                               |
                               +--> generate --> END
```

**6 nodes.** Connected by **3 conditional edge functions:**

| Edge Function          | After Node           | Possible Targets                                       |
|------------------------|----------------------|--------------------------------------------------------|
| `route_after_classify` | classify_and_route   | out_of_scope, executor, evaluate_batch, generate       |
| `route_after_executor` | executor             | confirm_ingest, evaluate_batch, classify_and_route     |
| `route_after_eval`     | evaluate_batch       | generate, classify_and_route                           |

---

## 5. Node-by-Node Breakdown

### 5.1 classify_and_route (the brain)

The merged guardrail + router. Single LLM call returning structured output.

**Four layers, evaluated in order:**

| Layer | What It Does | Skips LLM? |
|-------|-------------|------------|
| 1. Injection scan | Regex detection against 12 patterns | Yes (flags only) |
| 2. Fast-path | Short follow-ups ("yes", "explain more") reuse prior classification | Yes |
| 3. Max-iterations guard | Forces direct generation if `iteration > max_iterations` | Yes |
| 4. LLM classification | Structured output: intent, scope_score, tool_calls, reasoning | No |

**Post-LLM dedup guard:** Prevents re-calling tools that already succeeded.
- `extends_chunks` tools (retrieve): blocked only on exact argument match
- One-shot tools (arxiv_search, list_papers): any repeat blocked
- If all tools are duplicates: forces `intent="direct"`

**Output:** `ClassificationResult` with:
- `intent`: out_of_scope / direct / execute
- `scope_score`: 0-100
- `tool_calls`: list of `ToolCall`
- `reasoning`: string

### 5.2 executor (parallel tool runner)

Runs all selected tool calls in parallel via `asyncio.gather`.

For each tool:
1. Parse `tool_args_json`
2. Emit `tool_start` stream event
3. Execute via `ToolRegistry.execute()`
4. Emit `tool_end` stream event
5. Record a `ToolExecution` in `tool_history`

**Result routing based on tool flags:**
- `extends_chunks=True` --> results go to `retrieved_chunks`
- `extends_chunks=False` --> results go to `tool_outputs`
- `sets_pause=True` --> sets `pause_reason` and `pause_data` for HITL

### 5.3 evaluate_batch (chunk quality assessment)

Single LLM call to assess all retrieved chunks at once.

**Key behaviors:**
- **Stagnation detection:** Computes chunk fingerprints (arxiv_id + first 100 chars).
  If identical to previous iteration, short-circuits with `sufficient=True`.
- **Empty chunks:** Returns `sufficient=False` without an LLM call.
- **Sufficient:** Promotes all retrieved chunks to `relevant_chunks`.
- **Insufficient + iterations remain:** Sets `rewritten_query` for retry loop.
- **Insufficient + max iterations:** Promotes all chunks as best-effort.

**Output:** `BatchEvaluation` with:
- `sufficient`: bool
- `reasoning`: string
- `suggested_rewrite`: optional string

### 5.4 generate (answer streaming)

Streams the final answer token-by-token via `get_stream_writer()`.

Prompt composed by `PromptBuilder` from:
- System prompt (sourcing tiers, hallucination guard, LaTeX/math rules)
- Relevant chunks (top-k with arxiv_id, title, section, content)
- Non-retrieve tool outputs (arxiv_search, list_papers, etc.)
- Conversation history
- User query
- Optional note if evaluation found insufficient coverage

### 5.5 out_of_scope (rejection)

Generates a warm 2-3 sentence rejection via streaming. Suggests relevant
academic angles. Uses scope_score and reasoning from classification.

### 5.6 confirm_ingest (HITL interrupt)

Calls LangGraph's `interrupt(pause_data)` to checkpoint state and suspend
execution. When resumed via `Command(resume=value)`, processes the user's
decision (approved or declined). Always routes back to `classify_and_route`.

---

## 6. Tools

All extend `BaseTool` ABC. Two key class flags: `extends_chunks` and `sets_pause`.

| Tool | Purpose | `extends_chunks` | `sets_pause` |
|------|---------|:-:|:-:|
| `retrieve_chunks` | Hybrid vector + full-text search with RRF fusion | Yes | No |
| `arxiv_search` | Search arXiv API for paper metadata (no download) | No | No |
| `propose_ingest` | Propose papers for user-confirmed ingestion | No | Yes |
| `list_papers` | Browse the local knowledge base | No | No |
| `explore_citations` | Extract reference graph from an ingested paper | No | No |

**Tier gating:** Tools are conditionally registered based on user tier (free/pro).
The LLM never sees tool schemas for unavailable tools, so it cannot attempt to
call them.

---

## 7. The Retry / Grading Loop

This is the core RAG loop. Emphasize it in the interview.

```
classify_and_route
       |
       v
   executor (retrieve_chunks)
       |
       v
  evaluate_batch
       |
   sufficient? ----YES----> generate --> END
       |
      NO
       |
   rewrite query
       |
       v
  classify_and_route (loop back)
```

**Three safeguards against infinite loops:**

1. **max_iterations** (default 5): Hard cap checked at classify_and_route
2. **Stagnation detection**: Chunk fingerprinting at evaluate_batch -- if same
   chunks come back, break the loop
3. **Tool dedup guard**: Prevents re-calling tools with identical arguments

---

## 8. Human-in-the-Loop (HITL)

Paper ingestion uses a **two-stream pattern**:

### Stream 1: ask_stream

```
User asks "find papers about X and add them"
  --> classify_and_route selects [arxiv_search, propose_ingest]
  --> executor runs arxiv_search, then propose_ingest
  --> propose_ingest sets pause_data (sets_pause=True)
  --> confirm_ingest node calls interrupt()
  --> Graph state is checkpointed
  --> SSE emits CONFIRM_INGEST event with paper details
  --> Partial turn saved with pending_confirmation flag
```

### Stream 2: resume_stream

```
User sends approval (selected paper IDs)
  --> Service validates pending turn exists (double-confirm guard)
  --> Runs inline ingestion if approved
  --> Resumes graph via Command(resume=value)
  --> Generates follow-up response
  --> Saves new conversation turn
  --> Clears pending_confirmation
```

**Edge case:** If the LangGraph checkpoint has expired between streams, the
service catches the error, clears the pending confirmation, and emits a
`CHECKPOINT_EXPIRED` error event.

---

## 9. SSE Streaming

**Endpoint:** `POST /stream`

**9 event types:**

| Event | Purpose |
|-------|---------|
| `status` | Workflow step progress (classifying, executing, evaluating, generating) |
| `content` | Streamed answer tokens |
| `sources` | Retrieved document sources (emitted after evaluation, before generation) |
| `metadata` | Final execution stats (time, model, session, trace_id, reasoning_steps) |
| `error` | Error with message and code |
| `done` | Sentinel: stream complete |
| `citations` | Citation graph from explore_citations |
| `confirm_ingest` | HITL: papers proposed for user confirmation |
| `ingest_complete` | HITL: ingestion finished |

**Streaming mechanism:** `graph.astream()` with `stream_mode=["updates", "custom"]`

- **Custom events** (via `get_stream_writer()`): tokens, tool lifecycle, citations
- **Update events** (after each node): step tracking, source emission, interrupt detection

**Wire format:**
```
event: content
data: {"text": "The paper discusses..."}

event: status
data: {"step": "evaluating", "message": "Assessing retrieval quality"}
```

---

## 10. Key Design Decisions and Tradeoffs

Pick 2-3 of these to discuss. Lead with the tradeoff, not just the feature.

### 10.1 Merged Guardrail + Router

**What:** Combined scope assessment and tool selection into one LLM call.

**Why:** Originally two sequential calls. Merging cut latency by ~40%.

**Tradeoff:** More complex prompt, but since understanding intent and selecting
tools are related tasks, the LLM handles both well in one pass.

### 10.2 Single-Call Batch Evaluation

**What:** One LLM call to assess all chunks instead of N calls for N chunks.

**Why:** Cheaper, faster, and allows holistic reasoning about coverage
("do these chunks *together* answer the question?").

**Tradeoff:** Less granular per-chunk filtering. In practice, retrieval quality
was high enough that this didn't matter.

### 10.3 HITL via Graph Checkpointing

**What:** LangGraph's `interrupt()` to pause/resume the graph across two SSE
streams.

**Why:** Clean separation of concerns. The agent proposes, the user decides,
the agent continues from where it left off.

**Tradeoff:** Two separate SSE streams for one logical interaction adds state
management complexity (pending confirmation tracking, checkpoint expiration).

### 10.4 Single Compiled Graph, Injected Context

**What:** One compiled `StateGraph` instance shared across all requests.
Per-request state passed via `RunnableConfig`.

**Why:** Graph compilation is expensive. Sharing it avoids redundant work.

**Tradeoff:** Must be careful that no mutable state leaks between requests.
`AgentContext` is created fresh per request.

### 10.5 Tier-Gated Tool Schemas

**What:** Tools are conditionally registered based on user tier. The LLM never
sees schemas for unavailable tools.

**Why:** More reliable than post-hoc blocking. If the LLM doesn't know a tool
exists, it can't try to call it.

**Tradeoff:** Different tool registries per tier means slightly more complex
context setup.

---

## 11. Safety and Guardrails

Three layers of prompt injection defense:

| Layer | Mechanism | Location |
|-------|-----------|----------|
| 1. Regex scanning | 12 compiled patterns (e.g. "ignore previous instructions") | `security.py` |
| 2. Context sandboxing | User messages truncated to 200 chars, wrapped in `[CONTEXT]` markers | `ConversationFormatter` |
| 3. LLM-level instructions | Classification prompt: "ONLY evaluate the Current message section" | `prompts.py` |

**Scope scoring:** Configurable `guardrail_threshold` (default 75). Queries
scoring below are routed to `out_of_scope`.

---

## 12. Operational Details

Have these ready but don't volunteer them unless asked.

- **Stagnation detection:** Chunk fingerprints (arxiv_id + first 100 chars)
  compared across iterations to break rewrite loops returning identical results
- **Tool deduplication:** Post-LLM guard filters out already-succeeded tools;
  `extends_chunks` tools only blocked on exact arg match, one-shot tools
  blocked on any repeat
- **Langfuse observability:** Callback handlers on every graph run; scores
  (`guardrail_score`, `retrieval_attempts`) submitted for analytics; `trace_id`
  propagated to frontend for user feedback
- **Conversation title generation:** First turn triggers a separate LLM call
  to generate a 4-8 word title
- **PromptBuilder pattern:** Composable builder chaining
  `.with_conversation()`, `.with_retrieval_context()`, `.with_tool_outputs()`,
  `.with_query()`, `.build()` for modular prompt construction
- **Tool output formatting:** Tools set `prompt_text` on `ToolResult` for
  compact LLM-friendly representations, keeping generation prompts concise

---

## 13. Anticipated Interview Questions

### "Why LangGraph instead of a simple chain?"

> Because we need conditional routing, loops, and checkpointing for HITL. A
> linear chain can't do the retry loop or the interrupt/resume pattern. LangGraph
> gives us a state machine with built-in persistence and streaming support.

### "How do you prevent infinite loops?"

> Three mechanisms: (1) max_iterations hard cap at classify_and_route, (2)
> stagnation detection via chunk fingerprinting at evaluate_batch, (3) tool
> dedup guards that prevent re-calling succeeded tools with identical arguments.

### "How do you handle failures mid-stream?"

> The SSE generator wraps execution in `asyncio.timeout`, checks
> `is_disconnected()` per event, and emits structured error events. Partial
> turns are saved for recovery. The task registry supports external cancellation.

### "Why not per-chunk grading?"

> We tried it. N LLM calls for N chunks was slow and expensive. Batch
> evaluation is a single call that reasons about coverage holistically -- "do
> these chunks together answer the question?" The tradeoff is less granular
> filtering, but retrieval quality was high enough that it didn't matter.

### "How does the HITL flow handle checkpoint expiration?"

> If the user takes too long to respond and the LangGraph checkpoint expires,
> we catch the error, clear the pending confirmation from the conversation turn,
> and emit a `CHECKPOINT_EXPIRED` error event so the frontend can inform the
> user.

### "How do you handle prompt injection?"

> Three layers: regex scanning against 12 known patterns, context sandboxing
> that truncates and wraps prior user messages so they can't be followed as
> instructions, and explicit LLM-level instructions in the classification
> prompt to only evaluate the current message.

### "Why share one compiled graph across requests?"

> Graph compilation is expensive -- it validates the topology, builds the
> execution plan, etc. We compile once at startup and inject per-request
> context (LLM client, services, user config) through LangGraph's
> `RunnableConfig`. We create a fresh `AgentContext` per request to avoid
> state leakage.

---

## 14. Quick Reference: File Locations

```
backend/src/services/agent_service/
    context.py              # AgentContext + ConversationFormatter
    edges.py                # Conditional routing functions
    graph_builder.py        # LangGraph StateGraph construction
    prompts.py              # All prompt templates + PromptBuilder
    security.py             # Prompt injection scanner
    service.py              # AgentService (SSE orchestration, HITL, persistence)

    nodes/
        classify_and_route.py   # Merged guardrail + router
        confirm_ingest.py       # HITL interrupt point
        evaluate_batch.py       # Batch chunk evaluation
        executor.py             # Parallel tool execution
        generation.py           # Final answer generation with streaming
        out_of_scope.py         # Off-topic response

    tools/
        base.py                 # BaseTool ABC + ToolResult
        registry.py             # ToolRegistry
        retrieve.py             # RetrieveChunksTool
        arxiv_search.py         # ArxivSearchTool
        ingest.py               # IngestPapersTool
        propose_ingest.py       # ProposeIngestTool
        list_papers.py          # ListPapersTool
        explore_citations.py    # ExploreCitationsTool

backend/src/schemas/
    langgraph_state.py      # AgentState TypedDict
    stream.py               # SSE event types and data models

backend/src/routers/
    stream.py               # POST /stream endpoint
```

---

## 15. The Two-Graph System (Feed Pivot)

Everything above describes the **chat Q&A graph**. The feed pivot (see
`docs/product/feed-prd.md` and `docs/design/scoring-pipeline.md`) adds a **second
LangGraph workflow** that reuses the same scaffolding but serves a different purpose.

**Graph A -- chat Q&A (this document).** Agentic tool-selection loop with a grading/retry
loop, HITL, and SSE streaming. Under the pivot it becomes the **scoped per-paper chat**
panel on paper detail -- same graph, narrowed context, no global chat tab.

**Graph B -- paper scoring.** A *fixed* fan-out/fan-in DAG (no LLM tool-selection), so it
is deterministic and eval-friendly:

```
START -> fetch_and_extract
      -> [fan-out (v1): score_method_clarity | score_resource_feasibility
                 | score_data_availability | score_demand]   (parallel, distinct state keys)
      -> [fan-in] compose_and_persist -> END
         (v1.1 adds a 5th parallel node, score_code_gap)
```

Key contrasts to the chat graph:
- No `get_stream_writer` / `stream_mode="custom"` (no token streaming) and **no
  checkpointer** (no HITL interrupts).
- Parallel dimension nodes each write a distinct `PaperScoreState` key, so last-write-wins
  never collides -- no reducers.
- Only 2 of the 4 v1 dimensions are LLM calls (method clarity, resource feasibility, on a
  stronger model via an explicit `model=` override); the rest are extraction / external-API
  lookups. **Code gap (GitHub search) is deferred to v1.1** -- highest-weighted but riskiest
  signal, gated on the `spikes/github-code-gap/` recall spike; v1 has no GitHub dependency.

**Shared reuse.** Both graphs are compiled once in `main.py` lifespan. The
`semantic_scholar` tool (v1; `github_search` in v1.1) subclasses the same `BaseTool` and
registers in the same `ToolRegistry`, so the scoped chat agent can call it too ("how cited
is this paper?"; "is there code for this?" once v1.1 lands). This "two graphs, one toolset"
story is the strongest part of the pivot's architecture narrative.

*Note: Graph B and its tools/clients are a design blueprint (`scoring-pipeline.md`), not
yet implemented.*
