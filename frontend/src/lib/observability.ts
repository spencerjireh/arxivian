// The only module that touches Grafana Faro (the browser twin of backend/src/observability.py).
// With VITE_FARO_URL set, the SDK is loaded lazily into its own `telemetry` chunk and reports
// unhandled errors, ErrorBoundary errors and Web Vitals to our own Alloy faro.receiver; with it
// empty (dev, CI, tests) nothing is loaded and every export is a no-op.
//
// Deliberately narrow: no tracing instrumentation, so nothing propagates traceparent and browser
// signals do not join the FastAPI traces. No console, user-action, performance or CSP capture. No
// session tracking, so nothing is stored on the visitor's device -- src/content/privacy-policy.md
// says so. VITE_FARO_API_KEY is public by construction (it ships in the bundle); the receiver's
// CORS allow-list and rate limiter are the real protection.
import type { Faro, TransportItem } from '@grafana/faro-web-sdk'

const APP_NAME = 'arxivian-web'
/** Faro requires a view name; the pathless root and unmatched routes have none. */
const UNKNOWN_VIEW = 'unknown'
/** componentStack is long and Faro contexts are strings; keep a line out of the payload budget. */
const MAX_CONTEXT_CHARS = 2000

let faro: Faro | null = null
let loading: Promise<void> | null = null
let currentRoute: string | undefined
let currentUserId: string | null = null

/** Load and configure the SDK once; resolves immediately when telemetry is off. */
export function configureObservability(): Promise<void> {
  const url = import.meta.env.VITE_FARO_URL
  if (!url || loading) return loading ?? Promise.resolve()
  loading = import('@grafana/faro-web-sdk').then(
    ({ ErrorsInstrumentation, initializeFaro, WebVitalsInstrumentation }) => {
      // Building the config inside the callback is what replays the context: whatever
      // setObservabilityContext recorded while the import was in flight becomes the initial
      // user and view metas, so an early route change is not lost.
      faro =
        initializeFaro({
          url,
          apiKey: import.meta.env.VITE_FARO_API_KEY || undefined,
          app: { name: APP_NAME, environment: import.meta.env.MODE },
          // Explicit list: getWebInstrumentations() would also add console, user-action,
          // performance, navigation, CSP and session capture.
          instrumentations: [new ErrorsInstrumentation(), new WebVitalsInstrumentation()],
          // Off, not merely non-persistent: the default volatile manager still writes a
          // com.grafana.faro.session id to sessionStorage. `persistent` only chooses which
          // storage, not whether one is used.
          sessionTracking: { enabled: false },
          user: currentUserId ? { id: currentUserId } : undefined,
          view: { name: currentRoute ?? UNKNOWN_VIEW },
          beforeSend: stripQueryString,
        }) ?? null // typed Faro, but returns undefined if a global instance already exists
    }
  )
  return loading
}

/** The matched route template (`/papers/:arxivId`) and the signed-in user's id, on every signal. */
export function setObservabilityContext(context: { route?: string; userId?: string | null }): void {
  if ('route' in context) currentRoute = context.route
  if ('userId' in context) currentUserId = context.userId ?? null
  // Faro's context API is push-based, unlike the pull callbacks this module used to hand the
  // Logfire SDK. Store first so configureObservability can replay, then push if it is loaded.
  if (!faro) return
  faro.api.setView({ name: currentRoute ?? UNKNOWN_VIEW })
  faro.api.setUser(currentUserId ? { id: currentUserId } : undefined)
}

/** Report a caught exception (the ErrorBoundary); a no-op until the SDK is configured. */
export function reportError(error: unknown, attributes?: Record<string, unknown>): void {
  if (!faro) return
  faro.api.pushError(error instanceof Error ? error : new Error(String(error)), {
    context: toContext(attributes),
  })
}

/**
 * Faro's page meta is `location.href`, and a paper URL carries `?session=<conversation id>`.
 * Send the path only.
 */
function stripQueryString(item: TransportItem): TransportItem {
  const url = item.meta.page?.url
  if (!url) return item
  const stripped = url.split(/[?#]/)[0]
  return { ...item, meta: { ...item.meta, page: { ...item.meta.page, url: stripped } } }
}

/** Faro contexts are Record<string, string>, so coerce and drop what carries no information. */
function toContext(attributes?: Record<string, unknown>): Record<string, string> | undefined {
  if (!attributes) return undefined
  const context: Record<string, string> = {}
  for (const [key, value] of Object.entries(attributes)) {
    const text = asString(value)
    if (text === undefined) continue
    context[key] = text.slice(0, MAX_CONTEXT_CHARS)
  }
  return Object.keys(context).length > 0 ? context : undefined
}

/** undefined for anything that would stringify to noise (nullish, functions, symbols). */
function asString(value: unknown): string | undefined {
  if (value === null || value === undefined) return undefined
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
    return value.toString()
  }
  return JSON.stringify(value)
}
