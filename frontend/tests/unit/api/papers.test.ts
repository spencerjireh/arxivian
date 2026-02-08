import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import type { ReactNode } from 'react'
import { usePapers, paperKeys } from '../../../src/api/papers'

vi.mock('../../../src/api/client', () => ({
  apiGet: vi.fn().mockResolvedValue({
    total: 0,
    offset: 0,
    limit: 20,
    papers: [],
  }),
  apiDelete: vi.fn().mockResolvedValue({ arxiv_id: 'test', title: 'test', chunks_deleted: 0, message: 'ok' }),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('usePapers', () => {
  it('fetches with correct query key', async () => {
    const params = { offset: 0, limit: 20 }
    const { result } = renderHook(() => usePapers(params), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual({
      total: 0,
      offset: 0,
      limit: 20,
      papers: [],
    })
  })

  it('builds query keys correctly', () => {
    const params = { offset: 10, limit: 20, category: 'cs.AI' }
    const key = paperKeys.list(params)

    expect(key).toEqual(['papers', 'list', params])
  })

  it('has explicit staleTime of 60_000', async () => {
    const params = { offset: 0, limit: 20 }
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    })
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children)

    const { result } = renderHook(() => usePapers(params), { wrapper })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    const queryCache = queryClient.getQueryCache()
    const query = queryCache.find({ queryKey: paperKeys.list(params) })
    const observers = query?.observers ?? []
    expect(observers.length).toBeGreaterThan(0)
    expect(observers[0].options.staleTime).toBe(60_000)
  })
})
