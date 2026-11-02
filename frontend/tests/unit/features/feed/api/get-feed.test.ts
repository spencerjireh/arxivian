import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { buildFeedQuery, useFeedWeek } from '@/features/feed/api/get-feed'
import { feedKeys, normalizeFeedParams } from '@/lib/query-keys'
import { makeFeedItem, makeFeedResponse } from '../../../../fixtures/feed'
import type { ReactNode } from 'react'

const apiGet = vi.fn()
vi.mock('@/lib/api-client', () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
}))

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('feed api', () => {
  it('normalizes params so equal weeks share a key', () => {
    expect(normalizeFeedParams({ week: undefined, include_dismissed: false })).toEqual({})
    expect(feedKeys.list({ week: '2026-08-03' })).toEqual(
      feedKeys.list({ week: '2026-08-03', include_dismissed: false })
    )
    expect(normalizeFeedParams({ week: '', include_dismissed: true })).toEqual({
      include_dismissed: true,
    })
  })

  it('asks for the whole week in one request', () => {
    expect(buildFeedQuery({})).toBe('/feed?limit=500')
    expect(buildFeedQuery({ week: '2026-08-03', include_dismissed: true })).toBe(
      '/feed?limit=500&week=2026-08-03&include_dismissed=true'
    )
  })

  it('loads the week', async () => {
    apiGet.mockResolvedValueOnce(makeFeedResponse([makeFeedItem()]))
    const { result } = renderHook(() => useFeedWeek({ week: '2026-08-03' }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(apiGet).toHaveBeenCalledWith('/feed?limit=500&week=2026-08-03')
    expect(result.current.data?.items).toHaveLength(1)
  })
})
