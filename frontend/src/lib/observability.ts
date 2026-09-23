// The only module that touches the Logfire browser SDK (the twin of backend/src/observability.py).
// With VITE_LOGFIRE_TOKEN and VITE_LOGFIRE_BASE_URL set, the SDK is loaded lazily and
// auto-instruments fetch, document load and Web Vitals; with either empty (dev, CI, tests)
// nothing is loaded and every export is a no-op. The token is a restricted frontend
// application token (Logfire > Frontend > Applications): it can only write telemetry for
// that application.
type Sdk = typeof import('@pydantic/logfire-browser').default

let sdk: Sdk | null = null
let loading: Promise<void> | null = null
let currentRoute: string | undefined
let currentUserId: string | null = null

/** Load and configure the SDK once; resolves immediately when tracing is off. */
export function configureObservability(): Promise<void> {
  const token = import.meta.env.VITE_LOGFIRE_TOKEN
  const baseUrl = import.meta.env.VITE_LOGFIRE_BASE_URL
  if (!token || !baseUrl || loading) return loading ?? Promise.resolve()
  loading = import('@pydantic/logfire-browser').then((mod) => {
    mod.default.configureFrontend({
      baseUrl,
      token,
      rum: {
        session: {
          getRouteName: () => currentRoute,
          // The API's opaque user id only; never a name or email.
          getUser: () => (currentUserId ? { id: currentUserId } : undefined),
        },
      },
    })
    sdk = mod.default
  })
  return loading
}

/** The matched route template (`/papers/:arxivId`) and the signed-in user's id, stamped on spans. */
export function setObservabilityContext(context: { route?: string; userId?: string | null }): void {
  if ('route' in context) currentRoute = context.route
  if ('userId' in context) currentUserId = context.userId ?? null
}

/** Report a caught exception (the ErrorBoundary); a no-op until the SDK is configured. */
export function reportError(error: unknown, attributes?: Record<string, unknown>): void {
  if (!sdk) return
  const message = error instanceof Error ? error.message : String(error)
  sdk.reportError(message, error, attributes)
}

/** Test seam: forget the loaded SDK and context. */
export function resetObservability(): void {
  sdk = null
  loading = null
  currentRoute = undefined
  currentUserId = null
}
