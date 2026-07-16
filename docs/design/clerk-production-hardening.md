# Clerk Authentication: Production Hardening

## Context

The Clerk auth integration is architecturally sound -- JWKS-based JWT verification, proper route protection via dependency injection, isolated API key auth for ops, and solid test coverage. However, a detailed audit identified 11 gaps ranging from missing claim validation to information disclosure. This document covers each issue, its risk, and the proposed fix.

**Current auth flow:**
```
Frontend                          Backend
ClerkProvider                     FastAPI
  |                                 |
  |-- getToken() ----------------->|
  |   (Bearer JWT)                  |
  |                                 |-- decode unverified (get issuer)
  |                                 |-- validate issuer domain
  |                                 |-- fetch JWKS from Clerk
  |                                 |-- verify signature (RS256)
  |                                 |-- validate exp, iat, nbf
  |                                 |-- extract sub -> clerk_id
  |                                 |-- get_or_create user in DB
  |                                 |-- inject User into route handler
```

---

## Issue 1: No `aud` (audience) claim validation

**Severity: Medium**
**Files:** `backend/src/services/auth_service.py` (lines 92-101)

### Problem

The JWT verification validates `iss`, `exp`, `iat`, `nbf`, and signature, but does not validate the `aud` (audience) claim. Without audience validation, a JWT issued by the same Clerk instance for a different frontend application would be accepted by this backend. In multi-app Clerk organizations, this is a token confusion vulnerability.

### Current code

```python
payload = jwt.decode(
    token,
    signing_key.key,
    algorithms=["RS256"],
    issuer=issuer,
    options={
        "verify_exp": True,
        "verify_iat": True,
        "verify_nbf": True,
    },
)
```

### Proposed fix

1. Add `CLERK_JWT_AUDIENCE` to `config.py` (optional, defaults to empty string)
2. Add `CLERK_JWT_AUDIENCE` to `.env.example` and `docker-compose.coolify.yml`
3. In `AuthService.__init__`, accept `audience: str | None`
4. In `verify_token`, pass `audience=self._audience` and `"verify_aud": bool(self._audience)` to `jwt.decode`
5. When the audience is not configured, skip validation (preserves backward compat for dev)

This requires configuring a custom JWT template in the Clerk dashboard that includes an `aud` claim. Clerk does not include `aud` in JWTs by default.

### Clerk dashboard setup

1. Go to Clerk Dashboard > JWT Templates
2. Create a template (or edit the default session token)
3. Add `"aud": "arxivian-api"` to the claims
4. Set the frontend to request tokens with this template: `getToken({ template: "arxivian-api" })`

---

## Issue 2: SSE proxy missing forwarded headers

**Severity: Medium**
**Files:** `frontend/nginx.conf` (lines 30-38)

### Problem

The `/api/stream` location block forwards `Host` but not `X-Real-IP`, `X-Forwarded-For`, or `X-Forwarded-Proto`. The `/api/` block (lines 41-47) correctly forwards all four. This means:

- Rate limiting or abuse detection based on client IP will see the nginx container's IP, not the real client
- Any backend logic checking `X-Forwarded-Proto` for HTTPS enforcement won't work on streaming requests
- Logging middleware (`middleware/logging.py:49-50`) uses `request.client.host`, which will reflect the proxy, not the user

### Proposed fix

Add the three missing headers to the `/api/stream` block:

```nginx
location /api/stream {
    proxy_pass http://app:8000/api/v1/stream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 86400s;
    chunked_transfer_encoding on;
}
```

---

## Issue 3: No forced re-auth on 401

**Severity: Medium**
**Files:** `frontend/src/main.tsx` (lines 26-31), `frontend/src/lib/errors.ts`

### Problem

When the backend returns 401 (expired/invalid token), the frontend shows a toast ("Session expired -- Please sign in again to continue") but does not redirect to `/sign-in` or invoke Clerk's `signOut()`. The user is left on a broken page where all subsequent API calls will also fail.

The current handling only applies to TanStack Query mutations. Queries have `retry: 1`, so a 401 on a query silently fails after one retry with no user feedback at all.

### Proposed fix

Add a global 401 interceptor. Two options:

**Option A (Recommended): Query client `onError` callback for queries + redirect**

Add a query-level `onError` to the QueryClient `defaultOptions.queries` that checks for 401 and calls `clerk.signOut()` then `navigate('/sign-in')`. This requires access to the Clerk client instance and router, so it may need a wrapper component.

**Option B: Fetch wrapper intercept**

In `api/client.ts`, check for 401 in `handleResponse` and dispatch a custom event. A top-level component listens for it and triggers sign-out + redirect.

Either way, the behavior should be:
1. Detect 401 on any API call (query or mutation)
2. Call `clerk.signOut()` to clear local session state
3. Redirect to `/sign-in` with a flash message
4. Do not retry -- the token is invalid, retrying won't help

### Edge case

Clerk's `getToken()` can sometimes return a stale token if the SDK's internal refresh fails silently. The 401 interceptor catches this case. Without it, the user sees broken UI with no actionable feedback.

---

## Issue 4: Add Clerk webhooks for user sync

**Severity: Medium**
**Files:** New endpoint in `backend/src/routers/`, new handler

### Problem

User profile data (email, name, avatar) only syncs to the database on login via `get_or_create` in `dependencies.py:148-160`. If a user changes their email in Clerk, deletes their account, or gets deactivated by an admin, the local database is stale. With real users in production, this causes:

- Stale email displayed in UI
- Deleted Clerk users retaining active DB records and sessions
- No way to deactivate a user from the Clerk dashboard

### Proposed fix

1. Register a Svix webhook endpoint in the Clerk dashboard pointing to `POST /api/v1/webhooks/clerk`
2. Create `backend/src/routers/webhooks.py` with a single endpoint
3. Verify the webhook signature using the `svix` library and `CLERK_WEBHOOK_SECRET` env var
4. Handle these event types:

| Event | Action |
|---|---|
| `user.updated` | Update email, name, avatar in `users` table |
| `user.deleted` | Soft-delete or deactivate the user record |

5. Add `CLERK_WEBHOOK_SECRET` to `config.py`, `.env.example`, and `docker-compose.coolify.yml`
6. Add `svix` to backend dependencies

### Auth model for the webhook endpoint

This endpoint must NOT use `CurrentUserRequired` (it's called by Clerk's servers, not by a user). Auth is via Svix signature verification only. The endpoint should be excluded from CORS (server-to-server).

---

## Issue 5: Remove unused `CLERK_SECRET_KEY`

**Severity: Low**
**Files:** `backend/src/config.py` (line 70), `backend/.env.example`, `docker-compose.coolify.yml` (lines 86-87, 155-156)

### Problem

`CLERK_SECRET_KEY` is configured in 4 places but never referenced by application code. The backend uses JWKS-based JWT verification (which only needs the public key fetched from the JWKS endpoint). Having an unused secret in env vars:

- Creates confusion about what's actually needed
- Expands the secret surface area unnecessarily
- Gets passed to celery workers that don't do auth verification

### Proposed fix

1. Remove `clerk_secret_key` from `config.py`
2. Remove `CLERK_SECRET_KEY` from `backend/.env.example`
3. Remove `CLERK_SECRET_KEY` from both `app` and `celery-worker` services in `docker-compose.coolify.yml`
4. Keep `CLERK_DOMAIN` (it is used)

**Exception:** If Issue 4 (webhooks) is implemented and the chosen library requires the secret key for signature verification, keep it. However, Svix webhooks use a separate `CLERK_WEBHOOK_SECRET`, not `CLERK_SECRET_KEY`, so removal is still safe.

---

## Issue 6: Root endpoint leaks API surface

**Severity: Low-Medium**
**Files:** `backend/src/main.py` (lines 132-157)

### Problem

The `GET /` endpoint returns a JSON payload listing every API route, feature list, and exact version number. In production, this is unnecessary information disclosure that gives attackers a complete map of the API surface without any authentication.

### Proposed fix

**Option A (Recommended): Minimal response**

```python
@app.get("/")
async def root():
    return {"name": "Arxivian API", "status": "ok"}
```

**Option B: Gate behind API key**

Move the detailed response behind `ApiKeyCheck` so only ops can see it.

**Option C: Remove entirely**

Health checks use `/api/v1/health`. The root endpoint serves no operational purpose. Return 404 or remove the route.

Additionally, disable `/docs` and `/redoc` in production by setting `docs_url=None, redoc_url=None` in the `FastAPI()` constructor when `DEBUG=False`.

---

## Issue 7: Missing HSTS header

**Severity: Low**
**Files:** `frontend/nginx.conf`

### Problem

`nginx.conf` includes `X-Frame-Options` and `X-Content-Type-Options` but not `Strict-Transport-Security`. Without HSTS, browsers don't enforce HTTPS on subsequent requests, leaving users vulnerable to SSL stripping on the first visit.

### Proposed fix

If nginx terminates TLS (unlikely in production behind Coolify's reverse proxy):

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

If Coolify's reverse proxy handles TLS (more likely): verify HSTS is set at that layer. No change needed in `nginx.conf` -- document this in a deployment checklist.

**Action:** Confirm where TLS terminates in the Coolify setup. If at the outer proxy, no code change is needed. If at nginx, add the header.

---

## Issue 8: No session revocation handling

**Severity: Low**
**Files:** `backend/src/services/auth_service.py`

### Problem

JWTs are stateless. If a user's session is revoked in the Clerk dashboard (e.g., compromised account), the token remains valid until its `exp` claim passes. Clerk's default session token lifetime is 60 seconds, which limits the window, but a compromised token is still usable for up to a minute.

### Proposed fix

**Option A (Recommended for now): Accept the risk, document it**

Clerk's short-lived tokens (60s) make the revocation window small. For most apps, this is acceptable. Document this as a known limitation.

**Option B (If stricter security is needed later): Active revocation check**

On each request, call Clerk's Backend API (`GET /v1/sessions/{session_id}`) to verify the session is still active. This adds latency to every request. Mitigate with a short-lived Redis cache (e.g., 10s TTL). This requires `CLERK_SECRET_KEY` (reverses Issue 5 partially).

**Recommendation:** Go with Option A for launch. Revisit if the threat model changes (e.g., handling financial data, regulatory requirements).

---

## Issue 9: `get_current_user_optional` swallows all exceptions

**Severity: Low (not currently wired into any route)**
**Files:** `backend/src/dependencies.py` (lines 176-179)

### Problem

```python
try:
    return await _sync_user(authorization, db)
except Exception:
    return None
```

This catches everything -- including database connection errors, unexpected bugs in `_sync_user`, and serialization issues. A transient DB outage would silently downgrade authenticated users to anonymous rather than returning a 500.

### Proposed fix

Narrow the exception handling to auth-specific errors only:

```python
from src.exceptions import AuthenticationError

try:
    return await _sync_user(authorization, db)
except AuthenticationError:
    return None
```

This way, auth failures return `None` (expected), but infrastructure failures propagate as 500s (correct). Apply this fix now even though the dependency isn't wired into any route -- it prevents a latent bug when it eventually is.

---

## Issue 10: AuthService singleton has no reset path

**Severity: Low**
**Files:** `backend/src/services/auth_service.py` (lines 143-155)

### Problem

The module-level `_auth_service` singleton caches the `clerk_domain` from first access. If the domain changes (env reload, test isolation), the stale value persists. This is primarily a testing concern -- production processes restart on config changes.

### Proposed fix

Add a `reset_auth_service()` function for test cleanup:

```python
def reset_auth_service() -> None:
    global _auth_service
    _auth_service = None
```

Use in test fixtures and conftest. No production impact.

---

## Issue 11: `CLERK_SECRET_KEY` passed to Celery workers

**Severity: Low**
**Files:** `docker-compose.coolify.yml` (lines 155-156)

### Problem

`CLERK_SECRET_KEY` and `CLERK_DOMAIN` are passed to `celery-worker` and `celery-beat` services. Celery tasks don't perform JWT verification -- they run background jobs (ingestion, cleanup). Passing auth secrets to services that don't need them increases the blast radius if a worker is compromised.

### Proposed fix

Remove `CLERK_SECRET_KEY` and `CLERK_DOMAIN` from the celery service environment blocks in `docker-compose.coolify.yml`. If Issue 5 removes `CLERK_SECRET_KEY` entirely, this is partially addressed, but `CLERK_DOMAIN` should also be removed from workers.

**Exception:** If a future celery task needs to make authenticated calls to the Clerk API, add the key back to that specific service only.

---

## Implementation Priority

| Phase | Issues | Effort | Risk Reduction |
|---|---|---|---|
| **Phase 1: Pre-launch** | #1 (aud validation), #2 (SSE headers), #3 (401 redirect), #6 (root endpoint) | ~4-6 hours | High -- closes real security and UX gaps |
| **Phase 2: Soon after launch** | #4 (webhooks), #5 (remove secret key), #11 (celery env cleanup) | ~3-4 hours | Medium -- data integrity and hygiene |
| **Phase 3: When convenient** | #7 (HSTS), #8 (revocation), #9 (exception narrowing), #10 (singleton reset) | ~1-2 hours | Low -- defensive hardening and test quality |

---

## Files Summary

### New files
- `backend/src/routers/webhooks.py` -- Clerk webhook handler (Issue 4)

### Modified files

| File | Issues | Changes |
|---|---|---|
| `backend/src/services/auth_service.py` | #1, #10 | Add `aud` validation, add `reset_auth_service()` |
| `backend/src/config.py` | #1, #4, #5 | Add `CLERK_JWT_AUDIENCE`, add `CLERK_WEBHOOK_SECRET`, remove `clerk_secret_key` |
| `backend/src/dependencies.py` | #9 | Narrow exception catch in `get_current_user_optional` |
| `backend/src/main.py` | #6 | Minimize root endpoint, conditionally disable docs |
| `backend/.env.example` | #1, #4, #5 | Add audience + webhook secret, remove secret key |
| `frontend/nginx.conf` | #2, #7 | Add forwarded headers to SSE block, optionally add HSTS |
| `frontend/src/main.tsx` | #3 | Add global 401 interceptor |
| `frontend/src/api/client.ts` | #1, #3 | Pass JWT template to `getToken()`, add 401 event dispatch |
| `frontend/src/components/auth/AuthTokenProvider.tsx` | #1 | Update `getToken()` call with template parameter |
| `docker-compose.coolify.yml` | #1, #4, #5, #11 | Add audience + webhook secret, remove secret key from all services, remove auth vars from celery |

### Test updates
- `backend/tests/unit/services/test_auth_service.py` -- add `aud` validation tests, add `reset_auth_service` usage
- `backend/tests/unit/routers/test_webhooks.py` -- new, webhook signature verification and event handling
- `backend/tests/unit/dependencies/test_dependencies.py` -- update `get_current_user_optional` exception tests

---

## Verification

1. **Unit tests**: `just test tests/unit/` -- all pass including new auth and webhook tests
2. **API tests**: `just test tests/api/` -- 401 responses still return correct error schema
3. **Lint + types**: `just check` -- zero errors
4. **Manual: aud validation**: Set `CLERK_JWT_AUDIENCE` in backend, configure JWT template in Clerk dashboard, verify tokens without `aud` are rejected
5. **Manual: 401 flow**: Let a session expire, verify automatic redirect to `/sign-in`
6. **Manual: webhooks**: Update user email in Clerk dashboard, verify DB reflects the change
7. **Manual: SSE headers**: Check `X-Real-IP` appears in backend logs for streaming requests
8. **Manual: root endpoint**: `curl /` returns minimal response, `/docs` returns 404 in production
