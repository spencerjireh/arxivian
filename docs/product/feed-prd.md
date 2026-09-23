# Arxivian -- Implementation-Opportunity Feed Product Requirements Document

**Version:** 1.1-public
**Last updated:** 2026-09-22
**Status:** Product-of-record for the feed. Phases 1-3 shipped (see section 9); Phase 5
(public feed, this revision) in progress; v1.1 code gap not started. `AGENTS.md` describes
the code as built.
**Supersedes:** 1.0-feed (2026-09-22, in git history); the chat-first beta PRD (removed
2026-09-20)
**Related:** `docs/design/scoring-pipeline.md` (pipeline), `docs/design/scoring-rubric.md`
(rubric v2), `docs/product/user-stories.md` (epics)

---

## 1. Product Summary

Arxivian is a **public weekly publication** of arXiv papers ranked by how implementable
they are. Each week is an issue of scored **paper cards**; anyone can read the current and
past issues and open any paper's evidence without an account. A two-stage scoring pipeline
(see `docs/design/scoring-pipeline.md`) triages new submissions and produces an
evidence-backed implementability score per paper.

An account adds the personal layer: saving and dismissing papers, a library with lifecycle
states, a compute-and-category profile that re-ranks the issue, a chat scoped to each
paper, and on-demand scoring of papers outside the digest. A paid tier adds volume (see
section 6).

**Why:** chat-with-papers is a commodity covered by frontier assistants. There is an
unfilled gap in implementation-oriented discovery -- Papers with Code was shut down in
mid-2025, and existing alternatives rank by popularity or relevance, not
*implementability*. No tool answers: "which papers this week describe a method that is
valuable, feasible to implement solo, and has no existing code?" The scored index is more
useful public than gated: it is the shared artifact, and a reader who has not signed in
still gets the full answer.

**Goal:** a weekly ritual. The issue lands after arXiv's weekend backlog clears; a reader
triages cards in about five minutes, a signed-in reader saves a couple and dismisses the
rest, and optionally goes deep on one.

**v1 scope note.** The "no existing code" half of the pitch -- the **code-gap** signal
backed by GitHub search -- is **deferred to v1.1**. It is the highest-value differentiator
but also the least reliable signal (unproven search recall, aggressive rate limits, answers
that go stale week to week), so the product scores papers on the four dependable
dimensions (method clarity, resource feasibility, data availability, demand) and does
**not** yet make a "no existing code" claim. Until then, no surface promises that a paper
is un-implemented.

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

**Anonymous reader:** the same person before they sign in, or someone who arrived from a
shared link. Reads the issue and the evidence; sees what an account adds without being
blocked.

**Not targeting:** broad literature-review users, teams/orgs, mobile.

---

## 3. Design Principles

1. **The feed is the primary interface.** The paper card, not the conversation, is the
   core object. Chat is a scoped companion on paper detail, never the home surface.
2. **Public by default; personalization is a layer.** Everything derived from the shared
   scored index (issues, cards, evidence) is readable without an account. Per-user state
   (saves, dismissals, profile, chat) is layered on at read time and never changes what an
   anonymous reader can see.
3. **Evidence over score.** The headline and the evidence-quoting breakdown are visually
   primary; scores are shown as a four-dimension meter, never as a single number on a
   card. Every dimension is auditable back to a passage or a search result. A
   confidently-wrong score kills trust faster than no score.
4. **A bounded weekly ritual, not an infinite feed.** One issue per week matches arXiv's
   rhythm and caps scoring compute. Fully triageable from cards alone.
5. **Pipeline internals stay behind a disclosure.** Level distributions, per-judgment
   probabilities, confidence and rubric version are available on paper detail under
   "Scoring details", not on the first screen.
6. **Ingestion is invisible.** Readers do not manage the corpus. The pipeline ingests
   scored papers automatically; a signed-in reader opening an unscored paper triggers
   on-demand scoring.

---

## 4. Core Object: the Paper Card

A card must answer "why should I care?" in about two seconds.

| Element | Content |
|---|---|
| Title + meta | Title, authors, category, submission date |
| Headline | A template sentence built in code from the stored attributes: "<Model family> for <task type>" with fallbacks ("Method for <task>", "<Family>", "Method paper"). No LLM at read time |
| Meta line | Short phrases from the stored judgments, truthy-only, in a fixed order: compute tier ("one consumer GPU"), data access ("public data"), "code released", "weights released", "pseudocode given", "hyperparameters stated". Never a negative claim. A "Fits your compute" marker is appended for a signed-in reader with a profile |
| Dimension meter | Four segments (method clarity, resource feasibility, data availability, demand) filled from the derived 0-100 sub-scores. A missing value (for example a failed demand lookup) renders as a hollow segment labeled "not available", never as low. No composite number, no band text, no confidence icon on the card |
| Actions | Signed in: Save, Dismiss. Anonymous: Save, which opens sign-in and returns to the issue. Implementing and Shipped live on paper detail and Library |

---

## 5. Screens and Flow

- **Home = the issue (`/`, public).** A document-style page: masthead ("Arxivian", "Week
  of <date>", paper count), week selector for past issues (pre-scored and cached, so
  historical browsing is free), filter bar (category, minimum band; "show dismissed" only
  when signed in), then one ranked list of cards with load-more. Filters live in the URL
  for everyone. Dismiss is a single action, no confirmation. A signed-in reader without a
  profile sees a dismissible prompt at the top of the issue ("Set your compute and
  categories") that opens the profile form.
- **Top nav, one for everyone.** Logo, Feed, About, Pricing; signed in adds Library,
  Settings and the account menu; signed out shows Sign in. There is no sidebar and no
  separate app shell.
- **About (`/about`).** The marketing page (hero, features, credibility). Sign-in and
  OAuth land on `/`, or on the page the reader came from when they clicked a sign-in
  prompt.
- **Paper detail (`/papers/{arxiv_id}`, public).** Top: header with actions (all four
  lifecycle actions when signed in; Save-to-sign-in otherwise), headline, meta line and
  the dimension meter. Then the four dimensions, each open by default with its band word
  (Strong / Mixed / Weak; Pass / Fail for data), level label, a short reason and the
  quoted evidence. At the bottom a collapsed **Scoring details** section holds the level
  distributions, the atomic judgments with probabilities, confidence and the rubric
  version. Right column: the **scoped chat** for signed-in readers (pre-loaded with the
  paper's ingested content, seeded prompts), a sign-in prompt otherwise.
  - An unscored paper: a signed-in reader triggers on-demand scoring and polls; an
    anonymous reader sees the paper's metadata and abstract with "Sign in to score this
    paper". A paper unknown to the index is fetched from arXiv on read and stored as a
    metadata-only row, never scored by an anonymous request.
- **Profile (`/onboarding`, signed in).** Select arXiv categories, declare compute reality
  (laptop / single GPU / cloud budget), optional interest keywords. ~30 seconds; stored on
  the `preferences` JSONB column on the user record. No longer a gate: reached from the
  issue prompt or Settings.
- **Library (`/library`, signed in).** Saved and in-progress papers grouped by lifecycle
  state (saved -> implementing -> shipped). The return-visit surface; shipped items show
  the linked repo.

---

## 6. Scope Boundary

### Access split

| Tier | Includes |
|---|---|
| Anonymous | The current and every past issue, filters, paper detail with evidence and Scoring details |
| Free account | Save, dismiss, library, profile and re-ranking, chat 10 turns/day, on-demand scoring within the daily per-user budget |
| Paid | Unlimited chat, a higher on-demand scoring budget; later custom feeds and an email digest |

Anonymous readers never enqueue scoring, never count against a budget, and never write
per-user state.

### In scope (this revision)
- Public read path: the issue and paper detail without a token; anonymous metadata-only
  202 for unscored papers.
- Headline + meta line built from stored attributes (no new judge questions, no rescore).
- Four-dimension meter on cards and detail; composite number and band text removed from
  cards.
- Top nav for everyone; sidebar removed; landing page at `/about`.
- Paper detail restructure with the collapsed Scoring details section; anonymous states
  for the chat panel and unscored papers.
- Onboarding prompt replaces the onboarding gate.

### Out of scope (deferred)
- **Code-gap dimension + GitHub search -> v1.1** (fast-follow). The differentiator, gated
  on the code-gap recall spike; ships first as an unweighted evidence chip.
- A written one-liner generated at score time (a richer headline than the template).
- New judged attributes for the headline (needs a rubric bump).
- Link previews and indexing for the public pages (the frontend is a single-page app).
- Custom feeds (category sets beyond the triage default) and email digests: the paid
  features after the public feed has readers.
- Compute profile for anonymous readers (local storage).
- Automated implementation generation. The product finds and scopes; the human implements.
- Social/community features (comments, shared feeds, leaderboards).
- Signals beyond GitHub and Semantic Scholar.
- Implementation-notes generation for shipped papers (data model should not preclude it).

### Removed
- The sidebar app shell, the "Beta" tag, the onboarding gate (superseded by the prompt).
- The composite score badge, band labels and signal chips on cards (superseded by the
  headline, meta line and meter).
- Global chat tab, conversation-history list, user-initiated ingestion as a chat action
  (removed in Phase 3; conversation data archived, not deleted).

---

## 7. Success Metrics

| Metric | Target | How measured |
|---|---|---|
| Weekly issue ritual | Author + early readers open the issue weekly, unprompted, for >=1 month | Feed open events (anonymous and signed in) |
| Sign-in conversion | Anonymous readers who save a paper complete sign-in and return to the issue | Sign-in events with a return path |
| Saved -> shipped conversions | >=1 paper/month reaches shipped with a public repo | `user_paper_states` |
| Golden-set rubric accuracy | >=85% agreement on feasibility (code gap added in v1.1); no regression between manual runs | `just inteval -k scoring` |
| Top-10 feed precision | <3 of 10 top-ranked dismissed as "misjudged" per week after tuning | author triage |

Chat sessions/day and thumbs-up rate are not primary.

---

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| False authority (wrong score at top of a public issue) | High (kills trust) | Evidence-first UI, meter instead of a number, golden-set eval gate, dismissal feedback as signal; the riskiest signal (code gap) is deferred out of v1 and debuts unweighted in v1.1 |
| Anonymous load on the read path and on arXiv | Medium | Reads are five batched queries per page; the arXiv metadata fetch is one call per unknown id, bounded by a timeout, and stores a row so it never repeats; scoring stays signed-in and budgeted |
| Scoring cost | Medium | Stage 1 cheap filter; only survivors full-text scored; weekly cached digests; per-user and global on-demand budgets |
| GitHub search recall / rate limits (v1.1) | Medium | Gated by the code-gap spike; arXiv IDs + title variants + author repos; surface raw results as evidence; Redis cache + backoff |
| Cold-start relevance | Medium | The profile prompt on the issue; the default order is the global composite |
| Scope creep back toward chat | Medium | Chat deliberately scoped to one paper; pressure to re-globalize -> improve the feed instead |

---

## 9. Rollout

Additive and reversible (system is in production):

1. **Pipeline in the dark (v1).** Ship the 4-dimension scoring pipeline + tables; runs on
   schedule, no UI. Validate against golden set; tune weights.
2. **Feed alongside chat (v1).** Feed, cards, paper detail, onboarding as new routes; chat
   remains default. *Shipped 2026-09-19 (ARX-9..ARX-13; PRs #18-#22).*
3. **Flip and remove (v1).** Feed becomes default home; global chat tab + conversation
   history removed. *Shipped 2026-09-20 (ARX-31, ARX-32, ARX-29). Relaunched to
   production 2026-09-21 behind the maintenance curtain; the first weekly cycle came out
   empty (ARX-39), the fix shipped 2026-09-22, the 2026-09-21 digest was rebuilt by hand
   (268 papers) and the curtain came down the same day.*
4. **Code gap (v1.1).** Once the spike clears the recall bar, ship `github_client` + the
   `score_code_gap` node; surface an unweighted "possible existing implementations" chip,
   then promote code gap to the highest-weighted ranking signal and enable the "no
   existing code" claim.
5. **Public feed (this revision).** Backend public reads and the headline/meta fields,
   then the frontend shell, cards and detail. All PRs land on `main`; production is
   promoted once, with a single `main -> production` merge, when the batch is complete.
   No curtain. Sequenced ahead of step 4.

User accounts, auth, and the communal knowledge base are untouched throughout.

---

## 10. Document Index

| Document | Path | Purpose |
|---|---|---|
| Scoring pipeline design | `docs/design/scoring-pipeline.md` | Two-stage pipeline + scoring graph |
| User stories | `docs/product/user-stories.md` | Epics, stories, acceptance criteria |
| Scoring rubric | `docs/design/scoring-rubric.md` | Questions, combine rules, bands (rubric v2) |
| Code map | `AGENTS.md` | The code as built, commands, conventions |
