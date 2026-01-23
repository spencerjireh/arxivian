// Base fetch wrapper for API calls

const API_BASE_URL = '/api'

// Token getter function - set by AuthTokenProvider
type TokenGetter = () => Promise<string | null>
let authTokenGetter: TokenGetter | null = null

/**
 * Register the auth token getter function.
 * Called by AuthTokenProvider on mount.
 */
export function setAuthTokenGetter(getter: TokenGetter): void {
  authTokenGetter = getter
}

/**
 * Get the current auth token.
 * Returns null if no token getter is registered or no token is available.
 */
export async function getAuthToken(): Promise<string | null> {
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

async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = await getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return headers
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.text()
    let message = errorBody
    try {
      const parsed = JSON.parse(errorBody)
      message = parsed.detail || parsed.message || errorBody
    } catch {
      // Keep original text if not JSON
    }
    throw new ApiError(response.status, response.statusText, message)
  }
  return response.json()
}

export async function apiGet<T>(path: string): Promise<T> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    headers,
  })
  return handleResponse<T>(response)
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response)
}

export async function apiDelete<T = void>(path: string): Promise<T> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    headers,
  })
  return handleResponse<T>(response)
}

export function getApiBaseUrl(): string {
  return API_BASE_URL
}
