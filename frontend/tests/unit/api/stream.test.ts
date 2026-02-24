import type { EventSourceMessage } from '@microsoft/fetch-event-source'
import { streamChat, StreamAbortError, StreamError } from '../../../src/api/stream'
import type { StreamCallbacks } from '../../../src/api/stream'
import type { StreamRequest } from '../../../src/types/api'

type FESConfig = {
  signal?: AbortSignal
  onopen?: (response: Response) => Promise<void>
  onmessage?: (ev: EventSourceMessage) => void
  onerror?: (err: Error) => void
  onclose?: () => void
}

vi.mock('@microsoft/fetch-event-source', () => ({
  fetchEventSource: vi.fn(),
}))

vi.mock('../../../src/api/client', () => ({
  getApiBaseUrl: () => '/api',
  getAuthHeaders: () => Promise.resolve({ 'Content-Type': 'application/json' }),
}))

// Helper to get the mock and set its implementation per test.
async function getFESMock() {
  const mod = await import('@microsoft/fetch-event-source')
  return vi.mocked(mod.fetchEventSource)
}

const baseRequest: StreamRequest = { query: 'test query' }

describe('streamChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('throws StreamAbortError when signal is already aborted', async () => {
    const fes = await getFESMock()
    fes.mockImplementation(async () => {
      // fetchEventSource resolves silently even when aborted
    })

    const ctrl = new AbortController()
    ctrl.abort()

    await expect(streamChat(baseRequest, {}, ctrl)).rejects.toThrow(StreamAbortError)
  })

  it('throws StreamAbortError when signal aborts mid-stream', async () => {
    const fes = await getFESMock()

    let abortDuringExecution: () => void

    fes.mockImplementation(async () => {
      // Give the test a hook to abort while fetchEventSource is "running".
      await new Promise<void>((resolve) => {
        abortDuringExecution = () => {
          resolve()
        }
      })
    })

    const ctrl = new AbortController()
    const promise = streamChat(baseRequest, {}, ctrl)

    // Wait a tick so fetchEventSource mock is entered and awaiting.
    await new Promise((r) => setTimeout(r, 0))

    // Abort mid-stream, then let the mock resolve.
    ctrl.abort()
    abortDuringExecution!()

    await expect(promise).rejects.toThrow(StreamAbortError)
  })

  it('resolves normally when stream completes without abort', async () => {
    const fes = await getFESMock()
    fes.mockImplementation(async () => {
      // Completes without abort -- no-op
    })

    await expect(streamChat(baseRequest, {})).resolves.toBeUndefined()
  })

  it('dispatches callbacks for each event type', async () => {
    const fes = await getFESMock()

    fes.mockImplementation(async (_url, config) => {
      const { onmessage } = config as FESConfig
      const events: { event: string; data: string }[] = [
        { event: 'status', data: JSON.stringify({ step: 'routing', message: 'Routing query' }) },
        { event: 'content', data: JSON.stringify({ token: 'hello' }) },
        { event: 'sources', data: JSON.stringify({ sources: [] }) },
        {
          event: 'metadata',
          data: JSON.stringify({
            query: 'q',
            execution_time_ms: 100,
            retrieval_attempts: 1,
            provider: 'openai',
            model: 'gpt-4o-mini',
            turn_number: 1,
            reasoning_steps: [],
          }),
        },
        { event: 'error', data: JSON.stringify({ error: 'oops' }) },
        { event: 'citations', data: JSON.stringify({ arxiv_id: '1234', title: 't', reference_count: 0, references: [] }) },
        { event: 'done', data: '{}' },
      ]

      for (const ev of events) {
        onmessage?.({ id: '', event: ev.event, data: ev.data } as EventSourceMessage)
      }
    })

    const callbacks: StreamCallbacks = {
      onStatus: vi.fn(),
      onContent: vi.fn(),
      onSources: vi.fn(),
      onMetadata: vi.fn(),
      onError: vi.fn(),
      onCitations: vi.fn(),
      onDone: vi.fn(),
    }

    await streamChat(baseRequest, callbacks)

    expect(callbacks.onStatus).toHaveBeenCalledWith({ step: 'routing', message: 'Routing query' })
    expect(callbacks.onContent).toHaveBeenCalledWith({ token: 'hello' })
    expect(callbacks.onSources).toHaveBeenCalledWith({ sources: [] })
    expect(callbacks.onMetadata).toHaveBeenCalledWith(
      expect.objectContaining({ query: 'q', provider: 'openai' })
    )
    expect(callbacks.onError).toHaveBeenCalledWith({ error: 'oops' })
    expect(callbacks.onCitations).toHaveBeenCalledWith(
      expect.objectContaining({ arxiv_id: '1234' })
    )
    expect(callbacks.onDone).toHaveBeenCalled()
  })

  it('skips empty events gracefully', async () => {
    const fes = await getFESMock()

    fes.mockImplementation(async (_url, config) => {
      const { onmessage } = config as FESConfig
      // Empty event name and missing data -- should be skipped
      onmessage?.({ id: '', event: '', data: '' } as EventSourceMessage)
      onmessage?.({ id: '', event: 'content', data: '' } as EventSourceMessage)
    })

    const callbacks: StreamCallbacks = { onContent: vi.fn() }
    await streamChat(baseRequest, callbacks)

    expect(callbacks.onContent).not.toHaveBeenCalled()
  })

  it('propagates non-abort errors from onerror as StreamError with CONNECTION_ERROR code', async () => {
    const fes = await getFESMock()
    const networkError = new Error('Network failure')

    fes.mockImplementation(async (_url, config) => {
      const { onerror } = config as FESConfig
      // onerror wraps the error as StreamError and re-throws
      onerror?.(networkError)
    })

    const callbacks: StreamCallbacks = { onError: vi.fn() }

    const promise = streamChat(baseRequest, callbacks)
    await expect(promise).rejects.toThrow(StreamError)
    await promise.catch((err) => {
      expect(err).toBeInstanceOf(StreamError)
      expect(err.code).toBe('CONNECTION_ERROR')
      expect(err.message).toBe('Network failure')
    })
    // onerror no longer calls callbacks.onError (handled by runStream catch)
    expect(callbacks.onError).not.toHaveBeenCalled()
  })
})
