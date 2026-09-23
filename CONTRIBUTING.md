# Contributing

Solo-maintained. This is the process the maintainer follows; outside PRs are held to the
same bar. `AGENTS.md` maps the code; this file covers process only.

## Setup

- Docker, Docker Compose and [just](https://github.com/casey/just): `just setup && just dev`.
- Git hooks need uv and Node 22 (`frontend/.nvmrc`) on the host: `uvx pre-commit install`,
  then `cd frontend && npm ci` (the lint-staged hook runs eslint and prettier from
  `frontend/node_modules`).

## Branches and pull requests

- Branch from `main` as `<type>/<slug>`, e.g. `feat/arx-29-library`.
- Squash-merge only. The PR title becomes the commit subject and must match
  `^(feat|fix|docs|test|chore|refactor|perf|ci|build)(\([a-z0-9-]+\))?: .+$`;
  put the Plane id at the end: `feat(feed): add week selector (ARX-11)`.
- Required checks on `main`: Backend lint, Backend unit + api, Backend integration,
  Frontend lint, Frontend tests, Docker images + coolify compose, PR title. The branch
  must be up to date with `main`, so rebase (or press Update branch) after each merge lands.
- Run `just ci` before pushing. It runs the same steps as CI except the production image
  builds.

## Coverage ratchet

`fail_under` in `backend/pyproject.toml` and `thresholds` in `frontend/vitest.config.ts`
only move up. When a PR raises coverage, raise the number in the same PR. Never lower them.

## Dependencies

Dependabot opens grouped weekly PRs. `ruff` and `ty` are pinned exactly in
`backend/pyproject.toml` because CI, the git hook and `just lint` must agree on
diagnostics; GitHub Actions are pinned by commit SHA. Both are bumped by Dependabot.

## Releases

`production` is promoted by a PR from `main` merged with a merge commit (never squash, so
the generated release notes list the real PRs). Every push to `production` is tagged
`vYYYY.MM.DD[.n]` and gets GitHub release notes built from the PR titles; those notes are
the changelog. Deployment mechanics are in `AGENTS.md` (Deployment).
