# Proposal: Pivoting Arxivian from Chat-First RAG to an Implementation-Opportunity Feed

**Status:** Draft for review
**Author:** Spencer Jireh
**Date:** July 2026
**Affects:** arxivian (production)

---

## 1. Summary

Arxivian today is an agentic RAG system: users chat with an AI agent that searches, ingests, and answers questions about arXiv papers. This proposal pivots the product into a **ranked discovery feed of papers worth turning into software implementations**. The core artifact shifts from a conversation to a scored **paper card**, surfaced in a weekly digest. Chat is retained but demoted to a contextual, per-paper feature.

The pivot preserves the majority of the existing production system — ingestion pipeline, hybrid retrieval, LangGraph agent, communal knowledge base, auth, and eval infrastructure — while replacing the primary interface and adding a scoring pipeline as the new backbone.

## 2. Motivation

Three converging observations drive this change.

First, **chat-with-papers is now a commodity.** General-purpose chatbots with web search and file upload cover most of arxivian's current value proposition. Competing on that surface means competing with frontier assistants on their home turf, with no structural advantage.

Second, **there is an unfilled gap in implementation-oriented paper discovery.** Papers with Code — the de facto index linking papers to implementations — was shut down by Meta in mid-2025. Existing alternatives (Hugging Face papers, alphaXiv, arxiv-sanity derivatives) rank by popularity or personal relevance, not by *implementability*. No tool answers the question: "which papers published this week describe a method that is valuable, feasible for an individual to implement, and has no existing code?"

Third, **the pivot has a flywheel the current product lacks.** The app surfaces a paper; the user implements it; the published repo is both a portfolio artifact and public proof the ranking works. Each shipped implementation strengthens the case for the product itself. A chat app produces no comparable public artifact.

## 3. Goals and Non-Goals

### Goals (v1)

1. A scoring pipeline that triages new arXiv submissions in configured categories and produces an implementability score with evidence-backed sub-scores.
2. A feed UI presenting a weekly ranked digest of paper cards, triageable without opening details.
3. A paper detail page showing the transparent score breakdown, with scoped chat as a secondary panel.
4. Paper lifecycle states per user: saved → implementing → shipped (with repo link).
5. Zero regression to the production deployment: auth, user data, and the communal knowledge base carry forward.

### Non-Goals (v1)

- Automated implementation generation (paper-to-code agents). The product finds and scopes opportunities; the human implements.
- Social/community features (comments, shared feeds, leaderboards).
- Signals beyond GitHub and Semantic Scholar (Hugging Face discussions, X/Bluesky chatter) — deferred.
- Email digests and notifications — deferred.
- Implementation-notes generation for shipped papers — deferred, but the data model should not preclude it.

## 4. Product Design

### 4.1 The core object: the paper card

The primary unit of the product changes from a conversation to a **paper card**. A card must answer "why should I care?" in roughly two seconds. Its anatomy:

| Element | Content |
|---|---|
| Title + meta | Paper title, authors, category, submission date |
| Verdict line | One LLM-generated sentence, e.g. "Novel KV-cache eviction method, no official code, single-GPU feasible" |
| Score badge | Composite implementability score; visually secondary to the verdict |
| Signal chips | "No code found" / "Pseudocode present" / "Public datasets" / "1 GPU" |
| Actions | Save, Dismiss, Mark as Implementing |

### 4.2 Screens and user flow

**Onboarding (new, one-time).** After sign-in: select arXiv categories, declare compute reality (laptop / single GPU / cloud budget), optional interest keywords. Roughly thirty seconds; stored on the existing user model. This makes the first feed personal rather than generic.

**Home = Feed.** A ranked list of cards for the current week with a filter bar (category, minimum score, "no existing code only") and a week selector for browsing past digests. Past weeks are pre-scored and cached, so historical browsing is free. The feed must be fully triageable from cards alone; dismiss is a single action with no confirmation.

**Paper detail.** The deep-dive surface, replacing chat in that role. Top: the score breakdown, where each sub-score is accompanied by quoted evidence extracted from the paper (the pseudocode block found, the compute requirements mentioned, GitHub search results for existing implementations). Bottom or slide-over: **scoped chat**, pre-loaded with the paper's ingested content, seeded with suggested prompts ("Explain the core method," "What would a minimal repo look like," "What are the risky parts to reproduce"). The existing streaming and citation UI transfers here with a narrowed context.

**Library.** Saved and in-progress papers grouped by lifecycle state. This is the return-visit surface: the feed serves discovery; the library serves ongoing projects. Shipped items display the linked repository.

### 4.3 What is removed

- The global chat tab and conversation-history list are removed entirely.
- User-initiated ingestion ("ingest this paper" as a chat action) disappears. Ingestion becomes invisible background work: the pipeline ingests scored papers automatically, and opening a paper detail triggers ingestion on demand if needed. Users no longer manage the corpus.

### 4.4 Interaction rhythm

The product moves from a session tool (come with a question, stay ten minutes) to a **weekly ritual**: the digest lands after arXiv's weekend backlog clears, the user triages cards in about five minutes, saves a couple, dismisses the rest, and optionally goes deep on one. The design optimizes for this cadence — a bounded weekly digest rather than an infinite feed. This both matches arXiv's publishing rhythm and caps scoring compute.

### 4.5 Trust as a design constraint

The failure mode of every AI paper feed is false authority: a confidently wrong score destroys trust faster than no score at all. Two mitigations are built into the design. The verdict line and evidence-quoting breakdown are visually primary; the numeric score is secondary. And every sub-score is auditable — the user can see exactly which passage or search result produced it.

## 5. High-Level System Design

### 5.1 Scoring pipeline (new backbone)

A two-stage triage, implemented as Celery tasks on the existing broker, scheduled via Celery Beat.

**Stage 1 — cheap filter.** Runs on title + abstract only, using a small model via the existing LiteLLM routing. Classifies each paper as method / survey / benchmark / theory / position, and estimates rough implementability. Expected to eliminate 70–80% of the 500–800 daily submissions in target categories at negligible cost.

**Stage 2 — deep scoring.** For survivors: fetch full text, run extraction and scoring against the rubric below, cross-check external signals. Results (sub-scores plus extracted evidence spans) are persisted to Postgres.

**Rubric (v1):**

| Dimension | Weight | Signal source |
|---|---|---|
| Code gap | Highest | GitHub code/README search for title and arXiv ID; existing repos' stars and issue health |
| Method clarity | High | Presence of pseudocode/algorithm blocks, stated hyperparameters, fully specified architecture (LLM-judged from full text) |
| Resource feasibility | High | Compute requirements extracted from the paper, matched against user compute profile |
| Data availability | Gate | Public datasets vs. proprietary/clinical data; disqualifying if inaccessible |
| Demand | Medium | Citation velocity via Semantic Scholar API |

**Design rule: store evidence, not just numbers.** Sub-scores and their supporting extracted spans are first-class records. This makes the UI breakdown trustworthy and, critically, makes the rubric tunable: reweighting is arithmetic over stored sub-scores and never requires re-running extraction.

### 5.2 Architecture: what transfers, what changes

| Component | Disposition |
|---|---|
| arXiv ingestion + Celery/Beat/Redis | Transfers; extended with scheduled category crawls and the two scoring queues |
| Hybrid retrieval (pgvector HNSW + GIN/tsvector, RRF) | Transfers; repurposed for dedup and similar-paper / prior-implementation checks |
| LangGraph agent | Refactored: triage/scoring workflow becomes the primary graph; the Q&A graph survives as the scoped per-paper chat with narrowed context |
| LiteLLM routing | Transfers; enables cheap-model Stage 1 / stronger-model Stage 2 split via config |
| Communal knowledge base | Transfers; becomes the shared scored-paper index — the open-source artifact |
| Clerk auth + tiered rate limiting | **Kept.** Accounts matter more in a feed product: saves, dismissals, and states are the personalization signal |
| Langfuse observability, structlog | Transfers unchanged; scoring pipeline traces route through the same setup |
| Postgres + Alembic | Transfers; new tables/migrations below |
| Frontend (React 19, Zustand, streaming UI) | Chat components reused inside paper detail; feed, cards, library, onboarding are new surfaces |
| Global chat tab, conversation history | Removed |

### 5.3 Data model additions (sketch)

- `paper_scores` — paper FK, rubric version, composite score, per-dimension sub-scores, model/version metadata.
- `score_evidence` — score FK, dimension, extracted span or external result (e.g. GitHub hit), source pointer.
- `user_paper_states` — user FK, paper FK, state enum (saved / dismissed / implementing / shipped), repo URL, timestamps. Dismissals with optional reason double as labeled feedback.
- `user_profiles` (extend existing) — categories, compute profile, interest keywords.
- `digests` — week identifier, category set, ordered paper list (cached ranking snapshot so past weeks render without recomputation).

### 5.4 Evaluation and quality control

The existing eval profile becomes a differentiator rather than an accessory. A **golden set** of 30–50 hand-labeled papers (implementable or not, and why) is maintained; every prompt or model change runs rubric-accuracy evals against it in CI, alongside the existing 80% coverage gate. User dismissals tagged "misjudged" flow into the golden set over time. The known failure mode this guards against is silent score drift — e.g., the model rating a cluster-scale training paper "single-GPU feasible."

## 6. Migration and Rollout

Because the system is in production, the pivot ships behind additive changes rather than a big-bang rewrite:

**Phase 1 — pipeline in the dark.** Ship the scoring pipeline and new tables. It runs on schedule and populates scores with no UI exposure. Validate against the golden set; tune weights.

**Phase 2 — feed alongside chat.** Ship feed, cards, paper detail, and onboarding as new routes while the existing chat remains default. Existing users see a banner inviting them to the feed. Scoped chat reuses the current agent with narrowed context.

**Phase 3 — flip and remove.** Feed becomes the default home. Global chat tab and conversation-history UI are removed; conversation data is archived, not deleted. Library and lifecycle states ship here if not earlier.

Each phase is independently deployable and reversible. User accounts, auth, and the knowledge base are untouched throughout.

## 7. Risks and Mitigations

**Scoring cost.** Deep-scoring everything would be expensive. Mitigated structurally: Stage 1 filters on abstracts with a small model; only survivors incur full-text costs; digests are computed once weekly and cached.

**False authority.** A wrong score at the top of the feed kills trust. Mitigated by evidence-first UI, the golden-set eval gate, and treating dismissal feedback as training signal.

**GitHub search reliability.** Code-gap detection depends on search recall (papers are implemented under names that don't match titles). Mitigated by searching arXiv IDs, title variants, and author repos, and by surfacing the search results themselves in evidence so users can spot misses.

**Cold-start relevance.** A generic feed on day one is uncompelling. Mitigated by onboarding (categories + compute profile) shaping the very first digest.

**Scope creep back toward chat.** Chat is deliberately scoped to one paper's context. Any pressure to re-globalize it should be treated as a signal to improve the feed instead.

## 8. Success Criteria

- The author (and early users) open the digest weekly without prompting — the ritual holds for at least a month.
- At least one paper per month moves through saved → implementing → shipped with a public repo.
- Golden-set rubric accuracy meets an agreed threshold (proposed: ≥85% agreement with hand labels on the feasibility and code-gap dimensions) and does not regress in CI.
- Top-10 feed precision, judged by the author's triage: fewer than 3 of 10 top-ranked papers dismissed as "misjudged" per week after tuning.

## 9. Open Questions

1. Should Stage 1 filtering be rules-assisted (arXiv metadata heuristics) before any LLM call, to cut costs further?
2. Rubric weights: fixed globally, or personalized per user compute profile from day one?
3. Does the communal knowledge base remain fully shared under the feed model, or do scores need per-user variants once personalization lands?
4. AGPL implications if the scored index is exposed via a public API later.

---

*Appendix intentionally omitted at this stage; module-by-module migration mapping against the current codebase to follow as a separate document once this proposal is approved in direction.*
