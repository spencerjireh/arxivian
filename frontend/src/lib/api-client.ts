// Base fetch wrapper for API calls

const API_BASE_URL = '/api'

// Token getter function - set by AuthSession
type TokenGetter = () => Promise<string | null>
let authTokenGetter: TokenGetter | null = null

/**
 * Register the auth token getter function.
 * Called by AuthSession during render.
 */
export function setAuthTokenGetter(getter: TokenGetter): void {
  authTokenGetter = getter
}

/**
 * Get the current auth token.
 * Returns null if no token getter is registered or no token is available.
 */
async function getAuthToken(): Promise<string | null> {
  if (!authTokenGetter) {
    return null
  }
  return authTokenGetter()
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
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = await getAuthToken()
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
      window.dispatchEvent(new CustomEvent('auth:signout'))
    }
    throw new ApiError(response.status, response.statusText, message)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export async function apiGet<T>(path: string): Promise<T> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    headers,
  })
  return handleResponse<T>(response, 'Authorization' in headers)
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response, 'Authorization' in headers)
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response, 'Authorization' in headers)
}

export async function apiDelete<T = void>(path: string): Promise<T> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    headers,
  })
  return handleResponse<T>(response, 'Authorization' in headers)
}

export function getApiBaseUrl(): string {
  return API_BASE_URL
}
