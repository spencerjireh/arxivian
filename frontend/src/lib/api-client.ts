// Base fetch wrapper for API calls: one request() behind the four verbs, the Clerk token getter
// and the 401 handler that AuthSession registers.

const API_BASE_URL = '/api'

type TokenGetter = () => Promise<string | null>
let authTokenGetter: TokenGetter | null = null
let unauthorizedHandler: (() => void) | null = null

/** Register the auth token getter. Called by AuthSession during render. */
export function setAuthTokenGetter(getter: TokenGetter): void {
  authTokenGetter = getter
}

/** Register what happens when a request that carried a token gets a 401 (the session is dead). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

/** Fire the registered 401 handler; the SSE client calls this on its own 401. */
export function reportUnauthorized(): void {
  unauthorizedHandler?.()
}

export class ApiError extends Error {
  status: number
  statusText: string

  constructor(status: number, statusText: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
  }
}

export async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = authTokenGetter ? await authTokenGetter() : null
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/** Pull a human-readable message out of a parsed error body, if it has one. */
export function errorMessageFrom(parsed: unknown): string | undefined {
  if (typeof parsed !== 'object' || parsed === null) return undefined
  const body = parsed as { detail?: unknown; message?: unknown }
  if (typeof body.detail === 'string') return body.detail
  if (typeof body.message === 'string') return body.message
  return undefined
}

/**
 * `hadToken` says whether the request carried a bearer token. A 401 on an authenticated
 * request means the session is dead and forces a sign-out; a 401 on an anonymous request
 * is just an error (the public routes never 401 without a token).
 */
async function handleResponse<T>(response: Response, hadToken: boolean): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.text()
    let message = errorBody
    try {
      const parsed: unknown = JSON.parse(errorBody)
      message = errorMessageFrom(parsed) ?? errorBody
    } catch {
      // Keep original text if not JSON
    }
    if (response.status === 401 && hadToken) {
      reportUnauthorized()
    }
    throw new ApiError(response.status, response.statusText, message)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  return handleResponse<T>(response, 'Authorization' in headers)
}

export const apiGet = <T>(path: string) => request<T>('GET', path)
export const apiPut = <T>(path: string, body: unknown) => request<T>('PUT', path, body)
export const apiPatch = <T>(path: string, body: unknown) => request<T>('PATCH', path, body)
export const apiDelete = <T = void>(path: string) => request<T>('DELETE', path)

export function getApiBaseUrl(): string {
  return API_BASE_URL
}
