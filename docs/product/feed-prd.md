# Arxivian -- Implementation-Opportunity Feed Product Requirements Document

**Version:** 1.0-feed
**Last updated:** 2026-07-16
**Status:** Draft (product-of-record for the feed pivot)
**Supersedes:** `docs/product/beta-prd.md` (chat-first beta)
**Related:** `proposal.md` (direction pitch), `docs/design/scoring-pipeline.md` (backbone)

---

## 1. Product Summary

Arxivian is a ranked discovery feed of **papers worth turning into software
implementations**. The core artifact is a scored **paper card** surfaced in a weekly
digest, not a conversation. A two-stage scoring pipeline (see
`docs/design/scoring-pipeline.md`) triages new arXiv submissions and produces an
evidence-backed implementability score per paper. Chat is retained but demoted to a
scoped, per-paper panel on the paper detail page.

**Why:** chat-with-papers is now a commodity covered by frontier assistants. There is an
unfilled gap in implementation-oriented discovery -- Papers with Code was shut down in
mid-2025, and existing alternatives rank by popularity or relevance, not
*implementability*. No tool answers: "which papers this week describe a method that is
valuable, feasible to implement solo, and has no existing code?"

**Goal:** a weekly ritual. The digest lands after arXiv's weekend backlog clears; the user
triages cards in about five minutes, saves a couple, dismisses the rest, and optionally
goes deep on one.

**v1 scope note.** The "no existing code" half of the pitch -- the **code-gap** signal
backed by GitHub search -- is **deferred to v1.1**. It is the highest-value differentiator
but also the least reliable signal (unproven search recall, aggressive rate limits, answers
that go stale week to week), so v1 scores papers on the four dependable dimensions (method
clarity, resource feasibility, data availability, demand) and does **not** yet make a
"no existing code" claim. Code gap returns in v1.1, first as an informational
"possible existing implementations" chip and later as a weighted ranking signal, once its
recall is validated (see `docs/design/scoring-pipeline.md`). Until then, no surface should
promise that a paper is un-implemented.

---

## 2. Target Persona

**Primary:** Builders who implement papers -- individual ML/systems engineers, indie
researchers, and grad students who ship code from papers.

- Works at a desktop/laptop; has a defined compute reality (laptop / single GPU / cloud
  budget).
- Wants to find a small number of high-value, feasible, un-implemented papers per week --
  not to read broadly.
- Values transparency: will not trust a score they cannot audit.
- Produces a public artifact (a repo) when a pick pans out.

**Not targeting:** broad literature-review users, teams/orgs, mobile.

---

## 3. Design Principles

1. **The feed is the primary interface.** The paper card, not the conversation, is the
   core object. Chat is a scoped companion on paper detail, never the home surface.
2. **Evidence over score.** The verdict line and the evidence-quoting breakdown are
   visually primary; the numeric score is secondary. Every sub-score is auditable back to
   a passage or a search result. A confidently-wrong score kills trust faster than no
   score.
3. **A bounded weekly ritual, not an infinite feed.** One digest per week matches arXiv's
   rhythm and caps scoring compute. Fully triageable from cards alone.
4. **Communal knowledge grows with use.** The scored-paper index is shared -- the
   open-source artifact. Personalization is per-user state (saves, dismissals, compute
   profile), layered at read time.
5. **Ingestion is invisible.** Users no longer manage the corpus. The pipeline ingests
   scored papers automatically; opening a paper triggers on-demand ingestion if needed.

---

## 4. Core Object: the Paper Card

A card must answer "why should I care?" in about two seconds.

| Element | Content |
|---|---|
| Title + meta | Title, authors, category, submission date |
| Verdict line | One LLM sentence, e.g. "Novel KV-cache eviction method, single-GPU feasible" (the "no official code" clause is added in v1.1 with the code-gap signal) |
| Score badge | Composite implementability score; visually secondary to the verdict |
| Signal chips | v1: "Pseudocode present" / "Public datasets" / "1 GPU". v1.1 adds "No code found" / "Possible existing repo (as of `<date>`)" |
| Actions | Save, Dismiss, Mark as Implementing |

---

## 5. Screens and Flow

- **Onboarding (new, one-time).** After sign-in: select arXiv categories, declare compute
  reality (laptop / single GPU / cloud budget), optional interest keywords. ~30 seconds;
  stored on the existing `preferences` JSONB column on the user record. Shapes the first
  digest so it is personal, not generic.
- **Home = Feed.** Ranked cards for the current week, filter bar (category, minimum score,
  "no existing code only"), week selector for past digests (pre-scored and cached, so
  historical browsing is free). Dismiss is a single action, no confirmation.
- **Paper detail.** The deep-dive surface. Top: score breakdown, each sub-score paired
  with quoted evidence (the pseudocode block, the compute requirements, the dataset
  mentions; GitHub search results join in v1.1 with code gap). Bottom / slide-over:
  **scoped chat**, pre-loaded with the paper's ingested
  content, seeded with suggested prompts ("Explain the core method," "What would a minimal
  repo look like," "What are the risky parts to reproduce"). Reuses the existing streaming
  + citation UI with a narrowed context.
- **Library.** Saved and in-progress papers grouped by lifecycle state
  (saved -> implementing -> shipped). The return-visit surface; shipped items show the
  linked repo.

---

## 6. Scope Boundary

### In scope (v1)
- Scoring pipeline (Stage 1 triage + Stage 2 graph) and new tables, on a **4-dimension
  rubric** (method clarity, resource feasibility, data availability, demand). No GitHub
  dependency.
- Feed with weekly ranked cards, filters, week selector.
- Paper detail with evidence breakdown + scoped chat.
- Onboarding (categories + compute profile + keywords).
- Library with lifecycle states (saved / implementing / shipped + repo link).
- Golden-set eval gate in CI.

### Out of scope (deferred)
- **Code-gap dimension + GitHub search -> v1.1** (fast-follow, not far-future). The
  differentiator, gated on the `spikes/github-code-gap/` recall spike; ships first as an
  unweighted evidence chip.
- Automated implementation generation (paper-to-code agents). The product finds and
  scopes; the human implements.
- Social/community features (comments, shared feeds, leaderboards).
- Signals beyond GitHub and Semantic Scholar (HF discussions, X/Bluesky chatter).
- Email digests and notifications.
- Implementation-notes generation for shipped papers (data model should not preclude it).

### Removed from the chat-first product
- Global chat tab and conversation-history list.
- User-initiated ingestion as a chat action.
- (Conversation data archived, not deleted.)

---

## 7. Success Metrics

| Metric | Target | How measured |
|---|---|---|
| Weekly digest ritual | Author + early users open the digest weekly, unprompted, for >=1 month | Feed open events |
| Saved -> shipped conversions | >=1 paper/month reaches shipped with a public repo | `user_paper_states` |
| Golden-set rubric accuracy | >=85% agreement on feasibility + code-gap; no CI regression | eval profile |
| Top-10 feed precision | <3 of 10 top-ranked dismissed as "misjudged" per week after tuning | author triage |

Note the deliberate departure from the beta metrics: chat sessions/day and thumbs-up rate
are no longer primary.

---

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| False authority (wrong score at top of feed) | High (kills trust) | Evidence-first UI, golden-set eval gate, dismissal feedback as signal; the riskiest signal (code gap) is deferred out of v1 and debuts unweighted in v1.1 |
| Scoring cost | Medium | Stage 1 cheap filter; only survivors full-text scored; weekly cached digests |
| GitHub search recall / rate limits (v1.1) | Medium | Gated by the `spikes/github-code-gap/` spike; arXiv IDs + title variants + author repos; surface raw results as evidence; Redis cache + backoff |
| Cold-start relevance | Medium | Onboarding (categories + compute profile) shapes the first digest |
| Scope creep back toward chat | Medium | Chat deliberately scoped to one paper; pressure to re-globalize -> improve the feed instead |

---

## 9. Rollout

Additive and reversible (system is in production):

1. **Pipeline in the dark (v1).** Ship the 4-dimension scoring pipeline + tables; runs on
   schedule, no UI. Validate against golden set; tune weights. GitHub code-gap spike runs in
   parallel but is not on the critical path.
2. **Feed alongside chat (v1).** Ship feed, cards, paper detail, onboarding as new routes;
   chat remains default; existing users see a banner. Scoped chat reuses the current agent
   with narrowed context.
3. **Flip and remove (v1).** Feed becomes default home; global chat tab + conversation-history
   UI removed; conversation data archived. Library and lifecycle states ship here if not
   earlier.
4. **Code gap (v1.1).** Once the spike clears the recall bar, ship `github_client` + the
   `score_code_gap` node; surface an unweighted "possible existing implementations" chip,
   then promote code gap to the highest-weighted ranking signal and enable the
   "no existing code" claim.

User accounts, auth, and the communal knowledge base are untouched throughout.

---

## 10. Document Index

| Document | Path | Purpose |
|---|---|---|
| Direction pitch | `proposal.md` | Why the pivot; historical |
| Scoring pipeline design | `docs/design/scoring-pipeline.md` | Two-stage pipeline + scoring graph |
| User stories | `docs/product/user-stories.md` | Epics, stories, acceptance criteria |
| Chat-first beta PRD | `docs/product/beta-prd.md` | Superseded predecessor |
