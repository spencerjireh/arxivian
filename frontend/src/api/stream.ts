// SSE stream handler using fetchEventSource

import { fetchEventSource } from '@microsoft/fetch-event-source'
import { getApiBaseUrl } from './client'
import type {
  StreamRequest,
  StreamEventType,
  StatusEventData,
  ContentEventData,
  SourcesEventData,
  MetadataEventData,
  ErrorEventData,
} from '../types/api'

export interface StreamCallbacks {
  onStatus?: (data: StatusEventData) => void
  onContent?: (data: ContentEventData) => void
  onSources?: (data: SourcesEventData) => void
  onMetadata?: (data: MetadataEventData) => void
  onError?: (data: ErrorEventData) => void
  onDone?: () => void
}

export class StreamAbortError extends Error {
  constructor() {
    super('Stream aborted')
    this.name = 'StreamAbortError'
  }
}

export async function streamChat(
  request: StreamRequest,
  callbacks: StreamCallbacks,
  abortController?: AbortController
): Promise<void> {
  const ctrl = abortController ?? new AbortController()

  await fetchEventSource(`${getApiBaseUrl()}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
    signal: ctrl.signal,
    openWhenHidden: true,

    onopen: async (response) => {
      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = errorText
        try {
          const parsed = JSON.parse(errorText)
          errorMessage = parsed.detail || parsed.message || errorText
        } catch {
          // Keep original text
        }
        throw new Error(errorMessage)
      }
    },

    onmessage: (event) => {
      if (event.event === '' || !event.data) {
        return
      }

      const eventType = event.event as StreamEventType

      try {
        const data = JSON.parse(event.data)

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
          case 'done':
            callbacks.onDone?.()
            break
        }
      } catch (e) {
        console.error('Failed to parse SSE event data:', e, event.data)
      }
    },

    onerror: (err) => {
      if (err.name === 'AbortError') {
        throw new StreamAbortError()
      }
      callbacks.onError?.({ error: err.message || 'Stream connection error' })
      throw err
    },

    onclose: () => {
      callbacks.onDone?.()
    },
  })
}

export function createStreamAbortController(): AbortController {
  return new AbortController()
}
