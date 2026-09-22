# frontend/AGENTS.md

As-built map of the React app. The root `AGENTS.md` holds the repo map, commands, CI and
deployment; this file holds what is specific to `frontend/`. `CLAUDE.md` here is a symlink
to it. Update it in the same PR as the code it describes.

## Structure

Bulletproof React layout: shared modules -> features -> app, enforced by
`import-x/no-restricted-paths` in `eslint.config.js`. Features never import each other,
with one documented exception: `feed` renders `paper`'s `CardActions` on its cards, so
`feed -> paper` is allowed and `paper -> feed` is not. Shared modules (`components/`,
`lib/`, `stores/`, `types/`) never import `features/` or `app/`. Imports that climb two or
more directories use the `@/` alias (`tsconfig.*.json` `paths`, `vite.config.ts`
`resolve.alias`); siblings and children stay relative. No barrel `index.ts` files.

```
src/main.tsx                 Vite entry: createRoot, maintenance switch, <AppProvider><AppRouter/>
src/app/provider.tsx         Clerk + QueryClient (global mutation error toast) + ErrorBoundary + Toaster
src/app/router.tsx           the only router (AuthSession > Layout > lazy routes; ProtectedRoute on account routes)
src/app/routes/              one file per route
src/features/feed/           GET /feed: api/get-feed.ts, FeedList/FeedCard/FeedFilterBar/WeekSelector/OnboardingPrompt, lib/feedParams.ts
src/features/paper/          paper detail + chat: api/{get-paper-score,get-library,get-conversation,stream-chat,paper-state}.ts,
                             components/ (PaperHeader, CardActions, ScoreBreakdown and its parts, ScopedChatPanel, chat/*),
                             hooks/{useChat,useMessageCache,useAutoScroll}.ts, lib/{errorMapping,scopedPrompts}.ts
src/features/profile/        onboarding form + settings sections; api/update-feed-profile.ts, lib/arxivCategories.ts
src/features/auth/           AuthSession, ProtectedRoute, AuthLayout, OAuthButtons, SignInForm, SignUpForm
src/features/landing/        /about page sections (Hero, FeatureGrid, Credibility, ...), hooks/useInView.ts
src/components/ui/           primitives: Button, Chip, Input, AnimatedCollapse, ErrorBoundary, PageErrorFallback, Toaster, DimensionMeter, SignInLink
src/components/layout/       Layout, TopNav, UserMenu, Footer, MaintenanceScreen
src/lib/api-client.ts        fetch wrapper; API base is /api (nginx rewrites to /api/v1)
src/lib/query-keys.ts        every TanStack Query key factory (feed, library, scores, conversations); shared so features can invalidate each other
src/lib/                     errors, formatting, formClasses, id, nav, animations, markdown/ (component map, plugins), markdownHeadings
src/stores/                  Zustand: chatStore (streaming state), userStore (me)
src/types/api.ts             hand-mirrored backend schemas; update with every schema change
src/content/privacy-policy.md   rendered at /privacy
tests/unit/**                vitest + jsdom, mirrors src/; tests/{fixtures,helpers,mocks}
```

Every module starts with a one-line `//` header naming its responsibility and its backend
twin where one exists. Grep either tree by route or table name to find the other side.

## Behavior

React 19 + TypeScript strict + Vite; Tailwind v4 (light-only warm stone theme, tokens in
`src/index.css`); Clerk auth; React Router v7. The feed is public and lives at `/`
(`/feed` and `/chat/*` redirect there, keeping the query string); `/papers/:arxivId`,
`/about` (the marketing page), `/pricing` and `/privacy` are public too; `/library` and
`/settings` sit behind `ProtectedRoute`; `/onboarding`, `/sign-in`, `/sign-up` and
`/sso-callback` render outside the shell. `features/auth/components/AuthSession.tsx` is the
root layout route: it registers Clerk's token getter with `lib/api-client.ts` (a null
getter when signed out), waits for Clerk to load, fetches `/users/me` only for a signed-in
visitor, clears the TanStack Query cache when a signed-in session ends (the public pages
must not serve the previous user's state) and handles the forced sign-out that
`lib/api-client.ts` and `features/paper/api/stream-chat.ts` raise on a 401 to a request
that carried a token. `components/layout/Layout.tsx` is a document page (window scroll):
`TopNav` (Feed, About, Pricing; Library, Settings and `UserMenu` when signed in;
`SignInLink` otherwise), the page, `Footer`. There is no sidebar and no onboarding gate.
Sign-in returns to `location.state.from` (`lib/nav.ts::returnPathFrom`, same-origin paths
only) through `OAuthButtons`' `redirectUrlComplete`; every sign-in prompt is
`components/ui/SignInLink.tsx`.

Cards (`features/feed/components/FeedCard.tsx`) show the API's `headline` and `meta`
phrases (plus a "Fits your compute" chip on `compute_match`) and a `DimensionMeter` over the
four 0-100 sub-scores (a null sub-score is a hollow "not available" segment); no composite
number, band word or confidence icon on a card. Actions are Save and Dismiss;
`features/paper/components/CardActions.tsx` offers Implementing / Ship only where the
handlers are passed (paper detail, Library). An anonymous reader gets a `SignInLink` Save,
no dismissed toggle, and `include_dismissed` is dropped from the URL params.
`features/feed/components/OnboardingPrompt.tsx` replaces the gate: it shows for
`me.onboarded === false` until dismissed (local storage). Paper detail
(`features/paper/components/ScoreBreakdown.tsx`) is `ScoreSummary` (headline, meta, meter)
-> `AttributeChips` -> four always-open `DimensionRow`s (`lib/scoring.ts::bandWord` Strong /
Mixed / Weak or Pass / Fail, the level label, `dimensionFacts`, the evidence) -> code
mentions -> `ScoringDetails`, a native `<details>` closed by default that holds the rubric
version, composite, confidence, `DistributionBar`s and `JudgmentList`s. Anonymous readers
see `ChatSignInPrompt` instead of the chat panel, and on an unscored paper `PaperPreview`
(the 202's `paper` metadata) with a sign-in CTA; `usePaperScore(id, { poll: false })` then
treats the 202 as final.

Server state is TanStack Query v5 (`features/*/api/*.ts`, hooks over the key factories in
`lib/query-keys.ts`, optimistic lifecycle updates in `features/paper/api/paper-state.ts`);
UI state is Zustand (`src/stores/`). Chat exists only as
`features/paper/components/ScopedChatPanel.tsx`: `useChat(sessionId, { arxivId })` posts
`{query, arxiv_id, session_id}` over `@microsoft/fetch-event-source`, keeps a per-paper
draft, and shows one status line; `useChatStore` allows one mounted chat surface, so the
panel aborts on unmount; `?session=` selects a thread. One markdown renderer
(`features/paper/components/chat/MarkdownRenderer.tsx` lazily loads `MarkdownBody`: GFM,
remark-math/KaTeX, arXiv links, Prism); the privacy page uses the same component map from
`lib/markdown/`. `features/paper/api/get-paper-score.ts` polls the 202 every 5 s for up to
3 min. Tiers on the client are `daily_chat_limit` / `chats_used_today` only.

## Testing

vitest + jsdom + Testing Library; `tests/unit/**` mirrors `src/**`, so a test moves with its
subject. `tests/helpers/renderWithProviders.tsx` wraps in QueryClientProvider + MemoryRouter;
`tests/mocks/clerk.ts` and `tests/mocks/framer-motion.tsx` are the module mocks; fixtures in
`tests/fixtures/`. Coverage thresholds in `vitest.config.ts` are a ratchet: raise them when
the number goes up, never lower. `npm run lint` is eslint + knip (unused files, exports and
dependencies fail), `npm run format:check`, `npm run typecheck`; `just check` and `just ci`
run the same steps from the repo root.

## Gotchas

- `VITE_*` values are baked at build time in production (`frontend/Dockerfile` build args).
- `POST /stream` rejects unknown fields; the chat store allows one mounted panel at a time.
- A route component that is also statically imported (RouteErrorPage -> NotFoundPage) does
  not get its own chunk; the build warns and it is harmless.
