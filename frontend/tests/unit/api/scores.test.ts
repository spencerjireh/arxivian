import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { ApiError } from '../../../src/api/client'
import {
  fetchPaperScore,
  usePaperScore,
  SCORE_POLL_INTERVAL_MS,
  SCORE_POLL_TIMEOUT_MS,
} from '../../../src/api/scores'
import { makePaperMetadata } from '../../fixtures/feed'
import { makePaperScoreDetail } from '../../fixtures/scores'
import type { ReactNode } from 'react'

const apiGet = vi.fn()
vi.mock('../../../src/api/client', async () => {
  const actual =
    await vi.importActual<typeof import('../../../src/api/client')>('../../../src/api/client')
  return { ...actual, apiGet: (...args: unknown[]) => apiGet(...args) }
})

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

beforeEach(() => {
  apiGet.mockReset()
})

describe('fetchPaperScore', () => {
  it('discriminates ready and pending bodies', async () => {
    const detail = makePaperScoreDetail()
    apiGet.mockResolvedValueOnce(detail)
    expect(await fetchPaperScore('2401.00001')).toEqual({ status: 'ready', detail })
    const paper = makePaperMetadata()
    apiGet.mockResolvedValueOnce({
      status: 'pending',
      arxiv_id: '2401.00001',
      paper,
      task_id: 't1',
    })
    expect(await fetchPaperScore('2401.00001')).toEqual({ status: 'pending', task_id: 't1', paper })
    expect(apiGet).toHaveBeenCalledWith('/papers/2401.00001/score')
  })
})

describe('usePaperScore', () => {
  it('returns ready data without polling', async () => {
    apiGet.mockResolvedValue(makePaperScoreDetail())
    const { result } = renderHook(() => usePaperScore('2401.00001'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.data?.status).toBe('ready'))
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(result.current.pollTimedOut).toBe(false)
  })

  it('polls while pending, then stops after the timeout and restarts on demand', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      apiGet.mockResolvedValue({ status: 'pending', arxiv_id: '2401.00001', task_id: 't1' })
      const { result } = renderHook(() => usePaperScore('2401.00001'), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.data?.status).toBe('pending'))
      expect(apiGet).toHaveBeenCalledTimes(1)

      await act(async () => {
        await vi.advanceTimersByTimeAsync(SCORE_POLL_INTERVAL_MS + 50)
      })
      await waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2))

      await act(async () => {
        await vi.advanceTimersByTimeAsync(SCORE_POLL_TIMEOUT_MS + SCORE_POLL_INTERVAL_MS)
      })
      await waitFor(() => expect(result.current.pollTimedOut).toBe(true))
      const callsAtTimeout = apiGet.mock.calls.length
      await act(async () => {
        await vi.advanceTimersByTimeAsync(SCORE_POLL_INTERVAL_MS * 3)
      })
      expect(apiGet.mock.calls.length).toBe(callsAtTimeout)

      act(() => {
        result.current.restartPolling()
      })
      await waitFor(() => expect(apiGet.mock.calls.length).toBeGreaterThan(callsAtTimeout))
      expect(result.current.pollTimedOut).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })

  it('does not poll a pending answer when polling is off (anonymous reader)', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      apiGet.mockResolvedValue({
        status: 'pending',
        arxiv_id: '2401.00001',
        paper: makePaperMetadata(),
        task_id: null,
      })
      const { result } = renderHook(() => usePaperScore('2401.00001', { poll: false }), {
        wrapper: createWrapper(),
      })
      await waitFor(() => expect(result.current.data?.status).toBe('pending'))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(SCORE_POLL_INTERVAL_MS * 2)
      })
      expect(apiGet).toHaveBeenCalledTimes(1)
      expect(result.current.pollTimedOut).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })

  it.each([
    [404, 'Paper not found'],
    [429, "You reached today's limit of 10 on-demand scores. Resets at midnight UTC."],
  ])('does not retry a %i', async (status, message) => {
    apiGet.mockRejectedValue(new ApiError(status, 'Error', message))
    const { result } = renderHook(() => usePaperScore('9999.99999'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(result.current.error?.status).toBe(status)
    expect(result.current.error?.message).toBe(message)
  })
})
