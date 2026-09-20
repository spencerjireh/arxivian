// SSE stream handler using fetchEventSource

import { fetchEventSource } from '@microsoft/fetch-event-source'
import { errorMessageFrom, getApiBaseUrl, getAuthHeaders } from './client'
import type {
  StreamRequest,
  StreamEventType,
  StatusEventData,
  ContentEventData,
  SourcesEventData,
  MetadataEventData,
  ErrorEventData,
  CitationsEventData,
} from '../types/api'

export interface StreamCallbacks {
  onStatus?: (data: StatusEventData) => void
  onContent?: (data: ContentEventData) => void
  onSources?: (data: SourcesEventData) => void
  onMetadata?: (data: MetadataEventData) => void
  onError?: (data: ErrorEventData) => void
  onDone?: () => void
  onCitations?: (data: CitationsEventData) => void
}

export class StreamAbortError extends Error {
  constructor() {
    super('Stream aborted')
    this.name = 'StreamAbortError'
  }
}

export class StreamError extends Error {
  code: string
  constructor(message: string, code: string) {
    super(message)
    this.name = 'StreamError'
    this.code = code
  }
}

export async function streamChat(
  request: StreamRequest,
  callbacks: StreamCallbacks,
  abortController?: AbortController
): Promise<void> {
  const ctrl = abortController ?? new AbortController()

  const headers = await getAuthHeaders()

  await fetchEventSource(`${getApiBaseUrl()}/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
    signal: ctrl.signal,
    openWhenHidden: true,

    onopen: async (response) => {
      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = errorText
        let errorCode = 'INTERNAL_ERROR'
        try {
          const parsed: unknown = JSON.parse(errorText)
          // Structured error from error middleware: { error: { code, message } }
          const structured = (parsed as { error?: { code?: unknown; message?: unknown } }).error
          if (structured && typeof structured.code === 'string') {
            errorCode = structured.code
            errorMessage = typeof structured.message === 'string' ? structured.message : errorText
          } else {
            errorMessage = errorMessageFrom(parsed) ?? errorText
          }
        } catch {
          // Keep original text
        }
        if (response.status === 401) {
          window.dispatchEvent(new CustomEvent('auth:signout'))
        }
        throw new StreamError(errorMessage, errorCode)
      }
    },

    onmessage: (event) => {
      if (event.event === '' || !event.data) {
        return
      }

      const eventType = event.event as StreamEventType

      try {
        const data: unknown = JSON.parse(event.data)

        switch (eventType) {
          case 'status':
            callbacks.onStatus?.(data as StatusEventData)
            break
          case 'content':
            callbacks.onContent?.(data as ContentEventData)
            break
          case 'sources':
            callbacks.onSources?.(data as SourcesEventData)
            break
          case 'metadata':
            callbacks.onMetadata?.(data as MetadataEventData)
            break
          case 'error':
            callbacks.onError?.(data as ErrorEventData)
            break
          case 'citations':
            callbacks.onCitations?.(data as CitationsEventData)
            break
          case 'done':
            callbacks.onDone?.()
            break
        }
      } catch (e) {
        console.error('Failed to parse SSE event data:', e, event.data)
      }
    },

    onerror: (err) => {
      const message = err instanceof Error && err.message ? err.message : 'Stream connection error'
      throw new StreamError(message, 'CONNECTION_ERROR')
    },

    onclose: () => {
      callbacks.onDone?.()
    },
  })

  // fetchEventSource resolves silently on abort instead of rejecting.
  // Honor the contract callers expect: abort means StreamAbortError.
  if (ctrl.signal.aborted) {
    throw new StreamAbortError()
  }
}
